"""Deterministic fallback optimizer for degraded planning mode."""

from __future__ import annotations

import math
import uuid

from vrp_platform.domain.entities import (
    Depot,
    Order,
    RouteLeg,
    RoutePlan,
    Shift,
    SolveRequest,
    SolveResponse,
    Stop,
    Vehicle,
    Violation,
)
from vrp_platform.integrations.travel import TravelMatrixProvider


class FallbackSolver:
    """Simple nearest-neighbor fallback used when the main optimizer fails."""

    def __init__(self, travel_provider: TravelMatrixProvider):
        self.travel_provider = travel_provider

    def solve(self, request: SolveRequest) -> SolveResponse:
        if not request.depots:
            raise ValueError("At least one depot is required")
        if not request.vehicles:
            raise ValueError("At least one vehicle is required")

        run_id = f"fallback-{uuid.uuid4().hex[:10]}"
        depot = request.depots[0]
        travel = self.travel_provider.build(
            depot=depot,
            orders=request.orders,
            vehicles=request.vehicles,
            departure_minute=request.constraints.departure_minute,
            traffic_incidents=request.traffic_incidents,
            consider_traffic=request.constraints.consider_live_traffic,
            avoid_incidents=request.constraints.avoid_incidents,
        )
        shifts = {shift.vehicle_id: shift for shift in request.shifts}
        planned_order_ids: set[str] = set()
        routes: list[RoutePlan] = []

        for route_number, vehicle in enumerate(request.vehicles, start=1):
            route = self._build_vehicle_route(
                run_id=run_id,
                route_number=route_number,
                vehicle=vehicle,
                depot=depot,
                orders=request.orders,
                travel_minutes=travel.matrix_minutes,
                distance_km=travel.distance_km,
                shift=shifts.get(vehicle.id),
                request=request,
                planned_order_ids=planned_order_ids,
            )
            if route is not None:
                routes.append(route)

        unassigned = self._build_unassigned(request.orders, request.vehicles, planned_order_ids)
        warnings = ["Fallback solver used; route quality may be reduced."]
        if travel.metadata.get("fallback_used"):
            warnings.append("Deterministic travel fallback is active; ETA confidence is reduced.")

        return SolveResponse(
            run_id=run_id,
            routes=routes,
            unassigned_orders=unassigned,
            objective_breakdown=self._objective_breakdown(routes),
            validation_warnings=warnings,
            packing_status={
                "solver": "fallback_nearest_neighbor",
                "planned_orders": len(planned_order_ids),
                "unassigned_orders": len(unassigned),
            },
            metadata={
                "solver": "fallback_nearest_neighbor",
                "travel_provider": travel.metadata,
                "orders_considered": len(request.orders),
                "orders_planned": len(planned_order_ids),
                "unassigned_count": len(unassigned),
            },
        )

    def _build_vehicle_route(
        self,
        run_id: str,
        route_number: int,
        vehicle: Vehicle,
        depot: Depot,
        orders: list[Order],
        travel_minutes: list[list[float]],
        distance_km: list[list[float]],
        shift: Shift | None,
        request: SolveRequest,
        planned_order_ids: set[str],
    ) -> RoutePlan | None:
        remaining_weight = vehicle.capacity_kg
        remaining_volume = vehicle.capacity_volume_m3
        current_time = shift.start_minute if shift is not None else request.constraints.departure_minute
        current_index = 0
        continuous_drive = 0.0
        total_distance = 0.0
        total_drive = 0.0
        total_service = 0.0
        total_break = 0.0
        stops: list[Stop] = []
        legs: list[RouteLeg] = []
        previous_stop_id = "depot"
        route_id = f"{run_id}-route-{route_number}"
        route_limit = shift.end_minute if shift is not None else request.constraints.departure_minute + vehicle.max_shift_minutes

        while True:
            best_candidate: tuple[float, int, float, float, float, float, float, float] | None = None
            for order_index, order in enumerate(orders):
                if order.id in planned_order_ids:
                    continue
                if not self._vehicle_can_serve_order(vehicle, order):
                    continue
                if order.demand_kg > remaining_weight or order.volume_m3 > remaining_volume:
                    continue

                matrix_index = order_index + 1
                drive_min = travel_minutes[current_index][matrix_index]
                break_min, resumed_drive = self._breaks_for_leg(
                    continuous_drive,
                    drive_min,
                    vehicle,
                    request.constraints.enforce_breaks,
                )
                arrival_minute = current_time + break_min + drive_min
                service_start = max(arrival_minute, order.time_window_start_min)
                if request.constraints.enforce_time_windows and service_start > order.time_window_end_min:
                    continue
                departure_minute = service_start + order.service_time_min
                projected_return = departure_minute + travel_minutes[matrix_index][0]
                if request.constraints.enforce_shift_time and projected_return > route_limit:
                    continue

                candidate = (
                    distance_km[current_index][matrix_index],
                    order_index,
                    break_min,
                    resumed_drive,
                    arrival_minute,
                    service_start,
                    departure_minute,
                    drive_min,
                )
                if best_candidate is None or candidate[0] < best_candidate[0]:
                    best_candidate = candidate

            if best_candidate is None:
                break

            (
                leg_distance,
                order_index,
                break_min,
                _resumed_drive,
                arrival_minute,
                service_start,
                departure_minute,
                drive_min,
            ) = best_candidate
            order = orders[order_index]
            stop_id = f"{route_id}-stop-{len(stops) + 1}"

            legs.append(
                RouteLeg(
                    from_stop_id=previous_stop_id,
                    to_stop_id=stop_id,
                    distance_km=leg_distance,
                    travel_time_min=drive_min,
                    eta_minute=arrival_minute,
                )
            )
            stops.append(
                Stop(
                    stop_id=stop_id,
                    order_id=order.id,
                    sequence=len(stops) + 1,
                    arrival_minute=arrival_minute,
                    service_start_minute=service_start,
                    departure_minute=departure_minute,
                    distance_from_previous_km=leg_distance,
                    travel_time_from_previous_min=drive_min,
                )
            )

            planned_order_ids.add(order.id)
            remaining_weight -= order.demand_kg
            remaining_volume -= order.volume_m3
            current_index = order_index + 1
            current_time = departure_minute
            continuous_drive = 0.0
            total_distance += leg_distance
            total_drive += drive_min
            total_service += order.service_time_min
            total_break += break_min
            previous_stop_id = stop_id

        if not stops:
            return None

        return_break_min, _ = self._breaks_for_leg(
            continuous_drive,
            travel_minutes[current_index][0],
            vehicle,
            request.constraints.enforce_breaks,
        )
        total_break += return_break_min
        total_drive += travel_minutes[current_index][0]
        total_distance += distance_km[current_index][0]
        return_eta = current_time + return_break_min + travel_minutes[current_index][0]
        legs.append(
            RouteLeg(
                from_stop_id=previous_stop_id,
                to_stop_id="depot-return",
                distance_km=distance_km[current_index][0],
                travel_time_min=travel_minutes[current_index][0],
                eta_minute=return_eta,
            )
        )

        fuel_used = total_distance * vehicle.fuel_consumption_per_km
        energy_cost = fuel_used * vehicle.energy_unit_cost
        labor_hours = (total_drive + total_service + total_break) / 60.0
        return RoutePlan(
            route_id=route_id,
            vehicle_id=vehicle.id,
            depot_id=depot.id,
            stops=stops,
            legs=legs,
            total_distance_km=total_distance,
            total_drive_min=total_drive,
            total_service_min=total_service,
            total_cost=(total_distance * vehicle.cost_per_km) + energy_cost + (labor_hours * vehicle.labor_cost_per_hour),
            total_emissions_kg=total_distance * vehicle.emissions_kg_per_km,
            total_energy_cost=energy_cost,
            fuel_used=fuel_used,
            total_break_min=total_break,
        )

    def _build_unassigned(
        self,
        orders: list[Order],
        vehicles: list[Vehicle],
        planned_order_ids: set[str],
    ) -> list[Violation]:
        issues: list[Violation] = []
        for order in orders:
            if order.id in planned_order_ids:
                continue
            eligible = [vehicle for vehicle in vehicles if self._vehicle_can_serve_order(vehicle, order)]
            if not eligible:
                issues.append(
                    Violation(
                        code="DIMENSION_EXCEEDED",
                        order_id=order.id,
                        message="Order dimensions do not fit any active vehicle type.",
                    )
                )
                continue
            if order.demand_kg > max(vehicle.capacity_kg for vehicle in eligible):
                issues.append(
                    Violation(
                        code="CAPACITY_EXCEEDED",
                        order_id=order.id,
                        message="Order demand exceeds every vehicle capacity.",
                    )
                )
                continue
            if order.volume_m3 > max(vehicle.capacity_volume_m3 for vehicle in eligible):
                issues.append(
                    Violation(
                        code="VOLUME_EXCEEDED",
                        order_id=order.id,
                        message="Order volume exceeds every vehicle cargo volume.",
                    )
                )
                continue
            issues.append(
                Violation(
                    code="NO_FALLBACK_FEASIBLE_INSERTION",
                    order_id=order.id,
                    message="Fallback routing could not place the order within remaining route limits.",
                )
            )
        return issues

    def _vehicle_can_serve_order(self, vehicle: Vehicle, order: Order) -> bool:
        order_dims = order.package_dimensions_m
        vehicle_dims = (vehicle.cargo_length_m, vehicle.cargo_width_m, vehicle.cargo_height_m)
        if order.orientation_locked:
            return all(order_dim <= vehicle_dim for order_dim, vehicle_dim in zip(order_dims, vehicle_dims))
        return all(
            order_dim <= vehicle_dim
            for order_dim, vehicle_dim in zip(sorted(order_dims), sorted(vehicle_dims))
        )

    def _breaks_for_leg(
        self,
        continuous_drive_min: float,
        leg_drive_min: float,
        vehicle: Vehicle,
        enforce_breaks: bool,
    ) -> tuple[float, float]:
        if not enforce_breaks or vehicle.max_continuous_drive_min <= 0 or leg_drive_min <= 0:
            return 0.0, continuous_drive_min + leg_drive_min
        projected = continuous_drive_min + leg_drive_min
        break_count = int(max(0.0, math.floor((projected - 1e-6) / vehicle.max_continuous_drive_min)))
        if break_count <= 0:
            return 0.0, projected
        return break_count * vehicle.required_break_min, leg_drive_min

    def _objective_breakdown(self, routes: list[RoutePlan]) -> dict[str, float]:
        return {
            "total_distance_km": round(sum(route.total_distance_km for route in routes), 2),
            "total_cost": round(sum(route.total_cost for route in routes), 2),
            "total_emissions_kg": round(sum(route.total_emissions_kg for route in routes), 2),
            "total_energy_cost": round(sum(route.total_energy_cost for route in routes), 2),
            "total_break_min": round(sum(route.total_break_min for route in routes), 2),
        }
