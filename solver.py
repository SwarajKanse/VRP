"""Explainable CVRP + multi-depot solver for the Tkinter project."""

from __future__ import annotations

import math
from dataclasses import dataclass

try:  # Support package and script-local imports.
    from .models import GeoPoint, Node, RouteOutline, RouteSummary, SolveResult, SolveStep
except ImportError:  # pragma: no cover - script entrypoint path
    from models import GeoPoint, Node, RouteOutline, RouteSummary, SolveResult, SolveStep

ROUTE_COLORS = [
    "#ff6b00",
    "#0f62fe",
    "#00a870",
    "#7c3aed",
    "#e11d48",
    "#f59e0b",
]
EPSILON = 1e-9


@dataclass(slots=True)
class _VehicleRoute:
    depot_index: int
    order_indexes: list[int]
    load: float


class ExplainableVRPSolver:
    """Capacity-constrained multi-depot VRP solver with explainable NN + 2-opt steps."""

    def __init__(self, depots: list[Node], orders: list[Node], vehicle_count: int, vehicle_capacity: float):
        if vehicle_count < 1:
            raise ValueError("Vehicle count must be at least 1")
        if vehicle_capacity <= 0:
            raise ValueError("Vehicle capacity must be positive")
        if not depots:
            raise ValueError("At least one depot is required")
        if not orders:
            raise ValueError("At least one order is required")
        if any(depot.kind != "depot" for depot in depots):
            raise ValueError("All depot nodes must have kind='depot'")
        if any(order.kind != "order" for order in orders):
            raise ValueError("All order nodes must have kind='order'")

        depot_ids = [depot.node_id for depot in depots]
        order_ids = [order.node_id for order in orders]
        if len(depot_ids) != len(set(depot_ids)):
            raise ValueError("Depot node IDs must be unique")
        if len(order_ids) != len(set(order_ids)):
            raise ValueError("Order node IDs must be unique")
        if set(depot_ids) & set(order_ids):
            raise ValueError("Depot node IDs must be different from order node IDs")

        self.depots = depots[:]
        self.orders = orders[:]
        self.vehicle_count = max(1, min(vehicle_count, len(orders)))
        self.vehicle_capacity = float(vehicle_capacity)
        self.steps: list[SolveStep] = []

        for order in self.orders:
            if order.demand <= 0:
                raise ValueError(f"Order demand must be positive for {order.label}")
            if order.demand - self.vehicle_capacity > EPSILON:
                raise ValueError(
                    f"Order {order.label} demand {order.demand:.2f} exceeds vehicle capacity {self.vehicle_capacity:.2f}"
                )

        self.order_order_distances = self._build_order_order_distances()
        self.depot_order_distances = self._build_depot_order_distances()
        self.preferred_depot_by_order = self._build_preferred_depot_map()

    def solve(self) -> SolveResult:
        self.steps = []
        min_required_vehicles = self._minimum_required_vehicles()
        used_vehicle_count, fleet_trials = self._select_vehicle_usage(min_required_vehicles)
        self._record_start_step(min_required_vehicles, used_vehicle_count, fleet_trials)

        construction_routes = self._construct_nearest_neighbor(used_vehicle_count, record_steps=True)
        construction_distance = self._total_distance(construction_routes)
        self._validate_routes(construction_routes)

        final_routes_state = [self._clone_route(route) for route in construction_routes]
        self._improve_routes(final_routes_state, record_steps=True)
        final_distance = self._total_distance(final_routes_state)
        self._validate_routes(final_routes_state)

        final_routes = self._to_route_summaries(final_routes_state, "Final", "final")
        self.steps.append(
            SolveStep(
                index=len(self.steps) + 1,
                title="Final Answer",
                detail=(
                    f"CVRP solution is complete. Final plan uses {len(final_routes_state)} of {self.vehicle_count} "
                    f"available vehicle(s), respects vehicle capacity {self.vehicle_capacity:.2f}, and starts/ends "
                    f"each route at its assigned depot. Total distance is {final_distance:.2f} km; improvement over "
                    f"construction is {construction_distance - final_distance:.2f} km."
                ),
                context_routes=final_routes,
            )
        )

        construction_summaries = self._to_route_summaries(construction_routes, "Construction", "baseline")
        return SolveResult(
            baseline_routes=construction_summaries,
            savings_routes=construction_summaries,
            final_routes=final_routes,
            steps=self.steps,
            baseline_distance_km=construction_distance,
            savings_distance_km=construction_distance,
            final_distance_km=final_distance,
            vehicle_count=self.vehicle_count,
        )

    def _minimum_required_vehicles(self) -> int:
        total_demand = sum(order.demand for order in self.orders)
        return max(1, math.ceil(total_demand / self.vehicle_capacity - EPSILON))

    def _select_vehicle_usage(self, min_required_vehicles: int) -> tuple[int, list[tuple[int, tuple[float, float]]]]:
        best_vehicle_count = min_required_vehicles
        best_objective = (math.inf, math.inf)
        trials: list[tuple[int, tuple[float, float]]] = []
        max_vehicles = min(self.vehicle_count, len(self.orders))

        for vehicle_count in range(min_required_vehicles, max_vehicles + 1):
            trial_routes = self._construct_nearest_neighbor(vehicle_count, record_steps=False)
            improved_routes = [self._clone_route(route) for route in trial_routes]
            self._improve_routes(improved_routes, record_steps=False)
            objective = self._solution_objective(improved_routes)
            trials.append((vehicle_count, objective))
            if objective < best_objective:
                best_vehicle_count = vehicle_count
                best_objective = objective

        return best_vehicle_count, trials

    def _record_start_step(
        self,
        min_required_vehicles: int,
        used_vehicle_count: int,
        fleet_trials: list[tuple[int, tuple[float, float]]],
    ) -> None:
        trial_text = "; ".join(
            f"{vehicle_count} vehicle(s): longest route {objective[0]:.2f} km, total {objective[1]:.2f} km"
            for vehicle_count, objective in fleet_trials
        )
        self.steps.append(
            SolveStep(
                index=1,
                title="Start Layout",
                detail=(
                    f"This is a multi-depot CVRP. We have {len(self.depots)} depot(s), {len(self.orders)} order(s), "
                    f"up to {self.vehicle_count} vehicle(s), and vehicle capacity {self.vehicle_capacity:.2f}. "
                    f"At least {min_required_vehicles} vehicle(s) are required by demand. We test feasible fleet sizes "
                    f"from {min_required_vehicles} to {self.vehicle_count}, seed routes from the nearest suitable depot "
                    f"for each unserved cluster, extend them with nearest neighbour, then refine each route with 2-opt. "
                    f"We choose the fleet size with the smallest longest-route distance, then smallest total distance. "
                    f"Selected: {used_vehicle_count} vehicle(s). Trials -> {trial_text}."
                ),
            )
        )

    def _construct_nearest_neighbor(self, vehicle_count: int, record_steps: bool = False) -> list[_VehicleRoute]:
        remaining = set(range(len(self.orders)))
        routes: list[_VehicleRoute] = []
        committed_segments: list[RouteSummary] = []
        edge_counts: list[int] = []

        while remaining and len(routes) < vehicle_count:
            candidates: list[tuple[float, float, float, int, int]] = []
            seed_orders_by_depot = self._seed_orders_by_depot(remaining, routes)
            for depot_index, order_indexes in seed_orders_by_depot.items():
                for order_index in order_indexes:
                    leg = self._depot_to_order_distance(depot_index, order_index)
                    trial_routes = [self._clone_route(route) for route in routes]
                    trial_routes.append(
                        _VehicleRoute(
                            depot_index=depot_index,
                            order_indexes=[order_index],
                            load=self.orders[order_index].demand,
                        )
                    )
                    objective = self._solution_objective(trial_routes)
                    candidates.append((leg, objective[0], objective[1], depot_index, order_index))
            if not candidates:
                break
            candidates.sort(key=lambda item: (item[0], item[1], item[2], item[3], item[4]))
            chosen_leg, chosen_makespan, chosen_total, depot_index, order_index = candidates[0]
            route_index = len(routes)

            if record_steps:
                depot_label = self.depots[depot_index].label
                order_label = self.orders[order_index].label
                detail = (
                    f"Vehicle {route_index + 1}: start from depot {depot_label} and connect to {order_label}. "
                    f"Nearest-neighbour score = direct depot-to-order distance. Chosen edge = {chosen_leg:.2f} km, "
                    f"which is the smallest feasible seed connection from the nearest suitable depot for this cluster. "
                    f"The order demand is {self.orders[order_index].demand:.2f}, so route load becomes "
                    f"{self.orders[order_index].demand:.2f}/{self.vehicle_capacity:.2f}. "
                    f"Tie-breakers use longest-route distance {chosen_makespan:.2f} km and total distance {chosen_total:.2f} km."
                )
                self.steps.append(
                    SolveStep(
                        index=len(self.steps) + 1,
                        title=f"Connect {depot_label} to {order_label}",
                        detail=detail,
                        chosen=self._edge_outline(route_index + 1, depot_index, None, order_index, chosen_leg, detail),
                        alternatives=[
                            self._edge_outline(
                                route_index + 1,
                                other_depot_index,
                                None,
                                candidate_order,
                                candidate_leg,
                                (
                                    f"Alternative seed: {self.depots[other_depot_index].label} to "
                                    f"{self.orders[candidate_order].label}; direct edge {candidate_leg:.2f} km, "
                                    f"longest route {candidate_makespan:.2f} km, total distance {candidate_total:.2f} km."
                                ),
                                style="alternative",
                            )
                            for candidate_leg, candidate_makespan, candidate_total, other_depot_index, candidate_order in candidates[1:3]
                        ],
                        focus_node_ids=[self.depots[depot_index].node_id, self.orders[order_index].node_id],
                        context_routes=committed_segments[:],
                    )
                )

            routes.append(_VehicleRoute(depot_index=depot_index, order_indexes=[order_index], load=self.orders[order_index].demand))
            edge_counts.append(1)
            remaining.remove(order_index)
            committed_segments.append(self._edge_summary(route_index + 1, edge_counts[route_index], depot_index, None, order_index))

        while remaining:
            candidates = []
            for route_index, route in enumerate(routes):
                last_order = route.order_indexes[-1]
                for order_index in remaining:
                    order = self.orders[order_index]
                    if route.load + order.demand - self.vehicle_capacity > EPSILON:
                        continue
                    leg = self._order_to_order_distance(last_order, order_index)
                    trial_routes = [self._clone_route(existing) for existing in routes]
                    updated_route = trial_routes[route_index]
                    updated_route.order_indexes.append(order_index)
                    updated_route.load += order.demand
                    objective = self._solution_objective(trial_routes)
                    candidates.append((leg, objective[0], objective[1], route_index, order_index))
            if not candidates:
                raise ValueError(
                    "No feasible CVRP assignment exists for the remaining orders with the configured vehicle count and capacity"
                )
            candidates.sort(key=lambda item: (item[0], item[1], item[2], item[3], item[4]))
            chosen_leg, chosen_makespan, chosen_total, route_index, order_index = candidates[0]
            route = routes[route_index]
            previous_order = route.order_indexes[-1]
            route.order_indexes.append(order_index)
            route.load += self.orders[order_index].demand
            remaining.remove(order_index)
            edge_counts[route_index] += 1

            if record_steps:
                from_label = self.orders[previous_order].label
                chosen_label = self.orders[order_index].label
                detail = (
                    f"Vehicle {route_index + 1}: connect {from_label} to {chosen_label}. "
                    f"Nearest-neighbour score = direct edge distance. Chosen edge = {chosen_leg:.2f} km, which is the "
                    f"smallest feasible next connection. Demand {self.orders[order_index].demand:.2f} keeps the route load at "
                    f"{route.load:.2f}/{self.vehicle_capacity:.2f}. Tie-breakers use longest-route distance "
                    f"{chosen_makespan:.2f} km and total distance {chosen_total:.2f} km."
                )
                self.steps.append(
                    SolveStep(
                        index=len(self.steps) + 1,
                        title=f"Connect {from_label} to {chosen_label}",
                        detail=detail,
                        chosen=self._edge_outline(route_index + 1, route.depot_index, previous_order, order_index, chosen_leg, detail),
                        alternatives=[
                            self._edge_outline(
                                alternative_route_index + 1,
                                routes[alternative_route_index].depot_index,
                                routes[alternative_route_index].order_indexes[-1],
                                candidate_order,
                                candidate_leg,
                                (
                                    f"Alternative: Vehicle {alternative_route_index + 1} from "
                                    f"{self.orders[routes[alternative_route_index].order_indexes[-1]].label} to "
                                    f"{self.orders[candidate_order].label}; direct edge {candidate_leg:.2f} km, "
                                    f"longest route {candidate_makespan:.2f} km, total distance {candidate_total:.2f} km."
                                ),
                                style="alternative",
                            )
                            for candidate_leg, candidate_makespan, candidate_total, alternative_route_index, candidate_order in candidates[1:3]
                        ],
                        focus_node_ids=[self.orders[previous_order].node_id, self.orders[order_index].node_id],
                        context_routes=committed_segments[:],
                    )
                )

            committed_segments.append(
                self._edge_summary(route_index + 1, edge_counts[route_index], route.depot_index, previous_order, order_index)
            )

        if record_steps:
            for route_index, route in enumerate(routes):
                last_order = route.order_indexes[-1]
                depot = self.depots[route.depot_index]
                detail = (
                    f"Vehicle {route_index + 1}: return from {self.orders[last_order].label} to depot {depot.label} to "
                    f"close the route. Current load is {route.load:.2f}/{self.vehicle_capacity:.2f}."
                )
                self.steps.append(
                    SolveStep(
                        index=len(self.steps) + 1,
                        title=f"Return {self.orders[last_order].label} to {depot.label}",
                        detail=detail,
                        chosen=self._edge_outline(
                            route_index + 1,
                            route.depot_index,
                            last_order,
                            None,
                            self._order_to_depot_distance(last_order, route.depot_index),
                            detail,
                        ),
                        focus_node_ids=[self.orders[last_order].node_id, depot.node_id],
                        context_routes=committed_segments[:],
                    )
                )
                edge_counts[route_index] += 1
                committed_segments.append(
                    self._edge_summary(route_index + 1, edge_counts[route_index], route.depot_index, last_order, None)
                )

        return routes

    def _improve_routes(self, routes: list[_VehicleRoute], record_steps: bool = True) -> None:
        while True:
            improved = False
            for route_index, route in enumerate(routes):
                best_candidate = self._best_two_opt(route)
                if best_candidate is None:
                    continue
                improved_orders, improvement, left_node_id, right_node_id = best_candidate
                route.order_indexes = improved_orders
                improved = True
                if record_steps:
                    self.steps.append(
                        SolveStep(
                            index=len(self.steps) + 1,
                            title="2-opt Improvement",
                            detail=(
                                f"Vehicle {route_index + 1}: reverse the segment between {self._node_label(left_node_id)} "
                                f"and {self._node_label(right_node_id)}. 2-opt accepts the reversal because it shortens "
                                f"the route by {improvement:.2f} km while keeping the same depot and load "
                                f"({route.load:.2f}/{self.vehicle_capacity:.2f})."
                            ),
                            chosen=RouteOutline(
                                name=f"Vehicle {route_index + 1}",
                                node_ids=self._route_node_ids(route),
                                score=improvement,
                                reason=(
                                    f"2-opt rule: if reversing a route segment reduces route length, keep the reversal. "
                                    f"Improvement = {improvement:.2f} km."
                                ),
                                style="selected",
                                color=ROUTE_COLORS[route_index % len(ROUTE_COLORS)],
                            ),
                            focus_node_ids=[left_node_id, right_node_id],
                            context_routes=self._to_route_summaries(routes, "Final", "final"),
                        )
                    )
            if not improved:
                break

    def _best_two_opt(self, route: _VehicleRoute) -> tuple[list[int], float, str, str] | None:
        if len(route.order_indexes) < 3:
            return None
        baseline = self._route_distance(route)
        best: tuple[list[int], float, str, str] | None = None
        orders = route.order_indexes
        for left in range(len(orders) - 1):
            for right in range(left + 1, len(orders)):
                candidate_orders = orders[:left] + list(reversed(orders[left : right + 1])) + orders[right + 1 :]
                candidate_route = _VehicleRoute(route.depot_index, candidate_orders, route.load)
                improvement = baseline - self._route_distance(candidate_route)
                if improvement > EPSILON and (best is None or improvement > best[1]):
                    best = (
                        candidate_orders,
                        improvement,
                        self.orders[orders[left]].node_id,
                        self.orders[orders[right]].node_id,
                    )
        return best

    def _validate_routes(self, routes: list[_VehicleRoute]) -> None:
        seen: list[int] = []
        for route in routes:
            if not route.order_indexes:
                raise ValueError("Routes must not be empty")
            if route.depot_index < 0 or route.depot_index >= len(self.depots):
                raise ValueError("Route depot index is invalid")
            if route.load - self.vehicle_capacity > EPSILON:
                raise ValueError("Route load exceeds vehicle capacity")
            seen.extend(route.order_indexes)
        if len(routes) > self.vehicle_count:
            raise ValueError("Route count exceeds configured vehicle count")
        if sorted(seen) != list(range(len(self.orders))):
            raise ValueError("Routes must cover every order exactly once")

    def _build_order_order_distances(self) -> list[list[float]]:
        matrix = [[0.0 for _ in self.orders] for _ in self.orders]
        for left in range(len(self.orders)):
            for right in range(left + 1, len(self.orders)):
                distance = haversine_km(self.orders[left].point, self.orders[right].point)
                matrix[left][right] = distance
                matrix[right][left] = distance
        return matrix

    def _build_depot_order_distances(self) -> list[list[float]]:
        matrix = [[0.0 for _ in self.orders] for _ in self.depots]
        for depot_index, depot in enumerate(self.depots):
            for order_index, order in enumerate(self.orders):
                matrix[depot_index][order_index] = haversine_km(depot.point, order.point)
        return matrix

    def _build_preferred_depot_map(self) -> list[int]:
        preferred: list[int] = []
        for order_index in range(len(self.orders)):
            preferred.append(
                min(
                    range(len(self.depots)),
                    key=lambda depot_index: (
                        self._depot_to_order_distance(depot_index, order_index),
                        depot_index,
                    ),
                )
            )
        return preferred

    def _seed_orders_by_depot(
        self,
        remaining: set[int],
        routes: list[_VehicleRoute],
    ) -> dict[int, list[int]]:
        used_depots = {route.depot_index for route in routes}
        unopened_priority_depots = sorted(
            {
                self.preferred_depot_by_order[order_index]
                for order_index in remaining
                if self.preferred_depot_by_order[order_index] not in used_depots
            }
        )
        candidate_depots = unopened_priority_depots or list(range(len(self.depots)))
        candidates: dict[int, list[int]] = {}
        for depot_index in candidate_depots:
            eligible = [
                order_index
                for order_index in remaining
                if not unopened_priority_depots or self.preferred_depot_by_order[order_index] == depot_index
            ]
            if not eligible:
                continue
            ranked = sorted(
                eligible,
                key=lambda order_index: (
                    self._depot_to_order_distance(depot_index, order_index),
                    order_index,
                ),
            )
            candidates[depot_index] = ranked[:3]
        return candidates

    def _route_distance(self, route: _VehicleRoute) -> float:
        if not route.order_indexes:
            return 0.0
        total = self._depot_to_order_distance(route.depot_index, route.order_indexes[0])
        for left, right in zip(route.order_indexes, route.order_indexes[1:]):
            total += self._order_to_order_distance(left, right)
        total += self._order_to_depot_distance(route.order_indexes[-1], route.depot_index)
        return total

    def _total_distance(self, routes: list[_VehicleRoute]) -> float:
        return sum(self._route_distance(route) for route in routes)

    def _makespan_distance(self, routes: list[_VehicleRoute]) -> float:
        if not routes:
            return 0.0
        return max(self._route_distance(route) for route in routes)

    def _solution_objective(self, routes: list[_VehicleRoute]) -> tuple[float, float]:
        return (self._makespan_distance(routes), self._total_distance(routes))

    def _depot_to_order_distance(self, depot_index: int, order_index: int) -> float:
        return self.depot_order_distances[depot_index][order_index]

    def _order_to_depot_distance(self, order_index: int, depot_index: int) -> float:
        return self.depot_order_distances[depot_index][order_index]

    def _order_to_order_distance(self, left: int, right: int) -> float:
        return self.order_order_distances[left][right]

    def _to_route_summaries(self, routes: list[_VehicleRoute], prefix: str, style: str) -> list[RouteSummary]:
        summaries: list[RouteSummary] = []
        for route_index, route in enumerate(routes, start=1):
            summaries.append(
                RouteSummary(
                    name=f"{prefix} Vehicle {route_index} ({self.depots[route.depot_index].label})",
                    node_ids=self._route_node_ids(route),
                    distance_km=self._route_distance(route),
                    color=ROUTE_COLORS[(route_index - 1) % len(ROUTE_COLORS)],
                    style=style,
                    load=route.load,
                    capacity=self.vehicle_capacity,
                )
            )
        return summaries

    def _route_node_ids(self, route: _VehicleRoute) -> list[str]:
        depot_id = self.depots[route.depot_index].node_id
        return [depot_id] + [self.orders[index].node_id for index in route.order_indexes] + [depot_id]

    def _node_label(self, node_id: str) -> str:
        for depot in self.depots:
            if depot.node_id == node_id:
                return depot.label
        for order in self.orders:
            if order.node_id == node_id:
                return order.label
        return node_id

    def _edge_summary(
        self,
        route_index: int,
        edge_index: int,
        depot_index: int,
        left_order_index: int | None,
        right_order_index: int | None,
    ) -> RouteSummary:
        return RouteSummary(
            name=f"Vehicle {route_index} Edge {edge_index}",
            node_ids=[self._state_node_id(depot_index, left_order_index), self._state_node_id(depot_index, right_order_index)],
            distance_km=self._edge_distance(depot_index, left_order_index, right_order_index),
            color="#16a34a",
            style="final",
        )

    def _edge_outline(
        self,
        route_index: int,
        depot_index: int,
        left_order_index: int | None,
        right_order_index: int | None,
        score: float,
        reason: str,
        style: str = "selected",
    ) -> RouteOutline:
        return RouteOutline(
            name=f"Vehicle {route_index} Edge",
            node_ids=[self._state_node_id(depot_index, left_order_index), self._state_node_id(depot_index, right_order_index)],
            score=score,
            reason=reason,
            style=style,
            color="#16a34a" if style == "selected" else "#dc2626",
        )

    def _state_node_id(self, depot_index: int, order_index: int | None) -> str:
        if order_index is None:
            return self.depots[depot_index].node_id
        return self.orders[order_index].node_id

    def _edge_distance(self, depot_index: int, left_order_index: int | None, right_order_index: int | None) -> float:
        if left_order_index is None and right_order_index is None:
            return 0.0
        if left_order_index is None:
            return self._depot_to_order_distance(depot_index, right_order_index)
        if right_order_index is None:
            return self._order_to_depot_distance(left_order_index, depot_index)
        return self._order_to_order_distance(left_order_index, right_order_index)

    def _clone_route(self, route: _VehicleRoute) -> _VehicleRoute:
        return _VehicleRoute(route.depot_index, route.order_indexes[:], route.load)


def haversine_km(left: GeoPoint, right: GeoPoint) -> float:
    radius_km = 6371.0
    lat1 = math.radians(left.latitude)
    lat2 = math.radians(right.latitude)
    dlat = lat2 - lat1
    dlon = math.radians(right.longitude - left.longitude)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2.0) ** 2
    )
    return radius_km * (2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a)))
