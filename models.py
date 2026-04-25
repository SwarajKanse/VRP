"""Shared data models for the Tkinter VRP mini-project."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class GeoPoint:
    latitude: float
    longitude: float


@dataclass(slots=True)
class Node:
    node_id: str
    label: str
    point: GeoPoint
    kind: str = "order"
    demand: float = 0.0


@dataclass(slots=True)
class RouteSummary:
    name: str
    node_ids: list[str]
    distance_km: float
    color: str = "#1f4f6f"
    style: str = "final"
    load: float = 0.0
    capacity: float = 0.0


@dataclass(slots=True)
class RouteOutline:
    name: str
    node_ids: list[str]
    score: float
    reason: str
    style: str = "selected"
    color: str = "#c96a2d"


@dataclass(slots=True)
class SolveStep:
    index: int
    title: str
    detail: str
    chosen: RouteOutline | None = None
    alternatives: list[RouteOutline] = field(default_factory=list)
    focus_node_ids: list[str] = field(default_factory=list)
    context_routes: list[RouteSummary] = field(default_factory=list)


@dataclass(slots=True)
class SolveResult:
    baseline_routes: list[RouteSummary]
    savings_routes: list[RouteSummary]
    final_routes: list[RouteSummary]
    steps: list[SolveStep]
    baseline_distance_km: float
    savings_distance_km: float
    final_distance_km: float
    vehicle_count: int


@dataclass(slots=True)
class AnimationRoute:
    name: str
    color: str
    node_ids: list[str]
    distance_km: float = 0.0
