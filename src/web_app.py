from __future__ import annotations

import json
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from .pipeline import run_pipeline_with_config, save_result

FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"

app = Flask(__name__, static_folder=str(FRONTEND_DIST), static_url_path="")
CORS(app)


def _parse_config(payload: dict) -> dict:
    return {
        "mode": payload.get("mode", "tdx"),
        "city": payload.get("city", "Taipei"),
        "cities": payload.get("cities"),
        "origin_lat": float(payload["origin_lat"]),
        "origin_lon": float(payload["origin_lon"]),
        "dest_lat": float(payload["dest_lat"]),
        "dest_lon": float(payload["dest_lon"]),
        "battery_kwh": float(payload.get("battery_kwh", 60)),
        "soc_now_pct": float(payload.get("soc_now_pct", 90)),
        "reserve_soc_pct": float(payload.get("reserve_soc_pct", 10)),
        "desired_arrival_soc_pct": float(payload.get("desired_arrival_soc_pct", 10)),
        "consumption_kwh_per_km": float(payload.get("consumption_kwh_per_km", 0.18)),
        "vehicle_connector": payload.get("vehicle_connector", "CCS2"),
        "avg_speed_kmh": float(payload.get("avg_speed_kmh", 55)),
        "traffic_index": float(payload.get("traffic_index", 0.9)),
        "charge_efficiency": float(payload.get("charge_efficiency", 0.9)),
        "min_drive_before_charge_km": float(payload.get("min_drive_before_charge_km", 25)),
        "max_stops": int(payload.get("max_stops", 2)),
        "use_osm": bool(payload.get("use_osm", False)),
        "use_traffic": bool(payload.get("use_traffic", True)),
    }


@app.get("/api/health")
def health():
    return jsonify({"ok": True})


@app.post("/api/plan")
def api_plan():
    payload = request.get_json(force=True, silent=True) or {}
    try:
        config = _parse_config(payload)
        result = run_pipeline_with_config(mode=config["mode"], city=config["city"], config=config)
        save_result(result)
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@app.get("/", defaults={"path": ""})
@app.get("/<path:path>")
def spa(path: str):
    if FRONTEND_DIST.exists():
        target = FRONTEND_DIST / path
        if path and target.exists() and target.is_file():
            return send_from_directory(FRONTEND_DIST, path)
        return send_from_directory(FRONTEND_DIST, "index.html")
    return (
        "<h1>Frontend not built</h1><p>Run: <code>cd frontend && npm install && npm run build</code></p>",
        503,
    )


if __name__ == "__main__":
    # Port 5001 avoids macOS AirPlay Receiver on 5000 (returns HTTP 403).
    app.run(debug=True, port=5001)
