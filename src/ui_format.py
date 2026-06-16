from __future__ import annotations

from typing import Any


def _fmt_duration(minutes: float | None) -> str:
    if minutes is None:
        return "-"
    total = int(round(minutes))
    h, m = divmod(total, 60)
    if h:
        return f"{h} h {m} min"
    return f"{m} min"


def _build_steps(trip: dict, plan: dict) -> list[dict[str, Any]]:
    legs = plan.get("legs", [])
    charging = plan.get("charging_events", [])
    stops = plan.get("stops", [])

    steps: list[dict[str, Any]] = [
        {
            "type": "depart",
            "title": "Depart",
            "subtitle": "Origin",
            "soc_pct": trip.get("soc_now_pct"),
            "duration_min": 0,
        }
    ]

    charge_idx = 0
    for leg in legs:
        steps.append(
            {
                "type": "drive",
                "title": f"Drive {leg.get('distance_km_est')} km",
                "subtitle": f"{leg.get('from')} → {leg.get('to')}",
                "duration_min": leg.get("drive_minutes_est"),
                "soc_start_pct": leg.get("soc_start_pct"),
                "soc_end_pct": leg.get("soc_end_pct"),
                "traffic_factor": leg.get("traffic_factor"),
            }
        )
        if leg.get("to") != "destination" and charge_idx < len(charging):
            ev = charging[charge_idx]
            stop = stops[charge_idx] if charge_idx < len(stops) else {}
            steps.append(
                {
                    "type": "charge",
                    "title": stop.get("name") or ev.get("station_name"),
                    "subtitle": f"{ev.get('energy_added_kwh_est')} kWh · {stop.get('max_power_kw')} kW",
                    "duration_min": (ev.get("wait_minutes_est") or 0) + (ev.get("charge_minutes_est") or 0),
                    "wait_min": ev.get("wait_minutes_est"),
                    "charge_min": ev.get("charge_minutes_est"),
                    "available_connectors": ev.get("available_connectors"),
                    "lat": stop.get("lat"),
                    "lon": stop.get("lon"),
                }
            )
            charge_idx += 1

    steps.append(
        {
            "type": "arrive",
            "title": "Arrive",
            "subtitle": "Destination",
            "soc_pct": plan.get("final_soc_pct_est"),
            "duration_min": 0,
        }
    )
    return steps


def _build_summary(trip: dict, plan: dict) -> dict[str, Any]:
    legs = plan.get("legs", [])
    charging = plan.get("charging_events", [])
    stops = plan.get("stops", [])

    drive_min = sum(float(x.get("drive_minutes_est", 0)) for x in legs)
    wait_min = sum(float(x.get("wait_minutes_est", 0)) for x in charging)
    charge_min = sum(float(x.get("charge_minutes_est", 0)) for x in charging)
    distance_km = sum(float(x.get("distance_km_est", 0)) for x in legs)

    return {
        "total_time_minutes_est": plan.get("total_time_minutes_est"),
        "total_time_label": _fmt_duration(plan.get("total_time_minutes_est")),
        "drive_time_label": _fmt_duration(drive_min),
        "charge_time_label": _fmt_duration(wait_min + charge_min),
        "distance_km_est": round(distance_km, 1),
        "stop_count": len(stops),
        "final_soc_pct_est": plan.get("final_soc_pct_est"),
        "needs_charge_stop": trip.get("needs_charge_stop"),
    }


def _build_route_option(trip: dict, plan: dict, option_id: int, label: str, is_best: bool) -> dict[str, Any]:
    return {
        "id": option_id,
        "label": label,
        "is_best": is_best,
        "summary": _build_summary(trip, plan),
        "steps": _build_steps(trip, plan),
        "stops": plan.get("stops", []),
        "legs": plan.get("legs", []),
    }


def format_for_ui(result: dict) -> dict[str, Any]:
    trip = result.get("trip", {})
    plan = result.get("route_plan", {})

    route_options = [_build_route_option(trip, plan, 0, "Recommended", True)]
    for i, alt in enumerate(result.get("alternatives", [])):
        route_options.append(_build_route_option(trip, alt, i + 1, f"Option {i + 2}", False))

    primary = route_options[0]
    alternatives = []
    for opt in route_options[1:]:
        alternatives.append(
            {
                "total_time_minutes_est": opt["summary"]["total_time_minutes_est"],
                "total_time_label": opt["summary"]["total_time_label"],
                "stops": [s.get("name") for s in opt.get("stops", [])],
                "final_soc_pct_est": opt["summary"]["final_soc_pct_est"],
            }
        )

    return {
        "summary": primary["summary"],
        "steps": primary["steps"],
        "timeline": plan.get("timeline", []),
        "legs": plan.get("legs", []),
        "stops": plan.get("stops", []),
        "alternatives": alternatives,
        "route_options": route_options,
        "origin": trip.get("origin"),
        "destination": trip.get("destination"),
    }
