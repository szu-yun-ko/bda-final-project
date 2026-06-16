from __future__ import annotations

import hashlib
import json
import pickle
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .energy_model import drive_minutes, haversine_km

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cache"
OSRM_BASE = "https://router.project-osrm.org/route/v1/driving"


@dataclass
class RouteLeg:
    distance_km: float
    drive_minutes: float
    polyline: list[list[float]]  # [[lon, lat], ...]


class RoadRouter:
    def __init__(self, use_osm: bool = True) -> None:
        self.use_osm = use_osm
        self._graph = None
        self._bbox: tuple[float, float, float, float] | None = None
        self._backend = "haversine"

    def _bbox_for_points(self, points: list[tuple[float, float]], pad: float = 0.12) -> tuple[float, float, float, float]:
        lats = [p[0] for p in points]
        lons = [p[1] for p in points]
        return (max(lats) + pad, min(lats) - pad, max(lons) + pad, min(lons) - pad)

    def _cache_path(self, bbox: tuple[float, float, float, float]) -> Path:
        key = hashlib.md5(str(bbox).encode()).hexdigest()[:12]
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        return CACHE_DIR / f"osm_graph_{key}.pkl"

    def _osrm_cache_path(self, origin: tuple[float, float], dest: tuple[float, float]) -> Path:
        key = hashlib.md5(f"{origin}|{dest}".encode()).hexdigest()[:16]
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        return CACHE_DIR / f"osrm_{key}.json"

    def _load_graph(self, bbox: tuple[float, float, float, float]) -> bool:
        north, south, east, west = bbox
        # Local OSM graph only for compact trips; island-scale routes use OSRM.
        span_lat = north - south
        span_lon = east - west
        if span_lat > 1.2 or span_lon > 1.2:
            return False

        cache = self._cache_path(bbox)
        if cache.exists():
            try:
                with cache.open("rb") as f:
                    self._graph = pickle.load(f)
                self._bbox = bbox
                return True
            except Exception:
                pass

        if not self.use_osm:
            return False

        try:
            import osmnx as ox

            self._graph = ox.graph_from_bbox(north, south, east, west, network_type="drive", simplify=True)
            self._graph = ox.add_edge_speeds(self._graph)
            self._graph = ox.add_edge_travel_times(self._graph)
            with cache.open("wb") as f:
                pickle.dump(self._graph, f)
            self._bbox = bbox
            return True
        except Exception:
            self._graph = None
            return False

    def prepare(self, points: list[tuple[float, float]]) -> str:
        bbox = self._bbox_for_points(points)
        if self._load_graph(bbox):
            self._backend = "osm"
            return "osm"
        if self.use_osm:
            self._backend = "osrm"
            return "osrm"
        self._backend = "haversine"
        return "haversine"

    def _straight_polyline(self, origin: tuple[float, float], dest: tuple[float, float], n: int = 12) -> list[list[float]]:
        lat1, lon1 = origin
        lat2, lon2 = dest
        return [[lon1 + (lon2 - lon1) * i / n, lat1 + (lat2 - lat1) * i / n] for i in range(n + 1)]

    def _route_osmnx(
        self,
        origin: tuple[float, float],
        dest: tuple[float, float],
        traffic_factor: float,
    ) -> RouteLeg | None:
        if self._graph is None:
            return None
        try:
            import osmnx as ox

            o_node = ox.nearest_nodes(self._graph, origin[1], origin[0])
            d_node = ox.nearest_nodes(self._graph, dest[1], dest[0])
            path = ox.shortest_path(self._graph, o_node, d_node, weight="travel_time")
            route_gdf = ox.routing.route_to_gdf(self._graph, path)
            distance_m = float(route_gdf["length"].sum())
            travel_s = float(route_gdf["travel_time"].sum())
            coords: list[list[float]] = []
            for geom in route_gdf.geometry:
                if geom is None:
                    continue
                if geom.geom_type == "LineString":
                    coords.extend([[x, y] for x, y in geom.coords])
                elif geom.geom_type == "MultiLineString":
                    for part in geom.geoms:
                        coords.extend([[x, y] for x, y in part.coords])
            if not coords:
                return None
            return RouteLeg(
                distance_km=distance_m / 1000.0,
                drive_minutes=(travel_s / 60.0) / max(0.5, traffic_factor),
                polyline=coords,
            )
        except Exception:
            return None

    def _route_osrm(
        self,
        origin: tuple[float, float],
        dest: tuple[float, float],
        traffic_factor: float,
    ) -> RouteLeg | None:
        cache = self._osrm_cache_path(origin, dest)
        if cache.exists():
            try:
                payload = json.loads(cache.read_text(encoding="utf-8"))
                route = payload["routes"][0]
                coords = route["geometry"]["coordinates"]
                return RouteLeg(
                    distance_km=float(route["distance"]) / 1000.0,
                    drive_minutes=(float(route["duration"]) / 60.0) / max(0.5, traffic_factor),
                    polyline=coords,
                )
            except Exception:
                pass

        lon1, lat1 = origin[1], origin[0]
        lon2, lat2 = dest[1], dest[0]
        url = f"{OSRM_BASE}/{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson"
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            if payload.get("code") != "Ok" or not payload.get("routes"):
                return None
            cache.write_text(json.dumps(payload), encoding="utf-8")
            route = payload["routes"][0]
            coords = route["geometry"]["coordinates"]
            return RouteLeg(
                distance_km=float(route["distance"]) / 1000.0,
                drive_minutes=(float(route["duration"]) / 60.0) / max(0.5, traffic_factor),
                polyline=coords,
            )
        except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError):
            return None

    def route(
        self,
        origin: tuple[float, float],
        dest: tuple[float, float],
        avg_speed_kmh: float,
        traffic_factor: float,
    ) -> RouteLeg:
        if self.use_osm:
            osm_leg = self._route_osmnx(origin, dest, traffic_factor)
            if osm_leg is not None:
                return osm_leg
            osrm_leg = self._route_osrm(origin, dest, traffic_factor)
            if osrm_leg is not None:
                return osrm_leg

        km = haversine_km(origin[0], origin[1], dest[0], dest[1]) * 1.28
        return RouteLeg(
            distance_km=km,
            drive_minutes=drive_minutes(km, avg_speed_kmh, traffic_factor),
            polyline=self._straight_polyline(origin, dest),
        )


def enrich_route_polylines(
    route_plan: dict,
    waypoint_coords: dict[str, tuple[float, float]],
    avg_speed_kmh: float,
    traffic_factor_fn: Callable[[tuple[float, float], tuple[float, float]], float] | None = None,
) -> str:
    """Replace straight-line legs with road-following geometry for the selected route."""
    router = RoadRouter(use_osm=True)
    backend = "haversine"
    legs = route_plan.get("legs") or []
    if not legs:
        return backend

    total_drive = 0.0
    for leg in legs:
        from_id = str(leg.get("from"))
        to_id = str(leg.get("to"))
        if from_id not in waypoint_coords or to_id not in waypoint_coords:
            continue
        origin = waypoint_coords[from_id]
        dest = waypoint_coords[to_id]
        tf = traffic_factor_fn(origin, dest) if traffic_factor_fn else 0.9
        road = router.route(origin, dest, avg_speed_kmh, tf)
        if len(road.polyline) > 20:
            backend = "osrm"
        leg["polyline"] = road.polyline
        leg["distance_km_est"] = round(road.distance_km, 2)
        leg["drive_minutes_est"] = round(road.drive_minutes, 2)
        leg["traffic_factor"] = round(tf, 3)
        total_drive += road.drive_minutes

    charge_wait = 0.0
    for ev in route_plan.get("charging_events") or []:
        charge_wait += float(ev.get("wait_minutes_est") or 0) + float(ev.get("charge_minutes_est") or 0)
    if legs:
        route_plan["total_time_minutes_est"] = round(total_drive + charge_wait, 2)
    return backend
