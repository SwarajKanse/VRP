"""Travel matrix providers with explicit fallback metadata."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Protocol

import requests

from vrp_platform.config import PlatformSettings
from vrp_platform.domain.entities import Depot, Order, TrafficIncident, Vehicle


@dataclass(slots=True)
class TravelMatrixResult:
    matrix_minutes: list[list[float]]
    distance_km: list[list[float]]
    metadata: dict[str, object]


class TravelMatrixProvider(Protocol):
    """Provider interface for route travel times."""

    def build(
        self,
        depot: Depot,
        orders: list[Order],
        vehicles: list[Vehicle],
        departure_minute: float,
        traffic_incidents: list[TrafficIncident] | None = None,
        consider_traffic: bool = True,
        avoid_incidents: bool = True,
    ) -> TravelMatrixResult:
        """Build time and distance matrices."""


class HaversineTravelMatrixProvider:
    """Deterministic fallback provider with traffic profile support."""

    def __init__(self, settings: PlatformSettings):
        self.settings = settings
        self._cache: dict[tuple[float, ...], float] = {}

    def build(
        self,
        depot: Depot,
        orders: list[Order],
        vehicles: list[Vehicle],
        departure_minute: float,
        traffic_incidents: list[TrafficIncident] | None = None,
        consider_traffic: bool = True,
        avoid_incidents: bool = True,
    ) -> TravelMatrixResult:
        locations = [(depot.latitude, depot.longitude)] + [(o.latitude, o.longitude) for o in orders]
        avg_speed = sum(v.average_speed_kmh for v in vehicles) / max(len(vehicles), 1)
        avg_speed = avg_speed or self.settings.default_speed_kmh
        incidents = traffic_incidents or []
        traffic_multiplier = self._traffic_multiplier(departure_minute) if consider_traffic else 1.0
        size = len(locations)
        distance = [[0.0] * size for _ in range(size)]
        matrix = [[0.0] * size for _ in range(size)]
        affected_pairs = 0
        for i in range(size):
            for j in range(i + 1, size):
                dist = self._distance(locations[i], locations[j])
                incident_multiplier = self._incident_multiplier(
                    locations[i],
                    locations[j],
                    incidents,
                    avoid_incidents,
                )
                if incident_multiplier > 1.0:
                    affected_pairs += 1
                drive = (dist / avg_speed) * 60.0 * traffic_multiplier * incident_multiplier
                distance[i][j] = distance[j][i] = dist
                matrix[i][j] = matrix[j][i] = drive
        return TravelMatrixResult(
            matrix_minutes=matrix,
            distance_km=distance,
            metadata={
                "provider": "haversine",
                "fallback_used": True,
                "traffic_multiplier": traffic_multiplier,
                "average_speed_kmh": avg_speed,
                "active_incident_count": len(incidents),
                "affected_pairs": affected_pairs,
                "incident_names": [incident.name for incident in incidents],
            },
        )

    def _distance(self, left: tuple[float, float], right: tuple[float, float]) -> float:
        key = (round(left[0], 6), round(left[1], 6), round(right[0], 6), round(right[1], 6))
        if key in self._cache:
            return self._cache[key]
        lat1, lon1 = left
        lat2, lon2 = right
        r = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(dlon / 2) ** 2
        )
        distance = r * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))
        self._cache[key] = distance
        return distance

    def _traffic_multiplier(self, departure_minute: float) -> float:
        if 7 * 60 <= departure_minute <= 10 * 60 or 17 * 60 <= departure_minute <= 20 * 60:
            return self.settings.rush_hour_multiplier
        return 1.0

    def _incident_multiplier(
        self,
        left: tuple[float, float],
        right: tuple[float, float],
        incidents: list[TrafficIncident],
        avoid_incidents: bool,
    ) -> float:
        multiplier = 1.0
        midpoint = ((left[0] + right[0]) / 2.0, (left[1] + right[1]) / 2.0)
        for incident in incidents:
            center = (incident.latitude, incident.longitude)
            touches = min(
                self._distance(left, center),
                self._distance(right, center),
                self._distance(midpoint, center),
            ) <= incident.radius_km
            if not touches:
                continue
            incident_multiplier = incident.delay_multiplier
            if avoid_incidents:
                incident_multiplier += 0.12
            multiplier *= incident_multiplier
        return multiplier


class OSRMTravelMatrixProvider:
    """OSRM matrix provider."""

    def __init__(self, settings: PlatformSettings):
        self.settings = settings

    def build(
        self,
        depot: Depot,
        orders: list[Order],
        vehicles: list[Vehicle],
        departure_minute: float,
        traffic_incidents: list[TrafficIncident] | None = None,
        consider_traffic: bool = True,
        avoid_incidents: bool = True,
    ) -> TravelMatrixResult:
        locations = [(depot.latitude, depot.longitude)] + [(o.latitude, o.longitude) for o in orders]
        coordinates = ";".join(f"{lon},{lat}" for lat, lon in locations)
        url = f"{self.settings.osrm_base_url}/table/v1/driving/{coordinates}"
        response = requests.get(url, params={"annotations": "duration,distance"}, timeout=10)
        response.raise_for_status()
        data = response.json()
        durations = data.get("durations")
        distances = data.get("distances")
        if not durations or not distances:
            raise ValueError("OSRM response missing durations or distances")
        matrix = [[value / 60.0 for value in row] for row in durations]
        distance_km = [[value / 1000.0 for value in row] for row in distances]
        fallback = HaversineTravelMatrixProvider(self.settings)
        incidents = traffic_incidents or []
        traffic_multiplier = fallback._traffic_multiplier(departure_minute) if consider_traffic else 1.0
        affected_pairs = 0
        for i in range(len(matrix)):
            for j in range(len(matrix[i])):
                if i == j:
                    continue
                incident_multiplier = fallback._incident_multiplier(
                    locations[i],
                    locations[j],
                    incidents,
                    avoid_incidents,
                )
                if incident_multiplier > 1.0:
                    affected_pairs += 1
                matrix[i][j] *= traffic_multiplier * incident_multiplier
        return TravelMatrixResult(
            matrix_minutes=matrix,
            distance_km=distance_km,
            metadata={
                "provider": "osrm",
                "fallback_used": False,
                "traffic_multiplier": traffic_multiplier,
                "active_incident_count": len(incidents),
                "affected_pairs": affected_pairs,
                "incident_names": [incident.name for incident in incidents],
            },
        )


class HybridTravelMatrixProvider:
    """OSRM first, deterministic fallback if external routing fails."""

    def __init__(self, settings: PlatformSettings):
        self.settings = settings
        self.fallback = HaversineTravelMatrixProvider(settings)
        self.osrm = OSRMTravelMatrixProvider(settings)

    def build(
        self,
        depot: Depot,
        orders: list[Order],
        vehicles: list[Vehicle],
        departure_minute: float,
        traffic_incidents: list[TrafficIncident] | None = None,
        consider_traffic: bool = True,
        avoid_incidents: bool = True,
    ) -> TravelMatrixResult:
        if not self.settings.use_osrm:
            return self.fallback.build(
                depot,
                orders,
                vehicles,
                departure_minute,
                traffic_incidents=traffic_incidents,
                consider_traffic=consider_traffic,
                avoid_incidents=avoid_incidents,
            )
        try:
            return self.osrm.build(
                depot,
                orders,
                vehicles,
                departure_minute,
                traffic_incidents=traffic_incidents,
                consider_traffic=consider_traffic,
                avoid_incidents=avoid_incidents,
            )
        except Exception as exc:
            fallback = self.fallback.build(
                depot,
                orders,
                vehicles,
                departure_minute,
                traffic_incidents=traffic_incidents,
                consider_traffic=consider_traffic,
                avoid_incidents=avoid_incidents,
            )
            fallback.metadata["fallback_reason"] = type(exc).__name__
            return fallback
