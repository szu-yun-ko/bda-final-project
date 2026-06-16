from __future__ import annotations

from pathlib import Path

import folium


def build_route_map(result: dict, out_html: str = "outputs/route_map.html") -> Path:
    trip = result["trip"]
    origin = trip["origin"]
    destination = trip["destination"]
    center = [(origin["lat"] + destination["lat"]) / 2, (origin["lon"] + destination["lon"]) / 2]
    m = folium.Map(location=center, zoom_start=9)

    folium.Marker([origin["lat"], origin["lon"]], popup="Origin", icon=folium.Icon(color="green")).add_to(m)
    folium.Marker([destination["lat"], destination["lon"]], popup="Destination", icon=folium.Icon(color="red")).add_to(m)

    for stop in result.get("route_plan", {}).get("stops", []):
        folium.Marker(
            [stop["lat"], stop["lon"]],
            popup=stop.get("name", "Charger"),
            icon=folium.Icon(color="blue", icon="bolt", prefix="fa"),
        ).add_to(m)

    for leg in result.get("route_plan", {}).get("legs", []):
        poly = leg.get("polyline") or []
        if len(poly) >= 2:
            folium.PolyLine([[p[1], p[0]] for p in poly], color="#2563eb", weight=5, opacity=0.8).add_to(m)

    path = Path(out_html)
    path.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(path))
    return path
