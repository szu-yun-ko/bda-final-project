from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import combinations

from .energy_model import (
    charge_time_minutes,
    drive_energy_kwh,
    expected_wait_minutes,
    kwh_from_soc,
    soc_from_kwh,
)
from .osm_router import RoadRouter
from .traffic import TrafficModel
from .types import ConnectorLive, Station


@dataclass
class TripConfig:
    origin: tuple[float, float]
    destination: tuple[float, float]
    battery_kwh: float
    soc_now_pct: float
    reserve_soc_pct: float
    desired_arrival_soc_pct: float
    consumption_kwh_per_km: float
    vehicle_connector: str
    avg_speed_kmh: float
    traffic_factor: float
    charge_efficiency: float
    min_drive_before_charge_km: float
    max_stops: int


def _station_point(s: Station) -> tuple[float, float]:
    return (s.lat, s.lon)


def _compatible(s: Station, connector: str) -> bool:
    return connector.upper() in [c.upper() for c in s.connector_types]


def _corridor_distance_km(
    point: tuple[float, float],
    origin: tuple[float, float],
    destination: tuple[float, float],
) -> float:
    # Distance from point to straight O-D segment (approx, degrees to km).
    from .energy_model import haversine_km

    d1 = haversine_km(origin[0], origin[1], point[0], point[1])
    d2 = haversine_km(point[0], point[1], destination[0], destination[1])
    direct = haversine_km(origin[0], origin[1], destination[0], destination[1])
    return max(0.0, (d1 + d2) - direct)


def _corridor_stations_near(stations: list[Station], cfg: TripConfig, limit: int = 80) -> list[Station]:
    ranked = sorted(
        stations,
        key=lambda s: _corridor_distance_km(_station_point(s), cfg.origin, cfg.destination),
    )
    return ranked[:limit]


def _filter_stations(stations: list[Station], cfg: TripConfig, limit: int = 40) -> list[Station]:
    connector = cfg.vehicle_connector.upper()
    filtered = [s for s in stations if _compatible(s, connector)]
    filtered.sort(key=lambda s: _corridor_distance_km(_station_point(s), cfg.origin, cfg.destination))
    return filtered[:limit]


def _leg_traffic(
    traffic_model: TrafficModel | None,
    cfg: TripConfig,
    from_pt: tuple[float, float],
    to_pt: tuple[float, float],
) -> float:
    if traffic_model is not None:
        return traffic_model.factor_for_leg(from_pt, to_pt)
    return cfg.traffic_factor


def _simulate_route(
    router: RoadRouter,
    cfg: TripConfig,
    live_by_station: dict[str, ConnectorLive],
    waypoints: list[tuple[str, tuple[float, float], Station | None]],
    traffic_model: TrafficModel | None = None,
) -> dict | None:
    energy_kwh = kwh_from_soc(cfg.battery_kwh, cfg.soc_now_pct)
    reserve_kwh = kwh_from_soc(cfg.battery_kwh, cfg.reserve_soc_pct)
    target_kwh = kwh_from_soc(cfg.battery_kwh, cfg.desired_arrival_soc_pct)
    timeline: list[dict] = []
    legs: list[dict] = []
    stops: list[dict] = []
    charging_events: list[dict] = []
    elapsed = 0.0
    driven_since_charge = 0.0

    for i in range(len(waypoints) - 1):
        from_id, from_pt, from_station = waypoints[i]
        to_id, to_pt, to_station = waypoints[i + 1]
        leg_tf = _leg_traffic(traffic_model, cfg, from_pt, to_pt)
        leg = router.route(from_pt, to_pt, cfg.avg_speed_kmh, leg_tf)
        energy_use = drive_energy_kwh(leg.distance_km, cfg.consumption_kwh_per_km, leg_tf)
        soc_start = soc_from_kwh(cfg.battery_kwh, energy_kwh)
        energy_kwh -= energy_use
        if energy_kwh < reserve_kwh - 1e-6:
            return None
        soc_end = soc_from_kwh(cfg.battery_kwh, energy_kwh)
        legs.append(
            {
                "from": from_id,
                "to": to_id,
                "distance_km_est": round(leg.distance_km, 2),
                "drive_minutes_est": round(leg.drive_minutes, 2),
                "polyline": leg.polyline,
                "soc_start_pct": round(soc_start, 2),
                "soc_end_pct": round(soc_end, 2),
                "traffic_factor": round(leg_tf, 3),
            }
        )
        timeline.append(
            {
                "phase": "drive",
                "label": f"{from_id} -> {to_id}",
                "start_min": round(elapsed, 2),
                "duration_min": round(leg.drive_minutes, 2),
            }
        )
        elapsed += leg.drive_minutes
        driven_since_charge += leg.distance_km

        if to_station is not None:
            if driven_since_charge < cfg.min_drive_before_charge_km:
                return None
            stops.append(asdict(to_station))
            live = live_by_station.get(to_station.station_id, ConnectorLive(to_station.station_id, 0, 0, 0))
            wait_min = expected_wait_minutes(live.available_count, live.occupied_count)
            timeline.append(
                {
                    "phase": "wait",
                    "label": to_station.name,
                    "start_min": round(elapsed, 2),
                    "duration_min": round(wait_min, 2),
                }
            )
            elapsed += wait_min

            remaining_idx = i + 1
            remaining_km = 0.0
            for j in range(remaining_idx, len(waypoints) - 1):
                a = waypoints[j][1]
                b = waypoints[j + 1][1]
                rem_tf = _leg_traffic(traffic_model, cfg, a, b)
                rem_leg = router.route(a, b, cfg.avg_speed_kmh, rem_tf)
                remaining_km += rem_leg.distance_km
            needed_depart_kwh = drive_energy_kwh(remaining_km, cfg.consumption_kwh_per_km, leg_tf)
            needed_depart_kwh = max(needed_depart_kwh + reserve_kwh, needed_depart_kwh + target_kwh)
            charge_kwh = max(0.0, needed_depart_kwh - energy_kwh)
            soc_before_charge = soc_from_kwh(cfg.battery_kwh, energy_kwh)
            charge_min = charge_time_minutes(
                charge_kwh,
                to_station.max_power_kw,
                soc_before_charge,
                cfg.charge_efficiency,
            )
            energy_kwh += charge_kwh
            timeline.append(
                {
                    "phase": "charge",
                    "label": to_station.name,
                    "start_min": round(elapsed, 2),
                    "duration_min": round(charge_min, 2),
                    "energy_kwh": round(charge_kwh, 2),
                }
            )
            elapsed += charge_min
            driven_since_charge = 0.0
            charging_events.append(
                {
                    "station_id": to_station.station_id,
                    "station_name": to_station.name,
                    "wait_minutes_est": round(wait_min, 2),
                    "charge_minutes_est": round(charge_min, 2),
                    "energy_added_kwh_est": round(charge_kwh, 2),
                    "available_connectors": live.available_count,
                    "occupied_connectors": live.occupied_count,
                }
            )

    final_soc = soc_from_kwh(cfg.battery_kwh, energy_kwh)
    if final_soc < cfg.desired_arrival_soc_pct - 0.01:
        return None
    if final_soc < cfg.reserve_soc_pct - 0.01:
        return None
    return {
        "total_time_minutes_est": round(elapsed, 2),
        "final_soc_pct_est": round(final_soc, 2),
        "stops": stops,
        "legs": legs,
        "timeline": timeline,
        "charging_events": charging_events,
        "stop_count": len(stops),
    }


def plan_route(
    stations: list[Station],
    live_status: list[ConnectorLive],
    cfg: TripConfig,
    use_osm: bool = True,
    traffic_model: TrafficModel | None = None,
) -> dict:
    live_by_station = {x.station_id: x for x in live_status}
    router = RoadRouter(use_osm=use_osm)
    points = [cfg.origin, cfg.destination] + [_station_point(s) for s in stations]
    routing_backend = router.prepare(points)

    direct_tf = _leg_traffic(traffic_model, cfg, cfg.origin, cfg.destination)
    direct = router.route(cfg.origin, cfg.destination, cfg.avg_speed_kmh, direct_tf)
    direct_energy = drive_energy_kwh(direct.distance_km, cfg.consumption_kwh_per_km, direct_tf)
    arrival_soc_direct = soc_from_kwh(
        cfg.battery_kwh,
        kwh_from_soc(cfg.battery_kwh, cfg.soc_now_pct) - direct_energy,
    )

    corridor_stations = _corridor_stations_near(stations, cfg, limit=80)
    corridor_station_dicts = [asdict(s) for s in corridor_stations]

    candidates: list[dict] = []
    if arrival_soc_direct >= cfg.desired_arrival_soc_pct:
        candidates.append(
            _simulate_route(
                router,
                cfg,
                live_by_station,
                [("origin", cfg.origin, None), ("destination", cfg.destination, None)],
                traffic_model,
            )
        )

    if arrival_soc_direct < cfg.desired_arrival_soc_pct:
        filtered = _filter_stations(stations, cfg, limit=40)
        # 1-stop routes
        for s in filtered:
            plan = _simulate_route(
                router,
                cfg,
                live_by_station,
                [
                    ("origin", cfg.origin, None),
                    (s.station_id, _station_point(s), s),
                    ("destination", cfg.destination, None),
                ],
                traffic_model,
            )
            if plan:
                candidates.append(plan)

        # 2-stop routes for long trips
        if cfg.max_stops >= 2 and direct.distance_km > 110 and len(filtered) >= 2:
            top = filtered[:12]
            for s1, s2 in combinations(top, 2):
                d1 = router.route(cfg.origin, _station_point(s1), cfg.avg_speed_kmh, cfg.traffic_factor).distance_km
                d2 = router.route(_station_point(s1), _station_point(s2), cfg.avg_speed_kmh, cfg.traffic_factor).distance_km
                if d2 <= 5:
                    continue
                plan = _simulate_route(
                    router,
                    cfg,
                    live_by_station,
                    [
                        ("origin", cfg.origin, None),
                        (s1.station_id, _station_point(s1), s1),
                        (s2.station_id, _station_point(s2), s2),
                        ("destination", cfg.destination, None),
                    ],
                    traffic_model,
                )
                if plan:
                    candidates.append(plan)

    candidates = [c for c in candidates if c is not None]
    candidates.sort(key=lambda x: x["total_time_minutes_est"])
    best = candidates[0] if candidates else None

    return {
        "trip": {
            "origin": {"lat": cfg.origin[0], "lon": cfg.origin[1]},
            "destination": {"lat": cfg.destination[0], "lon": cfg.destination[1]},
            "objective": "min_total_trip_time_minutes",
            "constraints": {
                "reserve_soc_pct": cfg.reserve_soc_pct,
                "desired_arrival_soc_pct": cfg.desired_arrival_soc_pct,
                "vehicle_connector": cfg.vehicle_connector.upper(),
                "min_drive_before_charge_km": cfg.min_drive_before_charge_km,
                "max_stops": cfg.max_stops,
            },
            "direct_distance_km_est": round(direct.distance_km, 2),
            "direct_drive_minutes_est": round(direct.drive_minutes, 2),
            "arrival_soc_if_direct_pct": round(arrival_soc_direct, 2),
            "needs_charge_stop": arrival_soc_direct < cfg.desired_arrival_soc_pct,
            "battery_kwh": cfg.battery_kwh,
            "soc_now_pct": cfg.soc_now_pct,
            "consumption_kwh_per_km": cfg.consumption_kwh_per_km,
            "traffic_factor": direct_tf,
            "traffic_enabled": traffic_model is not None,
        },
        "route_plan": best
        or {
            "total_time_minutes_est": None,
            "final_soc_pct_est": None,
            "stops": [],
            "legs": [],
            "timeline": [],
            "charging_events": [],
            "stop_count": 0,
            "error": "No feasible route found with current constraints.",
        },
        "alternatives": candidates[1:4],
        "corridor_stations": corridor_station_dicts,
        "routing_backend": routing_backend,
        "traffic": traffic_model.summary() if traffic_model else None,
    }
