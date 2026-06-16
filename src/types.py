from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Station:
    station_id: str
    name: str
    lat: float
    lon: float
    city: str
    address: str
    max_power_kw: float
    connector_count: int
    connector_types: list[str]


@dataclass
class ConnectorLive:
    station_id: str
    available_count: int
    occupied_count: int
    fault_count: int
