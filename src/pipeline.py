from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .ingest import load_charging_data
from .osm_router import enrich_route_polylines
from .planner import TripConfig, plan_route
from .traffic import load_traffic_model
from .transform import enrich_stations_with_connectors, normalize_connector_live, normalize_stations
from .ui_format import format_for_ui


def _cfg(config: dict) -> TripConfig:
    traffic_fallback = float(config.get("traffic_index", 0.9))
    return TripConfig(
        origin=(float(config["origin_lat"]), float(config["origin_lon"])),
        destination=(float(config["dest_lat"]), float(config["dest_lon"])),
        battery_kwh=float(config["battery_kwh"]),
        soc_now_pct=float(config["soc_now_pct"]),
        reserve_soc_pct=float(config["reserve_soc_pct"]),
        desired_arrival_soc_pct=float(config["desired_arrival_soc_pct"]),
        consumption_kwh_per_km=float(config["consumption_kwh_per_km"]),
        vehicle_connector=str(config["vehicle_connector"]),
        avg_speed_kmh=float(config["avg_speed_kmh"]),
        traffic_factor=float(config.get("traffic_factor", traffic_fallback)),
        charge_efficiency=float(config["charge_efficiency"]),
        min_drive_before_charge_km=float(config.get("min_drive_before_charge_km", 25.0)),
        max_stops=int(config.get("max_stops", 2)),
    )


def _waypoint_coords(trip: dict, plan: dict) -> dict[str, tuple[float, float]]:
    coords = {
        "origin": (float(trip["origin"]["lat"]), float(trip["origin"]["lon"])),
        "destination": (float(trip["destination"]["lat"]), float(trip["destination"]["lon"])),
    }
    for stop in plan.get("stops", []):
        coords[str(stop["station_id"])] = (float(stop["lat"]), float(stop["lon"]))
    return coords


def _enrich_plans_with_roads(
    trip: dict,
    plans: list[dict],
    avg_speed_kmh: float,
    traffic_factor_fn,
) -> str:
    backend = "haversine"
    for plan in plans:
        if not plan.get("legs"):
            continue
        plan_backend = enrich_route_polylines(
            plan,
            _waypoint_coords(trip, plan),
            avg_speed_kmh,
            traffic_factor_fn=traffic_factor_fn,
        )
        if plan_backend == "osrm":
            backend = "osrm"
    return backend


def run_pipeline_with_config(mode: str, city: str, config: dict) -> dict:
    mode = mode.lower().strip()
    cities = config.get("cities")
    use_traffic = bool(config.get("use_traffic", mode == "tdx"))
    station_raw, connector_raw, connector_spec_raw = load_charging_data(mode, city, cities=cities)

    stations = normalize_stations(station_raw, fallback_city=city)
    stations = enrich_stations_with_connectors(stations, connector_spec_raw)
    connectors = normalize_connector_live(connector_raw)

    traffic_model = None
    if use_traffic:
        traffic_model = load_traffic_model(
            mode,
            city,
            cities,
            float(config.get("traffic_index", 0.9)),
        )

    use_road_geometry = bool(config.get("use_osm", True))
    # Fast feasibility search first; enrich selected route with road geometry after.
    result = plan_route(
        stations,
        connectors,
        _cfg(config),
        use_osm=False,
        traffic_model=traffic_model,
    )

    if use_road_geometry:
        trip = result["trip"]
        tf_fn = (lambda o, d: traffic_model.factor_for_leg(o, d)) if traffic_model else None
        plans = [result["route_plan"], *result.get("alternatives", [])]
        result["routing_backend"] = _enrich_plans_with_roads(
            trip,
            plans,
            float(config["avg_speed_kmh"]),
            tf_fn,
        )
    else:
        result["routing_backend"] = result.get("routing_backend", "haversine")

    result["ui"] = format_for_ui(result)
    result["meta"] = {
        "mode": mode,
        "city": city,
        "data_source": "TDX + Traffic + Roads" if mode == "tdx" and use_traffic else ("TDX + Roads" if mode == "tdx" else "Sample"),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "station_rows_raw": len(station_raw),
        "connector_rows_raw": len(connector_raw),
        "connector_spec_rows_raw": len(connector_spec_raw),
        "station_rows_normalized": len(stations),
        "connector_groups_normalized": len(connectors),
        "traffic_enabled": use_traffic,
        "road_geometry_enabled": use_road_geometry,
        "traffic": result.get("traffic"),
        "routing_backend": result.get("routing_backend"),
    }
    return result


def save_result(result: dict, out_path: str = "outputs/mvp_result.json") -> Path:
    import json

    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
