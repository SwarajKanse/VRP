"""Objective scoring."""

from __future__ import annotations

from vrp_platform.domain.enums import ObjectiveMode


class ObjectiveScorer:
    """Weighted objective scorer for route construction and reporting."""

    def __init__(self, mode: ObjectiveMode):
        self.mode = mode

    def insertion_penalty(
        self,
        added_distance_km: float,
        added_drive_min: float,
        lateness_min: float,
        emissions_kg: float,
        route_load_ratio: float,
        energy_cost: float,
        break_min: float,
        overtime_min: float,
        priority_score: float,
    ) -> float:
        if self.mode == ObjectiveMode.DISTANCE:
            return added_distance_km + lateness_min * 12 + break_min * 0.2 + overtime_min * 50
        if self.mode == ObjectiveMode.ON_TIME:
            return (
                lateness_min * 30
                + added_drive_min * 0.15
                + break_min * 0.1
                + overtime_min * 60
                - priority_score * 0.5
            )
        if self.mode == ObjectiveMode.EMISSIONS:
            return emissions_kg * 12 + energy_cost * 0.05 + lateness_min * 8 + overtime_min * 45
        if self.mode == ObjectiveMode.BALANCE:
            return (
                added_distance_km
                + route_load_ratio * 4
                + break_min * 0.3
                + lateness_min * 10
                + overtime_min * 40
            )
        return (
            energy_cost
            + added_drive_min * 0.1
            + lateness_min * 10
            + break_min * 0.15
            + overtime_min * 50
            - priority_score * 0.3
        )
