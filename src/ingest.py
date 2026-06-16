from __future__ import annotations

from typing import Any

from .config import get_settings
from .sample_data import load_json
from .tdx_client import TdxClient
from .transform import enrich_stations_with_connectors, merge_station_lists, normalize_connector_live, normalize_stations

DEFAULT_CORRIDOR_CITIES = ["Taipei", "NewTaipei", "Taoyuan", "Hsinchu", "Taichung"]


def load_charging_data(mode: str, city: str, cities: list[str] | None = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    mode = mode.lower().strip()
    if mode == "sample":
        station_raw = load_json("station_city.json") + load_json("station_freeway.json")
        connector_raw = load_json("connector_live_city.json")
        connector_spec_raw = load_json("connector_spec_city.json")
        return station_raw, connector_raw, connector_spec_raw

    if mode != "tdx":
        raise ValueError("mode must be one of: sample, tdx")

    settings = get_settings()
    client = TdxClient(settings)
    city_list = cities if cities else [city]

    station_raw: list[dict[str, Any]] = []
    connector_raw: list[dict[str, Any]] = []
    connector_spec_raw: list[dict[str, Any]] = []

    def _safe_extend(target: list[dict[str, Any]], fn) -> None:
        try:
            rows = fn()
            if rows:
                target.extend(rows)
        except Exception:
            return

    _safe_extend(station_raw, client.fetch_freeway_station)
    _safe_extend(connector_raw, client.fetch_freeway_connector_live_status)
    _safe_extend(connector_spec_raw, client.fetch_freeway_connector)

    for c in city_list:
        _safe_extend(station_raw, lambda c=c: client.fetch_city_station(c))
        _safe_extend(connector_raw, lambda c=c: client.fetch_city_connector_live_status(c))
        _safe_extend(connector_spec_raw, lambda c=c: client.fetch_city_connector(c))

    station_raw = merge_station_lists(station_raw)
    connector_raw = merge_station_lists(connector_raw)
    connector_spec_raw = merge_station_lists(connector_spec_raw)
    if not station_raw:
        raise RuntimeError(
            "TDX ingestion returned zero stations. Check API key, city names, or wait if rate-limited (HTTP 429)."
        )
    return station_raw, connector_raw, connector_spec_raw


def load_traffic_factor(mode: str, city: str, fallback: float) -> float:
    if mode != "tdx":
        return fallback
    try:
        settings = get_settings()
        client = TdxClient(settings)
        rows = client.fetch_city_traffic(city)
        speeds = []
        for r in rows:
            speed = r.get("Speed") or r.get("AvgSpeed")
            if speed is None:
                continue
            try:
                speeds.append(float(speed))
            except (TypeError, ValueError):
                continue
        if not speeds:
            return fallback
        avg = sum(speeds) / len(speeds)
        # Map avg speed to factor around free-flow 70 km/h.
        return max(0.55, min(1.05, avg / 70.0))
    except Exception:
        return fallback
