from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .config import get_settings
from .energy_model import haversine_km
from .tdx_client import TdxClient

FREE_FLOW_KMH = 70.0
CONGESTION_FACTOR = {
    "1": 1.0,
    "2": 0.82,
    "3": 0.65,
    "4": 0.48,
    "5": 0.35,
}


@dataclass
class TrafficPoint:
    lat: float
    lon: float
    speed_kmh: float


class TrafficModel:
    def __init__(self, points: list[TrafficPoint], fallback_factor: float = 0.9) -> None:
        self.points = points
        self.fallback_factor = fallback_factor

    def factor_for_leg(self, origin: tuple[float, float], dest: tuple[float, float]) -> float:
        mid = ((origin[0] + dest[0]) / 2.0, (origin[1] + dest[1]) / 2.0)
        return self._factor_at(mid)

    def _factor_at(self, point: tuple[float, float]) -> float:
        if not self.points:
            return self.fallback_factor
        lat, lon = point
        ranked: list[tuple[float, TrafficPoint]] = []
        for p in self.points:
            d = haversine_km(lat, lon, p.lat, p.lon)
            if d <= 25.0:
                ranked.append((d, p))
        if not ranked:
            return self.fallback_factor
        ranked.sort(key=lambda x: x[0])
        speeds = [p.speed_kmh for _, p in ranked[:6] if p.speed_kmh > 0]
        if not speeds:
            return self.fallback_factor
        avg = sum(speeds) / len(speeds)
        return max(0.45, min(1.05, avg / FREE_FLOW_KMH))

    def summary(self) -> dict[str, Any]:
        return {
            "sensor_count": len(self.points),
            "fallback_factor": self.fallback_factor,
        }


def _lane_speed(row: dict[str, Any]) -> float | None:
    speeds: list[float] = []
    for flow in row.get("LinkFlows") or []:
        if not isinstance(flow, dict):
            continue
        for lane in flow.get("Lanes") or []:
            if not isinstance(lane, dict):
                continue
            try:
                speed = float(lane.get("Speed"))
                if speed > 0 and speed < 130:
                    speeds.append(speed)
            except (TypeError, ValueError):
                continue
    if not speeds:
        return None
    return sum(speeds) / len(speeds)


def _live_speed(row: dict[str, Any]) -> float | None:
    try:
        speed = float(row.get("TravelSpeed"))
        if speed > 0:
            return speed
    except (TypeError, ValueError):
        pass
    level = str(row.get("CongestionLevelID") or "")
    return FREE_FLOW_KMH * CONGESTION_FACTOR.get(level, 0.85)


def load_traffic_model(
    mode: str,
    city: str,
    cities: list[str] | None,
    fallback: float,
) -> TrafficModel:
    if mode != "tdx":
        return TrafficModel([], fallback_factor=fallback)

    settings = get_settings()
    client = TdxClient(settings)
    points: list[TrafficPoint] = []
    city_list = cities if cities else [city]

    try:
        vd_rows = client.fetch_freeway_vd()
        live_rows = client.fetch_freeway_vd_live()
        live_by_id = {str(r.get("VDID")): r for r in live_rows if r.get("VDID")}
        for vd in vd_rows:
            vid = str(vd.get("VDID") or "")
            live = live_by_id.get(vid)
            if not live:
                continue
            speed = _lane_speed(live)
            if speed is None:
                continue
            try:
                points.append(
                    TrafficPoint(
                        lat=float(vd.get("PositionLat")),
                        lon=float(vd.get("PositionLon")),
                        speed_kmh=speed,
                    )
                )
            except (TypeError, ValueError):
                continue
    except Exception:
        pass

    live_by_section: dict[str, dict[str, Any]] = {}
    for c in city_list:
        try:
            for row in client.fetch_city_traffic_live(c):
                sid = str(row.get("SectionID") or "")
                if sid:
                    live_by_section[sid] = row
        except Exception:
            continue

    for c in city_list:
        try:
            for sec in client.fetch_city_traffic_sections(c):
                sid = str(sec.get("SectionID") or "")
                live = live_by_section.get(sid, {})
                speed = _live_speed(live)
                if speed is None:
                    continue
                start = sec.get("SectionStart") or {}
                end = sec.get("SectionEnd") or {}
                try:
                    lat = (float(start.get("PositionLat")) + float(end.get("PositionLat"))) / 2.0
                    lon = (float(start.get("PositionLon")) + float(end.get("PositionLon"))) / 2.0
                    points.append(TrafficPoint(lat=lat, lon=lon, speed_kmh=speed))
                except (TypeError, ValueError):
                    continue
        except Exception:
            continue

    return TrafficModel(points, fallback_factor=fallback)
