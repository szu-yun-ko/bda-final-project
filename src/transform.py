from __future__ import annotations

from typing import Any

from .types import ConnectorLive, Station

CONNECTOR_TYPE_MAP = {
    "1": "CCS1",
    "2": "CCS2",
    "3": "CHADEMO",
    "4": "TESLA",
    "5": "J1772",
    "6": "TYPE2",
    "CCS1": "CCS1",
    "CCS2": "CCS2",
    "CCCS2": "CCS2",
    "CHADEMO": "CHADEMO",
    "J1772": "J1772",
    "J1772_TYPE1": "J1772",
    "MENNEKES_TYPE2": "TYPE2",
    "TYPE2": "TYPE2",
}


def _station_name(value: Any, fallback: str) -> str:
    if isinstance(value, dict):
        return str(value.get("Zh_tw") or value.get("En") or fallback)
    return str(value or fallback)


def _parse_power_kw(value: Any, power_mode: Any = None) -> float:
    if isinstance(value, str):
        digits = "".join(ch if ch.isdigit() or ch == "." else " " for ch in value).split()
        for token in digits:
            try:
                kw = float(token)
                if kw > 0:
                    return kw
            except ValueError:
                continue
    try:
        mode = int(power_mode)
        return 120.0 if mode == 2 else 7.0
    except (TypeError, ValueError):
        return 0.0


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def normalize_stations(raw: list[dict[str, Any]], fallback_city: str = "") -> list[Station]:
    rows: list[Station] = []
    for r in raw:
        station_id = str(r.get("StationUID") or r.get("StationID") or r.get("station_id") or "").strip()
        if not station_id:
            continue
        lat = _float(r.get("PositionLat") or r.get("Latitude") or r.get("lat"))
        lon = _float(r.get("PositionLon") or r.get("Longitude") or r.get("lon"))
        if lat == 0.0 and lon == 0.0:
            continue
        raw_connector_types = r.get("ConnectorTypes") or r.get("connector_types") or []
        if isinstance(raw_connector_types, str):
            connector_types = [_normalize_connector_type(x) for x in raw_connector_types.split(",") if x.strip()]
        elif isinstance(raw_connector_types, list):
            connector_types = [_normalize_connector_type(x) for x in raw_connector_types if str(x).strip()]
        else:
            connector_types = []
        embedded = r.get("Connectors") or []
        if isinstance(embedded, list):
            for conn in embedded:
                if isinstance(conn, dict):
                    connector_types.append(_normalize_connector_type(conn.get("Type")))
        connector_types = sorted({x for x in connector_types if x})
        if not connector_types:
            connector_types = ["CCS2"]

        max_power_kw = _float(r.get("MaxPowerKW") or r.get("PowerKW") or r.get("power_kw"))
        if max_power_kw <= 0 and embedded:
            powers = [_parse_power_kw(None, c.get("Power")) for c in embedded if isinstance(c, dict)]
            max_power_kw = max(powers) if powers else 60.0
        connector_count = _int(
            r.get("ConnectorCount")
            or r.get("connector_count")
            or r.get("ChargingPoints")
            or r.get("Spaces")
            or 0
        )
        rows.append(
            Station(
                station_id=station_id,
                name=_station_name(r.get("StationName") or r.get("name"), station_id),
                lat=lat,
                lon=lon,
                city=str(r.get("City") or r.get("city") or fallback_city),
                address=str(
                    r.get("Address")
                    or r.get("address")
                    or ((r.get("Location") or {}).get("Place") or {}).get("POI")
                    or ""
                ),
                max_power_kw=max_power_kw,
                connector_count=connector_count,
                connector_types=connector_types,
            )
        )
    return rows


def normalize_connector_live(raw: list[dict[str, Any]]) -> list[ConnectorLive]:
    # TDX statuses can be numeric/string depending on source. We support both.
    available_tokens = {"1", "available", "idle", "free"}
    occupied_tokens = {"2", "occupied", "charging", "busy"}
    fault_tokens = {"3", "fault", "offline", "error"}

    by_station: dict[str, ConnectorLive] = {}
    for r in raw:
        station_id = str(r.get("StationUID") or r.get("StationID") or r.get("station_id") or "").strip()
        if not station_id:
            continue
        token = str(r.get("ConnectorStatus") or r.get("Status") or r.get("status") or "").strip().lower()
        current = by_station.get(station_id, ConnectorLive(station_id, 0, 0, 0))
        if token in available_tokens:
            current.available_count += 1
        elif token in occupied_tokens:
            current.occupied_count += 1
        elif token in fault_tokens:
            current.fault_count += 1
        by_station[station_id] = current
    return list(by_station.values())


def _normalize_connector_type(value: Any) -> str:
    token = str(value or "").strip().upper()
    return CONNECTOR_TYPE_MAP.get(token, token or "CCS2")


def merge_station_lists(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    for r in rows:
        sid = str(r.get("StationUID") or r.get("StationID") or "").strip()
        if sid:
            seen[sid] = r
    return list(seen.values())


def enrich_stations_with_connectors(
    stations: list[Station],
    connector_spec_raw: list[dict[str, Any]],
) -> list[Station]:
    by_station: dict[str, dict[str, Any]] = {}
    for r in connector_spec_raw:
        sid = str(r.get("StationUID") or r.get("StationID") or "").strip()
        if not sid:
            continue
        entry = by_station.setdefault(sid, {"types": set(), "max_kw": 0.0, "count": 0})
        entry["types"].add(_normalize_connector_type(r.get("ConnectorType") or r.get("Type") or r.get("PowerType")))
        entry["max_kw"] = max(
            entry["max_kw"],
            _parse_power_kw(r.get("PowerRating") or r.get("MaxPowerKW") or r.get("PowerKW"), r.get("Power")),
        )
        entry["count"] += 1

    enriched: list[Station] = []
    for s in stations:
        extra = by_station.get(s.station_id)
        if extra:
            types = sorted(extra["types"]) if extra["types"] else s.connector_types
            max_kw = extra["max_kw"] if extra["max_kw"] > 0 else s.max_power_kw
            count = extra["count"] if extra["count"] > 0 else s.connector_count
            enriched.append(
                Station(
                    station_id=s.station_id,
                    name=s.name,
                    lat=s.lat,
                    lon=s.lon,
                    city=s.city,
                    address=s.address,
                    max_power_kw=max_kw,
                    connector_count=count,
                    connector_types=types,
                )
            )
        else:
            enriched.append(s)
    return enriched
