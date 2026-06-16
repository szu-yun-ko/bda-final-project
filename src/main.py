from __future__ import annotations

import argparse

from .pipeline import run_pipeline_with_config, save_result
from .viz import build_route_map


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="EV routing data pipeline MVP")
    parser.add_argument("--mode", choices=["sample", "tdx"], default="sample")
    parser.add_argument("--city", default="Taipei", help="TDX city name, e.g., Taipei")
    parser.add_argument("--origin-lat", type=float, default=25.0478)
    parser.add_argument("--origin-lon", type=float, default=121.5170)
    parser.add_argument("--dest-lat", type=float, default=24.1477)
    parser.add_argument("--dest-lon", type=float, default=120.6736)
    parser.add_argument("--battery-kwh", type=float, default=60.0)
    parser.add_argument("--soc-now-pct", type=float, default=55.0)
    parser.add_argument("--reserve-soc-pct", type=float, default=10.0)
    parser.add_argument("--consumption-kwh-per-km", type=float, default=0.18)
    parser.add_argument("--desired-arrival-soc-pct", type=float, default=15.0)
    parser.add_argument("--vehicle-connector", default="CCS2")
    parser.add_argument("--avg-speed-kmh", type=float, default=55.0)
    parser.add_argument("--traffic-index", type=float, default=0.9)
    parser.add_argument("--charge-efficiency", type=float, default=0.9)
    parser.add_argument("--min-drive-before-charge-km", type=float, default=25.0)
    parser.add_argument("--max-stops", type=int, default=2)
    parser.add_argument("--use-osm", action="store_true", default=True)
    parser.add_argument("--no-osm", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_pipeline_with_config(
        mode=args.mode,
        city=args.city,
        config={
            "origin_lat": args.origin_lat,
            "origin_lon": args.origin_lon,
            "dest_lat": args.dest_lat,
            "dest_lon": args.dest_lon,
            "battery_kwh": args.battery_kwh,
            "soc_now_pct": args.soc_now_pct,
            "reserve_soc_pct": args.reserve_soc_pct,
            "consumption_kwh_per_km": args.consumption_kwh_per_km,
            "desired_arrival_soc_pct": args.desired_arrival_soc_pct,
            "vehicle_connector": args.vehicle_connector,
            "avg_speed_kmh": args.avg_speed_kmh,
            "traffic_index": args.traffic_index,
            "charge_efficiency": args.charge_efficiency,
            "min_drive_before_charge_km": args.min_drive_before_charge_km,
            "max_stops": args.max_stops,
            "use_osm": not args.no_osm,
        },
    )
    out_path = save_result(result)
    map_path = build_route_map(result)
    route_plan = result.get("route_plan", {})
    print(f"MVP output written to: {out_path}")
    print(f"Route map written to: {map_path}")
    print(f"Data source: {result['meta']['data_source']}")
    print(f"Routing backend: {result.get('routing_backend')}")
    print(f"Route total time (min est): {route_plan.get('total_time_minutes_est')}")
    print(f"Stops: {[s.get('name') for s in route_plan.get('stops', [])]}")


if __name__ == "__main__":
    main()
