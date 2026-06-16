from __future__ import annotations

from .planner import TripConfig, plan_route

__all__ = ["TripConfig", "plan_route", "build_trip_output"]


def build_trip_output(*args, **kwargs):
    """Backward-compatible alias."""
    return plan_route(*args, **kwargs)
