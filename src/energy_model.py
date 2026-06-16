from __future__ import annotations

import math


def kwh_from_soc(battery_kwh: float, soc_pct: float) -> float:
    return battery_kwh * max(0.0, soc_pct / 100.0)


def soc_from_kwh(battery_kwh: float, energy_kwh: float) -> float:
    if battery_kwh <= 0:
        return 0.0
    return max(0.0, min(100.0, (energy_kwh / battery_kwh) * 100.0))


def drive_energy_kwh(distance_km: float, consumption_kwh_per_km: float, traffic_factor: float = 1.0) -> float:
    # Higher congestion increases consumption (stop-and-go).
    factor = max(0.85, min(1.35, 1.0 + (1.0 - traffic_factor) * 0.25))
    return distance_km * consumption_kwh_per_km * factor


def effective_charge_power_kw(station_power_kw: float, current_soc_pct: float, charge_efficiency: float) -> float:
    # Simple taper: fast above 80% SOC, slower near top.
    taper = 1.0
    if current_soc_pct >= 80:
        taper = 0.45
    elif current_soc_pct >= 60:
        taper = 0.75
    return max(15.0, station_power_kw * max(0.6, charge_efficiency) * taper)


def charge_time_minutes(
    energy_kwh_needed: float,
    station_power_kw: float,
    current_soc_pct: float,
    charge_efficiency: float,
) -> float:
    if energy_kwh_needed <= 0:
        return 0.0
    power = effective_charge_power_kw(station_power_kw, current_soc_pct, charge_efficiency)
    return (energy_kwh_needed / power) * 60.0


def expected_wait_minutes(available: int, occupied: int) -> float:
    if available > 0:
        return 3.0
    if occupied <= 0:
        return 8.0
    return min(35.0, 8.0 + occupied * 4.5)


def drive_minutes(distance_km: float, avg_speed_kmh: float, traffic_factor: float) -> float:
    speed = max(12.0, avg_speed_kmh * max(0.45, min(1.2, traffic_factor)))
    return (distance_km / speed) * 60.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * radius * math.atan2(math.sqrt(a), math.sqrt(1 - a))
