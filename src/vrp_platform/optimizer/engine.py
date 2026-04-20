"""Pure Python staged optimizer with repair and local search."""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass

from vrp_platform.domain.entities import (
    ConstraintSet,
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
from vrp_platform.domain.enums import OrderStatus
from vrp_platform.integrations.travel import TravelMatrixProvider
from vrp_platform.optimizer.objectives import ObjectiveScorer


@dataclass(slots=True)
class _RouteState:
    vehicle: Vehicle
    depot: Depot
    order_indexes: list[int]


@dataclass(slots=True)
class _RouteMetrics:
    distance_km: float
    drive_min: float
    service_min: float
    break_min: float
    lateness_min: float
    energy_cost: float
    fuel_used: float
    emissions_kg: float
    load_ratio: float
    overtime_min: float
    end_minute: float


class RouteOptimizer:
    """Build and improve routes using regret insertion and local search."""

    def __init__(self, travel_provider: TravelMatrixProvider):
        self.travel_provider = travel_provider

    def solve(self, request: SolveRequest) -> SolveResponse:
        if not request.depots:
            raise ValueError("At least one depot is required")
        self._validate_request(request)
        run_id = f"run-{uuid.uuid4().hex[:10]}"
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
        scorer = ObjectiveScorer(request.objective)
        shifts = {shift.vehicle_id: shift for shift in request.shifts}
        feasible, blocked = self._feasibility_precheck(request, travel.distance_km)
        route_states = [_RouteState(vehicle=v, depot=depot, order_indexes=[]) for v in request.vehicles]
        unassigned = blocked[:]
        repair_candidates: list[int] = []

        pending = feasible[:]
        while pending:
            chosen_order = None
            chosen_route_index = None
            chosen_position = None
            chosen_cost = math.inf
            chosen_regret = -math.inf

            for order_idx in pending:
                evaluations = self._evaluate_insertions(
                    request=request,
                    travel_minutes=travel.matrix_minutes,
                    distance_km=travel.distance_km,
                    route_states=route_states,
                    scorer=scorer,
                    order_idx=order_idx,
                    shift_lookup=shifts,
                )
                if not evaluations:
                    continue
                evaluations.sort(key=lambda item: item[0])
                best_cost, route_index, position = evaluations[0]
                regret = float("inf") if len(evaluations) == 1 else evaluations[1][0] - best_cost
                if regret > chosen_regret or (math.isclose(regret, chosen_regret) and best_cost < chosen_cost):
                    chosen_order = order_idx
                    chosen_route_index = route_index
                    chosen_position = position
                    chosen_cost = best_cost
                    chosen_regret = regret

            if chosen_order is None or chosen_route_index is None or chosen_position is None:
                repair_candidates = pending[:]
                break

            route_states[chosen_route_index].order_indexes.insert(chosen_position, chosen_order)
            pending.remove(chosen_order)

        self._run_local_search(request, route_states, travel.matrix_minutes, travel.distance_km, shifts, scorer)
        if repair_candidates:
            remaining = self._repair_unassigned(
                repair_candidates,
                request,
                route_states,
                travel.matrix_minutes,
                travel.distance_km,
                shifts,
                scorer,
            )
            for order_idx in remaining:
                unassigned.append(
                    Violation(
                        code="NO_FEASIBLE_INSERTION",
                        order_id=request.orders[order_idx].id,
                        message="No feasible insertion found after repair attempts with current fleet, capacity, or shift limits.",
                    )
                )
        route_plans = self._build_route_plans(
            run_id=run_id,
            request=request,
            depot=depot,
            route_states=route_states,
            travel_minutes=travel.matrix_minutes,
            distance_km=travel.distance_km,
            shifts=shifts,
        )
        objective_breakdown = self._objective_breakdown(route_plans)
        packing_status = self._packing_status(route_plans, request)
        metadata = {
            "travel_provider": travel.metadata,
            "orders_considered": len(request.orders),
            "orders_planned": sum(len(route.stops) for route in route_plans),
            "unassigned_count": len(unassigned),
        }
        warnings = []
        if travel.metadata.get("fallback_used"):
            warnings.append("Fallback travel-time model used; ETA confidence is reduced.")
        return SolveResponse(
            run_id=run_id,
            routes=route_plans,
            unassigned_orders=unassigned,
            objective_breakdown=objective_breakdown,
            validation_warnings=warnings,
            packing_status=packing_status,
            metadata=metadata,
        )

    def _validate_request(self, request: SolveRequest) -> None:
        if not request.vehicles:
            raise ValueError("At least one vehicle is required")
        if not request.orders:
            raise ValueError("At least one order is required")
        for depot in request.depots:
            if not -90.0 <= depot.latitude <= 90.0:
                raise ValueError(f"Invalid depot latitude: {depot.latitude}")
            if not -180.0 <= depot.longitude <= 180.0:
                raise ValueError(f"Invalid depot longitude: {depot.longitude}")
        for vehicle in request.vehicles:
            if vehicle.capacity_kg <= 0 or vehicle.capacity_volume_m3 <= 0:
                raise ValueError(f"Vehicle {vehicle.id} has non-positive capacity")
            if vehicle.average_speed_kmh <= 0:
                raise ValueError(f"Vehicle {vehicle.id} has invalid average speed")
            if vehicle.max_continuous_drive_min < 0 or vehicle.required_break_min < 0:
                raise ValueError(f"Vehicle {vehicle.id} has invalid break configuration")
        for order in request.orders:
            if not -90.0 <= order.latitude <= 90.0:
                raise ValueError(f"Invalid order latitude: {order.latitude}")
            if not -180.0 <= order.longitude <= 180.0:
                raise ValueError(f"Invalid order longitude: {order.longitude}")
            if order.demand_kg < 0 or order.volume_m3 < 0:
                raise ValueError(f"Order {order.external_ref} has negative demand or volume")
            if order.service_time_min < 0:
                raise ValueError(f"Order {order.external_ref} has negative service time")
            if order.time_window_start_min > order.time_window_end_min:
                raise ValueError(f"Order {order.external_ref} has invalid time window")

    def _feasibility_precheck(
        self,
        request: SolveRequest,
        distance_km: list[list[float]],
    ) -> tuple[list[int], list[Violation]]:
        feasible = []
        blocked: list[Violation] = []
        for order_idx, order in enumerate(request.orders):
            eligible_vehicles = [vehicle for vehicle in request.vehicles if self._vehicle_can_serve_order(vehicle, order)]
            if not eligible_vehicles:
                blocked.append(
                    Violation(
                        code="DIMENSION_EXCEEDED",
                        order_id=order.id,
                        message="Order dimensions do not fit any active vehicle type.",
                    )
                )
                continue
            max_capacity = max((vehicle.capacity_kg for vehicle in eligible_vehicles), default=0.0)
            max_volume = max((vehicle.capacity_volume_m3 for vehicle in eligible_vehicles), default=0.0)
            if order.demand_kg > max_capacity:
                blocked.append(
                    Violation(
                        code="CAPACITY_EXCEEDED",
                        order_id=order.id,
                        message="Order demand exceeds every vehicle capacity.",
                    )
                )
                continue
            if order.volume_m3 > max_volume:
                blocked.append(
                    Violation(
                        code="VOLUME_EXCEEDED",
                        order_id=order.id,
                        message="Order volume exceeds every vehicle cargo volume.",
                    )
                )
                continue
            travel_idx = order_idx + 1
            if request.constraints.enforce_time_windows and distance_km[0][travel_idx] > 1000:
                blocked.append(
                    Violation(
                        code="TIME_WINDOW_INFEASIBLE",
                        order_id=order.id,
                        message="Order is too far from depot to respect the configured time window.",
                    )
                )
                continue
            feasible.append(order_idx)
        return feasible, blocked

    def _evaluate_insertions(
        self,
        request: SolveRequest,
        travel_minutes: list[list[float]],
        distance_km: list[list[float]],
        route_states: list[_RouteState],
        scorer: ObjectiveScorer,
        order_idx: int,
        shift_lookup: dict[str, Shift],
    ) -> list[tuple[float, int, int]]:
        evaluations: list[tuple[float, int, int]] = []
        for route_index, state in enumerate(route_states):
            if not self._vehicle_can_serve_order(state.vehicle, request.orders[order_idx]):
                continue
            for position in range(len(state.order_indexes) + 1):
                candidate = state.order_indexes[:]
                candidate.insert(position, order_idx)
                if not self._route_feasible(
                    state.vehicle,
                    candidate,
                    request.orders,
                    travel_minutes,
                    distance_km,
                    shift_lookup.get(state.vehicle.id),
                    request.constraints,
                ):
                    continue
                metrics = self._route_metrics(
                    state.vehicle,
                    candidate,
                    request.orders,
                    travel_minutes,
                    distance_km,
                    shift_lookup.get(state.vehicle.id),
                    request.constraints,
                )
                penalty = scorer.insertion_penalty(
                    added_distance_km=metrics.distance_km,
                    added_drive_min=metrics.drive_min,
                    lateness_min=metrics.lateness_min,
                    emissions_kg=metrics.emissions_kg,
                    route_load_ratio=metrics.load_ratio,
                    energy_cost=metrics.energy_cost,
                    break_min=metrics.break_min,
                    overtime_min=metrics.overtime_min,
                    priority_score=self._priority_score(candidate, request.orders),
                )
                evaluations.append((penalty, route_index, position))
        return evaluations

    def _route_feasible(
        self,
        vehicle: Vehicle,
        order_indexes: list[int],
        orders: list[Order],
        travel_minutes: list[list[float]],
        distance_km: list[list[float]],
        shift: Shift | None,
        constraints: ConstraintSet,
    ) -> bool:
        if self._route_weight(order_indexes, orders) > vehicle.capacity_kg:
            return False
        if self._route_volume(order_indexes, orders) > vehicle.capacity_volume_m3:
            return False
        if any(not self._vehicle_can_serve_order(vehicle, orders[order_idx]) for order_idx in order_indexes):
            return False
        metrics = self._route_metrics(vehicle, order_indexes, orders, travel_minutes, distance_km, shift, constraints)
        route_limit = shift.end_minute if shift else constraints.departure_minute + vehicle.max_shift_minutes
        if constraints.enforce_shift_time and metrics.end_minute > route_limit:
            return False
        if constraints.enforce_time_windows and metrics.lateness_min > 0:
            return False
        return True

    def _run_local_search(
        self,
        request: SolveRequest,
        routes: list[_RouteState],
        travel_minutes: list[list[float]],
        distance_km: list[list[float]],
        shifts: dict[str, Shift],
        scorer: ObjectiveScorer,
    ) -> None:
        for state in routes:
            improved = True
            while improved:
                improved = self._two_opt(
                    state,
                    request.orders,
                    travel_minutes,
                    distance_km,
                    shifts.get(state.vehicle.id),
                    request.constraints,
                    scorer,
                )
        self._relocate(
            routes,
            request.orders,
            travel_minutes,
            distance_km,
            shifts,
            request.constraints,
            scorer,
        )
        self._swap(
            routes,
            request.orders,
            travel_minutes,
            distance_km,
            shifts,
            request.constraints,
            scorer,
        )
        self._cross_exchange(
            routes,
            request.orders,
            travel_minutes,
            distance_km,
            shifts,
            request.constraints,
            scorer,
        )

    def _two_opt(
        self,
        state: _RouteState,
        orders: list[Order],
        travel_minutes: list[list[float]],
        distance_km: list[list[float]],
        shift: Shift | None,
        constraints: ConstraintSet,
        scorer: ObjectiveScorer,
    ) -> bool:
        best = state.order_indexes[:]
        best_score = self._route_penalty(
            state.vehicle, best, orders, travel_minutes, distance_km, shift, constraints, scorer
        )
        for i in range(len(best) - 1):
            for j in range(i + 1, len(best)):
                candidate = best[:i] + list(reversed(best[i : j + 1])) + best[j + 1 :]
                if not self._route_feasible(
                    state.vehicle, candidate, orders, travel_minutes, distance_km, shift, constraints
                ):
                    continue
                candidate_score = self._route_penalty(
                    state.vehicle, candidate, orders, travel_minutes, distance_km, shift, constraints, scorer
                )
                if candidate_score + 1e-6 < best_score:
                    state.order_indexes = candidate
                    return True
        return False

    def _relocate(
        self,
        routes: list[_RouteState],
        orders: list[Order],
        travel_minutes: list[list[float]],
        distance_km: list[list[float]],
        shifts: dict[str, Shift],
        constraints: ConstraintSet,
        scorer: ObjectiveScorer,
    ) -> None:
        for left in routes:
            for right in routes:
                if left is right or not left.order_indexes:
                    continue
                baseline = self._route_penalty(
                    left.vehicle,
                    left.order_indexes,
                    orders,
                    travel_minutes,
                    distance_km,
                    shifts.get(left.vehicle.id),
                    constraints,
                    scorer,
                ) + self._route_penalty(
                    right.vehicle,
                    right.order_indexes,
                    orders,
                    travel_minutes,
                    distance_km,
                    shifts.get(right.vehicle.id),
                    constraints,
                    scorer,
                )
                for index, order_idx in enumerate(left.order_indexes[:]):
                    reduced = left.order_indexes[:index] + left.order_indexes[index + 1 :]
                    for insert_at in range(len(right.order_indexes) + 1):
                        expanded = right.order_indexes[:]
                        expanded.insert(insert_at, order_idx)
                        if not self._route_feasible(
                            left.vehicle,
                            reduced,
                            orders,
                            travel_minutes,
                            distance_km,
                            shifts.get(left.vehicle.id),
                            constraints,
                        ):
                            continue
                        if not self._route_feasible(
                            right.vehicle,
                            expanded,
                            orders,
                            travel_minutes,
                            distance_km,
                            shifts.get(right.vehicle.id),
                            constraints,
                        ):
                            continue
                        new_total = self._route_penalty(
                            left.vehicle,
                            reduced,
                            orders,
                            travel_minutes,
                            distance_km,
                            shifts.get(left.vehicle.id),
                            constraints,
                            scorer,
                        ) + self._route_penalty(
                            right.vehicle,
                            expanded,
                            orders,
                            travel_minutes,
                            distance_km,
                            shifts.get(right.vehicle.id),
                            constraints,
                            scorer,
                        )
                        if new_total + 1e-6 < baseline:
                            left.order_indexes = reduced
                            right.order_indexes = expanded
                            return

    def _swap(
        self,
        routes: list[_RouteState],
        orders: list[Order],
        travel_minutes: list[list[float]],
        distance_km: list[list[float]],
        shifts: dict[str, Shift],
        constraints: ConstraintSet,
        scorer: ObjectiveScorer,
    ) -> None:
        for first_index, first in enumerate(routes):
            for second in routes[first_index + 1 :]:
                baseline = self._route_penalty(
                    first.vehicle,
                    first.order_indexes,
                    orders,
                    travel_minutes,
                    distance_km,
                    shifts.get(first.vehicle.id),
                    constraints,
                    scorer,
                ) + self._route_penalty(
                    second.vehicle,
                    second.order_indexes,
                    orders,
                    travel_minutes,
                    distance_km,
                    shifts.get(second.vehicle.id),
                    constraints,
                    scorer,
                )
                for i, left_order in enumerate(first.order_indexes):
                    for j, right_order in enumerate(second.order_indexes):
                        left_candidate = first.order_indexes[:]
                        right_candidate = second.order_indexes[:]
                        left_candidate[i], right_candidate[j] = right_order, left_order
                        if not self._route_feasible(
                            first.vehicle,
                            left_candidate,
                            orders,
                            travel_minutes,
                            distance_km,
                            shifts.get(first.vehicle.id),
                            constraints,
                        ):
                            continue
                        if not self._route_feasible(
                            second.vehicle,
                            right_candidate,
                            orders,
                            travel_minutes,
                            distance_km,
                            shifts.get(second.vehicle.id),
                            constraints,
                        ):
                            continue
                        new_total = self._route_penalty(
                            first.vehicle,
                            left_candidate,
                            orders,
                            travel_minutes,
                            distance_km,
                            shifts.get(first.vehicle.id),
                            constraints,
                            scorer,
                        ) + self._route_penalty(
                            second.vehicle,
                            right_candidate,
                            orders,
                            travel_minutes,
                            distance_km,
                            shifts.get(second.vehicle.id),
                            constraints,
                            scorer,
                        )
                        if new_total + 1e-6 < baseline:
                            first.order_indexes = left_candidate
                            second.order_indexes = right_candidate
                            return

    def _cross_exchange(
        self,
        routes: list[_RouteState],
        orders: list[Order],
        travel_minutes: list[list[float]],
        distance_km: list[list[float]],
        shifts: dict[str, Shift],
        constraints: ConstraintSet,
        scorer: ObjectiveScorer,
    ) -> None:
        for first_index, first in enumerate(routes):
            for second in routes[first_index + 1 :]:
                if not first.order_indexes or not second.order_indexes:
                    continue
                left_tail = first.order_indexes[-1:]
                right_tail = second.order_indexes[-1:]
                left_candidate = first.order_indexes[:-1] + right_tail
                right_candidate = second.order_indexes[:-1] + left_tail
                if not self._route_feasible(
                    first.vehicle,
                    left_candidate,
                    orders,
                    travel_minutes,
                    distance_km,
                    shifts.get(first.vehicle.id),
                    constraints,
                ):
                    continue
                if not self._route_feasible(
                    second.vehicle,
                    right_candidate,
                    orders,
                    travel_minutes,
                    distance_km,
                    shifts.get(second.vehicle.id),
                    constraints,
                ):
                    continue
                before = self._route_penalty(
                    first.vehicle,
                    first.order_indexes,
                    orders,
                    travel_minutes,
                    distance_km,
                    shifts.get(first.vehicle.id),
                    constraints,
                    scorer,
                ) + self._route_penalty(
                    second.vehicle,
                    second.order_indexes,
                    orders,
                    travel_minutes,
                    distance_km,
                    shifts.get(second.vehicle.id),
                    constraints,
                    scorer,
                )
                after = self._route_penalty(
                    first.vehicle,
                    left_candidate,
                    orders,
                    travel_minutes,
                    distance_km,
                    shifts.get(first.vehicle.id),
                    constraints,
                    scorer,
                ) + self._route_penalty(
                    second.vehicle,
                    right_candidate,
                    orders,
                    travel_minutes,
                    distance_km,
                    shifts.get(second.vehicle.id),
                    constraints,
                    scorer,
                )
                if after + 1e-6 < before:
                    first.order_indexes = left_candidate
                    second.order_indexes = right_candidate
                    return

    def _repair_unassigned(
        self,
        pending: list[int],
        request: SolveRequest,
        route_states: list[_RouteState],
        travel_minutes: list[list[float]],
        distance_km: list[list[float]],
        shifts: dict[str, Shift],
        scorer: ObjectiveScorer,
    ) -> list[int]:
        remaining = pending[:]
        improved = True
        while remaining and improved:
            improved = False
            for order_idx in remaining[:]:
                evaluations = self._evaluate_insertions(
                    request=request,
                    travel_minutes=travel_minutes,
                    distance_km=distance_km,
                    route_states=route_states,
                    scorer=scorer,
                    order_idx=order_idx,
                    shift_lookup=shifts,
                )
                if not evaluations:
                    continue
                evaluations.sort(key=lambda item: item[0])
                _, route_index, position = evaluations[0]
                route_states[route_index].order_indexes.insert(position, order_idx)
                remaining.remove(order_idx)
                improved = True
            if improved:
                self._run_local_search(request, route_states, travel_minutes, distance_km, shifts, scorer)
        return remaining

    def _build_route_plans(
        self,
        run_id: str,
        request: SolveRequest,
        depot: Depot,
        route_states: list[_RouteState],
        travel_minutes: list[list[float]],
        distance_km: list[list[float]],
        shifts: dict[str, Shift],
    ) -> list[RoutePlan]:
        plans: list[RoutePlan] = []
        for route_index, state in enumerate(route_states):
            if not state.order_indexes:
                continue
            current_time = (
                shifts.get(state.vehicle.id).start_minute
                if state.vehicle.id in shifts
                else request.constraints.departure_minute
            )
            previous = 0
            continuous_drive = 0.0
            stops: list[Stop] = []
            legs: list[RouteLeg] = []
            total_service = 0.0
            for sequence, order_idx in enumerate(state.order_indexes, start=1):
                matrix_idx = order_idx + 1
                order = request.orders[order_idx]
                travel_time = travel_minutes[previous][matrix_idx]
                travel_distance = distance_km[previous][matrix_idx]
                break_minutes, continuous_drive = self._breaks_for_leg(
                    continuous_drive,
                    travel_time,
                    state.vehicle,
                    request.constraints.enforce_breaks,
                )
                current_time += break_minutes
                arrival = current_time + travel_time
                service_start = max(arrival, order.time_window_start_min)
                departure = service_start + order.service_time_min
                stop_id = f"{run_id}-stop-{route_index + 1}-{sequence}"
                stops.append(
                    Stop(
                        stop_id=stop_id,
                        order_id=order.id,
                        sequence=sequence,
                        arrival_minute=arrival,
                        service_start_minute=service_start,
                        departure_minute=departure,
                        distance_from_previous_km=travel_distance,
                        travel_time_from_previous_min=travel_time,
                    )
                )
                legs.append(
                    RouteLeg(
                        from_stop_id=stops[-2].stop_id if len(stops) > 1 else depot.id,
                        to_stop_id=stop_id,
                        distance_km=travel_distance,
                        travel_time_min=travel_time,
                        eta_minute=arrival,
                    )
                )
                current_time = departure
                continuous_drive = 0.0
                total_service += order.service_time_min
                previous = matrix_idx
            return_distance = distance_km[previous][0]
            return_travel = travel_minutes[previous][0]
            metrics = self._route_metrics(
                state.vehicle,
                state.order_indexes,
                request.orders,
                travel_minutes,
                distance_km,
                shifts.get(state.vehicle.id),
                request.constraints,
            )
            plans.append(
                RoutePlan(
                    route_id=f"{run_id}-route-{route_index + 1}",
                    vehicle_id=state.vehicle.id,
                    depot_id=depot.id,
                    stops=stops,
                    legs=legs
                    + [
                        RouteLeg(
                            from_stop_id=stops[-1].stop_id,
                            to_stop_id=depot.id,
                            distance_km=return_distance,
                            travel_time_min=return_travel,
                            eta_minute=current_time + return_travel,
                        )
                    ],
                    total_distance_km=metrics.distance_km,
                    total_drive_min=metrics.drive_min,
                    total_service_min=total_service,
                    total_cost=(metrics.distance_km * state.vehicle.cost_per_km)
                    + metrics.energy_cost
                    + ((metrics.drive_min + total_service + metrics.break_min) / 60.0 * state.vehicle.labor_cost_per_hour),
                    total_emissions_kg=metrics.emissions_kg,
                    total_energy_cost=metrics.energy_cost,
                    fuel_used=metrics.fuel_used,
                    total_break_min=metrics.break_min,
                )
            )
            for order_idx in state.order_indexes:
                request.orders[order_idx].status = OrderStatus.PLANNED
        return plans

    def _objective_breakdown(self, routes: list[RoutePlan]) -> dict[str, float]:
        total_distance = sum(route.total_distance_km for route in routes)
        total_drive = sum(route.total_drive_min for route in routes)
        total_service = sum(route.total_service_min for route in routes)
        total_cost = sum(route.total_cost for route in routes)
        total_emissions = sum(route.total_emissions_kg for route in routes)
        total_energy = sum(route.total_energy_cost for route in routes)
        total_breaks = sum(route.total_break_min for route in routes)
        customer_count = sum(len(route.stops) for route in routes)
        return {
            "total_distance_km": round(total_distance, 3),
            "total_drive_min": round(total_drive, 3),
            "total_service_min": round(total_service, 3),
            "total_cost": round(total_cost, 2),
            "total_energy_cost": round(total_energy, 2),
            "total_emissions_kg": round(total_emissions, 3),
            "total_break_min": round(total_breaks, 2),
            "deliveries": float(customer_count),
        }

    def _packing_status(self, routes: list[RoutePlan], request: SolveRequest) -> dict[str, object]:
        route_lookup = {stop.order_id: route.vehicle_id for route in routes for stop in route.stops}
        warnings = []
        feasible_routes = 0
        for route in routes:
            vehicle = next(v for v in request.vehicles if v.id == route.vehicle_id)
            used_volume = sum(
                next(order.volume_m3 for order in request.orders if order.id == stop.order_id)
                for stop in route.stops
            )
            if used_volume <= vehicle.capacity_volume_m3:
                feasible_routes += 1
            else:
                warnings.append(f"Route {route.route_id} exceeds cargo volume.")
        return {
            "feasible_route_count": feasible_routes,
            "route_count": len(routes),
            "warnings": warnings,
            "route_lookup": route_lookup,
        }

    def _route_weight(self, order_indexes: list[int], orders: list[Order]) -> float:
        return sum(orders[index].demand_kg for index in order_indexes)

    def _route_volume(self, order_indexes: list[int], orders: list[Order]) -> float:
        return sum(orders[index].volume_m3 for index in order_indexes)

    def _route_distance(self, order_indexes: list[int], distance_km: list[list[float]]) -> float:
        if not order_indexes:
            return 0.0
        total = distance_km[0][order_indexes[0] + 1]
        for left, right in zip(order_indexes, order_indexes[1:]):
            total += distance_km[left + 1][right + 1]
        total += distance_km[order_indexes[-1] + 1][0]
        return total

    def _route_drive(self, order_indexes: list[int], travel_minutes: list[list[float]]) -> float:
        if not order_indexes:
            return 0.0
        total = travel_minutes[0][order_indexes[0] + 1]
        for left, right in zip(order_indexes, order_indexes[1:]):
            total += travel_minutes[left + 1][right + 1]
        total += travel_minutes[order_indexes[-1] + 1][0]
        return total

    def _route_lateness(
        self,
        order_indexes: list[int],
        orders: list[Order],
        travel_minutes: list[list[float]],
        departure_minute: float,
    ) -> float:
        late = 0.0
        current_time = departure_minute
        previous = 0
        for order_idx in order_indexes:
            matrix_idx = order_idx + 1
            order = orders[order_idx]
            current_time += travel_minutes[previous][matrix_idx]
            late += max(0.0, current_time - order.time_window_end_min)
            current_time = max(current_time, order.time_window_start_min) + order.service_time_min
            previous = matrix_idx
        return late

    def _route_penalty(
        self,
        vehicle: Vehicle,
        order_indexes: list[int],
        orders: list[Order],
        travel_minutes: list[list[float]],
        distance_km: list[list[float]],
        shift: Shift | None,
        constraints: ConstraintSet,
        scorer: ObjectiveScorer,
    ) -> float:
        metrics = self._route_metrics(vehicle, order_indexes, orders, travel_minutes, distance_km, shift, constraints)
        return scorer.insertion_penalty(
            added_distance_km=metrics.distance_km,
            added_drive_min=metrics.drive_min,
            lateness_min=metrics.lateness_min,
            emissions_kg=metrics.emissions_kg,
            route_load_ratio=metrics.load_ratio,
            energy_cost=metrics.energy_cost,
            break_min=metrics.break_min,
            overtime_min=metrics.overtime_min,
            priority_score=self._priority_score(order_indexes, orders),
        )

    def _route_metrics(
        self,
        vehicle: Vehicle,
        order_indexes: list[int],
        orders: list[Order],
        travel_minutes: list[list[float]],
        distance_km: list[list[float]],
        shift: Shift | None,
        constraints: ConstraintSet,
    ) -> _RouteMetrics:
        current_time = shift.start_minute if shift else constraints.departure_minute
        current_drive_time = 0.0
        break_min = 0.0
        lateness = 0.0
        service_min = 0.0
        previous = 0
        for order_idx in order_indexes:
            matrix_idx = order_idx + 1
            travel_time = travel_minutes[previous][matrix_idx]
            added_break, current_drive_time = self._breaks_for_leg(
                current_drive_time,
                travel_time,
                vehicle,
                constraints.enforce_breaks,
            )
            break_min += added_break
            current_time += added_break + travel_time
            order = orders[order_idx]
            service_start = max(current_time, order.time_window_start_min)
            lateness += max(0.0, service_start - order.time_window_end_min)
            current_time = service_start + order.service_time_min
            current_drive_time = 0.0
            service_min += order.service_time_min
            previous = matrix_idx
        return_travel = travel_minutes[previous][0] if order_indexes else 0.0
        added_break, current_drive_time = self._breaks_for_leg(
            current_drive_time,
            return_travel,
            vehicle,
            constraints.enforce_breaks,
        )
        break_min += added_break
        current_time += added_break + return_travel
        distance = self._route_distance(order_indexes, distance_km)
        drive = self._route_drive(order_indexes, travel_minutes)
        fuel_used = distance * vehicle.fuel_consumption_per_km
        energy_cost = fuel_used * vehicle.energy_unit_cost
        route_limit = shift.end_minute if shift else constraints.departure_minute + vehicle.max_shift_minutes
        return _RouteMetrics(
            distance_km=distance,
            drive_min=drive,
            service_min=service_min,
            break_min=break_min,
            lateness_min=lateness,
            energy_cost=energy_cost,
            fuel_used=fuel_used,
            emissions_kg=distance * vehicle.emissions_kg_per_km,
            load_ratio=self._route_weight(order_indexes, orders) / max(vehicle.capacity_kg, 1.0),
            overtime_min=max(0.0, current_time - route_limit),
            end_minute=current_time,
        )

    def _vehicle_can_serve_order(self, vehicle: Vehicle, order: Order) -> bool:
        order_dims = order.package_dimensions_m
        vehicle_dims = (vehicle.cargo_length_m, vehicle.cargo_width_m, vehicle.cargo_height_m)
        if order.orientation_locked:
            return all(order_dim <= vehicle_dim for order_dim, vehicle_dim in zip(order_dims, vehicle_dims))
        return all(
            order_dim <= vehicle_dim
            for order_dim, vehicle_dim in zip(sorted(order_dims), sorted(vehicle_dims))
        )

    def _priority_score(self, order_indexes: list[int], orders: list[Order]) -> float:
        return float(sum(orders[index].priority for index in order_indexes))

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
        break_min = break_count * vehicle.required_break_min
        resumed_drive = projected - (break_count * vehicle.max_continuous_drive_min)
        return break_min, resumed_drive
