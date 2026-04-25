"""Explainable VRP solver for the Tkinter mini-project."""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

from mini_vrp_tkinter.models import GeoPoint, Node, RouteOutline, RouteSummary, SolveResult, SolveStep

ROUTE_COLORS = [
    "#ff6b00",
    "#0f62fe",
    "#00a870",
    "#7c3aed",
    "#e11d48",
    "#f59e0b",
]
EPSILON = 1e-9
EXACT_ORDER_LIMIT = 12
ROUTE_EXACT_ORDER_LIMIT = 12


@dataclass(slots=True)
class _MergeCandidate:
    left_index: int
    right_index: int
    merged: list[int]
    saving: float
    distance_km: float
    left_tail: int
    right_head: int


@dataclass(slots=True)
class _MoveCandidate:
    source_index: int
    target_index: int
    source_customer: int
    target_position: int
    improvement: float
    updated_routes: list[list[int]]


@dataclass(slots=True)
class _SwapCandidate:
    left_index: int
    right_index: int
    left_customer: int
    right_customer: int
    improvement: float
    updated_routes: list[list[int]]


class ExplainableVRPSolver:
    """Small but credible VRP solver with human-readable decision logging."""

    def __init__(self, depot: Node, orders: list[Node], vehicle_count: int):
        if vehicle_count < 1:
            raise ValueError("Vehicle count must be at least 1")
        if depot.kind != "depot":
            raise ValueError("Depot node must have kind='depot'")
        order_ids = [order.node_id for order in orders]
        if len(order_ids) != len(set(order_ids)):
            raise ValueError("Order node IDs must be unique")
        if depot.node_id in order_ids:
            raise ValueError("Depot node ID must be different from order node IDs")
        self.depot = depot
        self.orders = orders[:]
        self.vehicle_count = max(1, min(vehicle_count, len(orders) or 1))
        self.steps: list[SolveStep] = []
        self.distance_matrix = self._distance_matrix()

    def solve(self) -> SolveResult:
        self.steps = []
        if not self.orders:
            return SolveResult(
                baseline_routes=[],
                savings_routes=[],
                final_routes=[],
                steps=[],
                baseline_distance_km=0.0,
                savings_distance_km=0.0,
                final_distance_km=0.0,
                vehicle_count=self.vehicle_count,
            )

        used_vehicle_count, fleet_trials = self._select_vehicle_usage()
        self._record_start_step(used_vehicle_count, fleet_trials)

        baseline_routes = self._nearest_neighbor_baseline(
            vehicle_count=used_vehicle_count,
            record_steps=True,
        )
        baseline_distance = self._total_distance(baseline_routes)
        self._validate_routes(baseline_routes)

        final_index_routes = [route[:] for route in baseline_routes]
        self._improve_routes(final_index_routes, record_steps=True)
        final_distance = self._total_distance(final_index_routes)
        self._validate_routes(final_index_routes)

        final_routes = self._to_route_summaries(final_index_routes, "Final", "final")
        self.steps.append(
            SolveStep(
                index=len(self.steps) + 1,
                title="Final Answer",
                detail=(
                    f"Nearest-neighbour construction is complete and 2-opt refinement is applied. "
                    f"Final solution uses {len(final_index_routes)} vehicle route(s), with total distance "
                    f"{final_distance:.2f} km and improvement of {baseline_distance - final_distance:.2f} km "
                    f"over the raw construction."
                ),
                context_routes=final_routes,
            )
        )

        baseline_summaries = self._to_route_summaries(baseline_routes, "Construction", "baseline")
        return SolveResult(
            baseline_routes=baseline_summaries,
            savings_routes=baseline_summaries,
            final_routes=final_routes,
            steps=self.steps,
            baseline_distance_km=baseline_distance,
            savings_distance_km=baseline_distance,
            final_distance_km=final_distance,
            vehicle_count=self.vehicle_count,
        )

    def _validate_routes(self, routes: list[list[int]]) -> None:
        seen: list[int] = []
        for route in routes:
            if not route:
                raise ValueError("Routes must not contain empty tours")
            seen.extend(route)
        if len(routes) > self.vehicle_count:
            raise ValueError("Route count exceeds configured vehicle count")
        if sorted(seen) != list(range(len(self.orders))):
            raise ValueError("Routes must cover every order exactly once")

    def _build_connection_steps(
        self,
        final_routes: list[list[int]],
        baseline_distance: float,
        final_distance: float,
    ) -> list[SolveStep]:
        steps: list[SolveStep] = [
            SolveStep(
                index=1,
                title="Start Layout",
                detail=(
                    "No nodes are connected yet. Start from the depot and add one connection at a time. "
                    "Each next edge is justified against the remaining candidate nodes."
                ),
            )
        ]
        committed_segments: list[RouteSummary] = []

        for route_index, route in enumerate(final_routes, start=1):
            route_planner = self._route_connection_planner(route)
            current: int | None = None
            remaining = tuple(route)
            local_segments: list[RouteSummary] = []

            for stop_position, chosen_order in enumerate(route, start=1):
                rankings = route_planner(current, remaining)
                chosen_leg, chosen_future, chosen_total, _ = next(
                    (leg, future, total, candidate)
                    for leg, future, total, candidate in rankings
                    if candidate == chosen_order
                )
                from_label = "Depot" if current is None else self.orders[current].label
                chosen_label = self.orders[chosen_order].label

                detail = (
                    f"Truck {route_index}: connect {from_label} to {chosen_label} next. "
                    f"Score(next) = direct edge + best completion of the remaining nodes. "
                    f"Here that is {chosen_leg:.2f} + {chosen_future:.2f} = {chosen_total:.2f} km, "
                    f"which is the minimum among the remaining candidates."
                )
                chosen_edge = self._edge_outline(
                    route_index,
                    current,
                    chosen_order,
                    chosen_total,
                    detail,
                )
                alternatives = [
                    self._edge_outline(
                        route_index,
                        current,
                        candidate,
                        candidate_total,
                        (
                            f"If {from_label} connected to {self.orders[candidate].label} instead, "
                            f"the score would be {candidate_leg:.2f} + {candidate_future:.2f} = "
                            f"{candidate_total:.2f} km."
                        ),
                        style="alternative",
                    )
                    for candidate_leg, candidate_future, candidate_total, candidate in rankings
                    if candidate != chosen_order
                ][:2]
                focus_node_ids = [self._state_node_id(current), self.orders[chosen_order].node_id]
                steps.append(
                    SolveStep(
                        index=len(steps) + 1,
                        title=f"Connect {from_label} to {chosen_label}",
                        detail=detail,
                        chosen=chosen_edge,
                        alternatives=alternatives,
                        focus_node_ids=focus_node_ids,
                        context_routes=committed_segments + local_segments,
                    )
                )
                local_segments.append(self._edge_summary(route_index, stop_position, current, chosen_order))
                current = chosen_order
                remaining = tuple(order for order in remaining if order != chosen_order)

            if route:
                last_order = route[-1]
                last_label = self.orders[last_order].label
                return_detail = (
                    f"Truck {route_index}: connect {last_label} back to Depot to close the route "
                    f"after all assigned nodes are served."
                )
                steps.append(
                    SolveStep(
                        index=len(steps) + 1,
                        title=f"Return {last_label} to Depot",
                        detail=return_detail,
                        chosen=self._edge_outline(
                            route_index,
                            last_order,
                            None,
                            self._distance_between(last_order, None),
                            return_detail,
                        ),
                        focus_node_ids=[self.orders[last_order].node_id, self.depot.node_id],
                        context_routes=committed_segments + local_segments,
                    )
                )
                local_segments.append(self._edge_summary(route_index, len(route) + 1, last_order, None))

            committed_segments.extend(local_segments)

        steps.append(
            SolveStep(
                index=len(steps) + 1,
                title="Final Answer",
                detail=(
                    f"Final route set is complete. Distance: {final_distance:.2f} km. "
                    f"Improvement over baseline: {baseline_distance - final_distance:.2f} km."
                ),
                context_routes=committed_segments,
            )
        )
        return steps

    def _route_connection_planner(self, route: list[int]):
        route_tuple = tuple(route)

        @lru_cache(maxsize=None)
        def completion_cost(current: int | None, remaining: tuple[int, ...]) -> float:
            if not remaining:
                return self._distance_between(current, None)
            best = math.inf
            for candidate in remaining:
                tail = tuple(order for order in remaining if order != candidate)
                cost = self._distance_between(current, candidate) + completion_cost(candidate, tail)
                if cost + EPSILON < best:
                    best = cost
            return best

        def rankings(current: int | None, remaining: tuple[int, ...]) -> list[tuple[float, float, float, int]]:
            scores: list[tuple[float, float, float, int]] = []
            for candidate in remaining:
                tail = tuple(order for order in remaining if order != candidate)
                leg = self._distance_between(current, candidate)
                future = completion_cost(candidate, tail)
                total = leg + future
                scores.append((leg, future, total, candidate))
            scores.sort(key=lambda item: (item[2], item[3]))
            return scores

        return rankings

    def _select_vehicle_usage(self) -> tuple[int, list[tuple[int, tuple[float, float]]]]:
        best_vehicle_count = 1
        best_objective = (math.inf, math.inf)
        trials: list[tuple[int, tuple[float, float]]] = []
        max_vehicles = min(self.vehicle_count, len(self.orders))

        for vehicle_count in range(1, max_vehicles + 1):
            trial_routes = self._nearest_neighbor_baseline(vehicle_count=vehicle_count)
            improved_routes = [route[:] for route in trial_routes]
            self._improve_routes(improved_routes, record_steps=False)
            objective = self._solution_objective(improved_routes)
            trials.append((vehicle_count, objective))
            if objective < best_objective:
                best_vehicle_count = vehicle_count
                best_objective = objective

        return best_vehicle_count, trials

    def _record_start_step(
        self,
        used_vehicle_count: int,
        fleet_trials: list[tuple[int, tuple[float, float]]],
    ) -> None:
        trial_text = "; ".join(
            f"{vehicle_count} truck(s): longest route {objective[0]:.2f} km, total {objective[1]:.2f} km"
            for vehicle_count, objective in fleet_trials
        )
        self.steps.append(
            SolveStep(
                index=1,
                title="Start Layout",
                detail=(
                    "No nodes are connected yet. "
                    f"We test 1 to {self.vehicle_count} available vehicle(s) using nearest-neighbour construction "
                    "followed by 2-opt improvement. We choose the fleet size with the smallest longest-route distance "
                    f"(completion-time proxy), then total distance as tie-breaker. Selected: {used_vehicle_count} "
                    f"vehicle(s). Trials -> {trial_text}."
                ),
            )
        )

    def _nearest_neighbor_baseline(
        self,
        vehicle_count: int | None = None,
        record_steps: bool = False,
    ) -> list[list[int]]:
        if not self.orders:
            return []

        route_count = min(vehicle_count or self.vehicle_count, len(self.orders))
        remaining = set(range(len(self.orders)))
        routes = [[] for _ in range(route_count)]
        committed_segments: list[RouteSummary] = []
        edge_counts = [0 for _ in range(route_count)]

        for route_index in range(route_count):
            if not remaining:
                break
            candidates: list[tuple[float, float, float, int]] = []
            for candidate in remaining:
                leg = self._distance_between(None, candidate)
                trial_routes = [route[:] for route in routes]
                trial_routes[route_index] = [candidate]
                objective = self._solution_objective([route for route in trial_routes if route])
                candidates.append((leg, objective[0], objective[1], candidate))
            candidates.sort(key=lambda item: (item[0], item[1], item[2], item[3]))
            chosen_leg, chosen_makespan, chosen_total, chosen_order = candidates[0]

            if record_steps:
                chosen_label = self.orders[chosen_order].label
                detail = (
                    f"Truck {route_index + 1}: start from Depot and connect to {chosen_label}. "
                    f"Nearest-neighbour score = direct edge distance. Chosen edge = {chosen_leg:.2f} km, "
                    f"which is the smallest depot-to-node distance among unserved nodes. Tie-breakers use "
                    f"resulting longest-route distance {chosen_makespan:.2f} km and total distance {chosen_total:.2f} km."
                )
                self.steps.append(
                    SolveStep(
                        index=len(self.steps) + 1,
                        title=f"Connect Depot to {chosen_label}",
                        detail=detail,
                        chosen=self._edge_outline(
                            route_index + 1,
                            None,
                            chosen_order,
                            chosen_leg,
                            detail,
                        ),
                        alternatives=[
                            self._edge_outline(
                                route_index + 1,
                                None,
                                candidate,
                                candidate_leg,
                                (
                                    f"If Truck {route_index + 1} started with {self.orders[candidate].label}, "
                                    f"the direct edge would be {candidate_leg:.2f} km, longest route "
                                    f"{candidate_makespan:.2f} km, total distance {candidate_total:.2f} km."
                                ),
                                style="alternative",
                            )
                            for candidate_leg, candidate_makespan, candidate_total, candidate in candidates[1:3]
                        ],
                        focus_node_ids=[self.depot.node_id, self.orders[chosen_order].node_id],
                        context_routes=committed_segments[:],
                    )
                )

            routes[route_index].append(chosen_order)
            remaining.remove(chosen_order)
            edge_counts[route_index] += 1
            committed_segments.append(
                self._edge_summary(route_index + 1, edge_counts[route_index], None, chosen_order)
            )

        while remaining:
            candidates: list[tuple[float, float, float, int, int]] = []
            for route_index, route in enumerate(routes):
                anchor = route[-1]
                for candidate in remaining:
                    leg = self._distance_between(anchor, candidate)
                    trial_routes = [existing[:] for existing in routes]
                    trial_routes[route_index] = route + [candidate]
                    objective = self._solution_objective([trial for trial in trial_routes if trial])
                    candidates.append((leg, objective[0], objective[1], route_index, candidate))
            candidates.sort(key=lambda item: (item[0], item[1], item[2], item[3], item[4]))
            chosen_leg, chosen_makespan, chosen_total, route_index, chosen_order = candidates[0]
            anchor = routes[route_index][-1]

            if record_steps:
                from_label = self.orders[anchor].label
                chosen_label = self.orders[chosen_order].label
                detail = (
                    f"Truck {route_index + 1}: connect {from_label} to {chosen_label}. "
                    f"Nearest-neighbour score = direct edge distance. Chosen edge = {chosen_leg:.2f} km, "
                    f"which is the smallest available next connection. Tie-breakers use resulting longest-route "
                    f"distance {chosen_makespan:.2f} km and total distance {chosen_total:.2f} km."
                )
                self.steps.append(
                    SolveStep(
                        index=len(self.steps) + 1,
                        title=f"Connect {from_label} to {chosen_label}",
                        detail=detail,
                        chosen=self._edge_outline(
                            route_index + 1,
                            anchor,
                            chosen_order,
                            chosen_leg,
                            detail,
                        ),
                        alternatives=[
                            self._edge_outline(
                                alternative_route_index + 1,
                                routes[alternative_route_index][-1],
                                candidate,
                                candidate_leg,
                                (
                                    f"Alternative: Truck {alternative_route_index + 1} from "
                                    f"{self.orders[routes[alternative_route_index][-1]].label} to "
                                    f"{self.orders[candidate].label}; direct edge {candidate_leg:.2f} km, "
                                    f"longest route {candidate_makespan:.2f} km, total distance {candidate_total:.2f} km."
                                ),
                                style="alternative",
                            )
                            for candidate_leg, candidate_makespan, candidate_total, alternative_route_index, candidate in candidates[1:3]
                        ],
                        focus_node_ids=[self.orders[anchor].node_id, self.orders[chosen_order].node_id],
                        context_routes=committed_segments[:],
                    )
                )

            routes[route_index].append(chosen_order)
            remaining.remove(chosen_order)
            edge_counts[route_index] += 1
            committed_segments.append(
                self._edge_summary(route_index + 1, edge_counts[route_index], anchor, chosen_order)
            )

        return [route for route in routes if route]

    def _clarke_wright(self) -> list[list[int]]:
        routes = [[index] for index in range(len(self.orders))]
        while len(routes) > self.vehicle_count:
            candidates = self._merge_candidates(routes)
            if not candidates:
                break
            selected = candidates[0]
            alternatives = [
                RouteOutline(
                    name=f"Option {option + 1}",
                    node_ids=self._route_node_ids(candidate.merged),
                    score=candidate.saving,
                    reason=(
                        f"Saving {candidate.saving:.2f} km by connecting "
                        f"{self.orders[candidate.left_tail].label} to {self.orders[candidate.right_head].label}."
                    ),
                    style="alternative" if option else "selected",
                    color=ROUTE_COLORS[option % len(ROUTE_COLORS)] if option == 0 else "#8c8c8c",
                )
                for option, candidate in enumerate(candidates[:3])
            ]
            left_route = routes[selected.left_index]
            right_route = routes[selected.right_index]
            routes[selected.left_index] = selected.merged
            routes.pop(selected.right_index)
            self.steps.append(
                SolveStep(
                    index=len(self.steps) + 1,
                    title="Chosen Savings Merge",
                    detail=(
                        f"Connected {self.orders[selected.left_tail].label} with {self.orders[selected.right_head].label} "
                        f"because it gives the largest available saving ({selected.saving:.2f} km). "
                        f"Route count dropped from {len(routes) + 1} to {len(routes)}."
                    ),
                    chosen=alternatives[0],
                    alternatives=alternatives[1:],
                    focus_node_ids=[
                        self.orders[selected.left_tail].node_id,
                        self.orders[selected.right_head].node_id,
                    ],
                    context_routes=self._to_route_summaries(routes, "Savings", "savings"),
                )
            )
            if left_route == right_route:
                break
        return routes

    def _improve_routes(self, routes: list[list[int]], record_steps: bool = True) -> None:
        while True:
            improved = False
            for route_index, route in enumerate(routes):
                opt_candidates = self._two_opt_candidates(route)
                if not opt_candidates:
                    continue
                best_route, improvement, left_customer, right_customer = opt_candidates[0]
                routes[route_index] = best_route
                improved = True
                if record_steps:
                    self.steps.append(
                        SolveStep(
                            index=len(self.steps) + 1,
                            title="2-opt Improvement",
                            detail=(
                                f"Truck {route_index + 1}: reverse the segment between "
                                f"{self._node_label(left_customer)} and {self._node_label(right_customer)}. "
                                f"2-opt keeps this reversal because it shortens the route by {improvement:.2f} km."
                            ),
                            chosen=RouteOutline(
                                name=f"Truck {route_index + 1}",
                                node_ids=self._route_node_ids(best_route),
                                score=improvement,
                                reason=(
                                    f"2-opt rule: if reversing a segment reduces route length, accept the reversal. "
                                    f"Improvement = {improvement:.2f} km."
                                ),
                                style="selected",
                                color=ROUTE_COLORS[route_index % len(ROUTE_COLORS)],
                            ),
                            focus_node_ids=[left_customer, right_customer],
                            context_routes=self._to_route_summaries(routes, "Final", "final"),
                        )
                    )
            if not improved:
                break

    def _merge_candidates(self, routes: list[list[int]]) -> list[_MergeCandidate]:
        candidates: list[_MergeCandidate] = []
        for left_index in range(len(routes)):
            for right_index in range(left_index + 1, len(routes)):
                left = routes[left_index]
                right = routes[right_index]
                for left_seq in (left, list(reversed(left))):
                    for right_seq in (right, list(reversed(right))):
                        saving = self._saving(left_seq[-1], right_seq[0])
                        merged = left_seq + right_seq
                        candidates.append(
                            _MergeCandidate(
                                left_index=left_index,
                                right_index=right_index,
                                merged=merged,
                                saving=saving,
                                distance_km=self._route_distance(merged),
                                left_tail=left_seq[-1],
                                right_head=right_seq[0],
                            )
                        )
        candidates.sort(key=lambda item: (-item.saving, item.distance_km, item.left_index, item.right_index))
        return candidates

    def _two_opt_candidates(self, route: list[int]) -> list[tuple[list[int], float, str, str]]:
        candidates: list[tuple[list[int], float, str, str]] = []
        baseline = self._route_distance(route)
        for left in range(len(route) - 1):
            for right in range(left + 1, len(route)):
                candidate = route[:left] + list(reversed(route[left : right + 1])) + route[right + 1 :]
                improvement = baseline - self._route_distance(candidate)
                if improvement > 1e-6:
                    candidates.append(
                        (
                            candidate,
                            improvement,
                            self.orders[route[left]].node_id,
                            self.orders[route[right]].node_id,
                        )
                    )
        candidates.sort(key=lambda item: -item[1])
        return candidates

    def _best_relocate(self, routes: list[list[int]]) -> _MoveCandidate | None:
        best: _MoveCandidate | None = None
        baseline = self._total_distance(routes)
        for source_index, source_route in enumerate(routes):
            if len(source_route) < 2:
                continue
            for source_pos, customer in enumerate(source_route):
                reduced = source_route[:source_pos] + source_route[source_pos + 1 :]
                for target_index, target_route in enumerate(routes):
                    if source_index == target_index:
                        continue
                    for insert_at in range(len(target_route) + 1):
                        updated_routes = [route[:] for route in routes]
                        updated_routes[source_index] = reduced
                        expanded = target_route[:insert_at] + [customer] + target_route[insert_at:]
                        updated_routes[target_index] = expanded
                        improvement = baseline - self._total_distance(updated_routes)
                        if improvement > 1e-6 and (best is None or improvement > best.improvement):
                            best = _MoveCandidate(
                                source_index=source_index,
                                target_index=target_index,
                                source_customer=customer,
                                target_position=insert_at,
                                improvement=improvement,
                                updated_routes=[route for route in updated_routes if route],
                            )
        return best

    def _best_swap(self, routes: list[list[int]]) -> _SwapCandidate | None:
        best: _SwapCandidate | None = None
        baseline = self._total_distance(routes)
        for left_index in range(len(routes)):
            for right_index in range(left_index + 1, len(routes)):
                left_route = routes[left_index]
                right_route = routes[right_index]
                for left_pos, left_customer in enumerate(left_route):
                    for right_pos, right_customer in enumerate(right_route):
                        updated_routes = [route[:] for route in routes]
                        updated_routes[left_index][left_pos] = right_customer
                        updated_routes[right_index][right_pos] = left_customer
                        improvement = baseline - self._total_distance(updated_routes)
                        if improvement > 1e-6 and (best is None or improvement > best.improvement):
                            best = _SwapCandidate(
                                left_index=left_index,
                                right_index=right_index,
                                left_customer=left_customer,
                                right_customer=right_customer,
                                improvement=improvement,
                                updated_routes=updated_routes,
                            )
        return best

    def _optimize_route_order(self, route: list[int]) -> list[int]:
        if len(route) <= 1 or len(route) > ROUTE_EXACT_ORDER_LIMIT:
            return route[:]

        route_tuple = tuple(route)

        @lru_cache(maxsize=None)
        def completion(current: int | None, remaining: tuple[int, ...]) -> tuple[float, tuple[int, ...]]:
            if not remaining:
                return (self._distance_between(current, None), ())

            best_cost = math.inf
            best_order: tuple[int, ...] = ()
            for candidate in remaining:
                tail = tuple(order for order in remaining if order != candidate)
                tail_cost, tail_order = completion(candidate, tail)
                total_cost = self._distance_between(current, candidate) + tail_cost
                candidate_order = (candidate,) + tail_order
                if total_cost + EPSILON < best_cost or (
                    abs(total_cost - best_cost) <= EPSILON and candidate_order < best_order
                ):
                    best_cost = total_cost
                    best_order = candidate_order
            return (best_cost, best_order)

        return list(completion(None, route_tuple)[1])

    def _exact_optimal_routes(self) -> list[list[int]]:
        order_count = len(self.orders)
        if order_count == 0:
            return []

        full_mask = (1 << order_count) - 1
        route_costs, route_orders = self._subset_route_catalog()
        max_routes = min(self.vehicle_count, order_count)

        infinity_objective = (math.inf, math.inf)
        partition_objectives = [
            [infinity_objective for _ in range(full_mask + 1)]
            for _ in range(max_routes + 1)
        ]
        partition_choice = [[0 for _ in range(full_mask + 1)] for _ in range(max_routes + 1)]
        partition_objectives[0][0] = (0.0, 0.0)

        for route_count in range(1, max_routes + 1):
            for mask in range(1, full_mask + 1):
                anchor = mask & -mask
                submask = mask
                while submask:
                    if submask & anchor:
                        previous_objective = partition_objectives[route_count - 1][mask ^ submask]
                        if previous_objective[0] < math.inf:
                            candidate_objective = (
                                max(previous_objective[0], route_costs[submask]),
                                previous_objective[1] + route_costs[submask],
                            )
                            if candidate_objective < partition_objectives[route_count][mask]:
                                partition_objectives[route_count][mask] = candidate_objective
                                partition_choice[route_count][mask] = submask
                    submask = (submask - 1) & mask

        best_route_count = min(
            range(1, max_routes + 1),
            key=lambda route_count: (partition_objectives[route_count][full_mask], route_count),
        )
        mask = full_mask
        route_count = best_route_count
        routes: list[list[int]] = []
        while mask:
            chosen_mask = partition_choice[route_count][mask]
            if chosen_mask == 0:
                raise ValueError("Exact solver could not reconstruct the optimal partition")
            routes.append(route_orders[chosen_mask][:])
            mask ^= chosen_mask
            route_count -= 1
        routes.sort(key=lambda route: tuple(route))
        return routes

    def _subset_route_catalog(self) -> tuple[list[float], list[list[int]]]:
        order_count = len(self.orders)
        full_mask = 1 << order_count
        depot_index = order_count

        path_costs: list[dict[int, float]] = [dict() for _ in range(full_mask)]
        predecessors: list[dict[int, int]] = [dict() for _ in range(full_mask)]
        route_costs = [math.inf for _ in range(full_mask)]
        route_orders: list[list[int]] = [[] for _ in range(full_mask)]

        for order_index in range(order_count):
            mask = 1 << order_index
            path_costs[mask][order_index] = self.distance_matrix[depot_index][order_index]
            predecessors[mask][order_index] = -1
            route_costs[mask] = (
                self.distance_matrix[depot_index][order_index]
                + self.distance_matrix[order_index][depot_index]
            )
            route_orders[mask] = [order_index]

        for mask in range(1, full_mask):
            if mask & (mask - 1) == 0:
                continue
            for end_index in self._mask_indices(mask):
                previous_mask = mask ^ (1 << end_index)
                best_cost = math.inf
                best_previous = -1
                for previous_end, previous_cost in path_costs[previous_mask].items():
                    candidate_cost = previous_cost + self.distance_matrix[previous_end][end_index]
                    if candidate_cost + EPSILON < best_cost:
                        best_cost = candidate_cost
                        best_previous = previous_end
                path_costs[mask][end_index] = best_cost
                predecessors[mask][end_index] = best_previous

            best_end_index = min(
                path_costs[mask],
                key=lambda end_index: path_costs[mask][end_index] + self.distance_matrix[end_index][depot_index],
            )
            route_costs[mask] = (
                path_costs[mask][best_end_index]
                + self.distance_matrix[best_end_index][depot_index]
            )
            route_orders[mask] = self._reconstruct_subset_route(mask, best_end_index, predecessors)

        return route_costs, route_orders

    def _reconstruct_subset_route(
        self,
        mask: int,
        end_index: int,
        predecessors: list[dict[int, int]],
    ) -> list[int]:
        route: list[int] = []
        current_mask = mask
        current_index = end_index
        while current_index != -1:
            route.append(current_index)
            previous_index = predecessors[current_mask][current_index]
            current_mask ^= 1 << current_index
            current_index = previous_index
        route.reverse()
        return route

    def _mask_indices(self, mask: int) -> list[int]:
        return [index for index in range(len(self.orders)) if mask & (1 << index)]

    def _distance_matrix(self) -> list[list[float]]:
        all_points = [order.point for order in self.orders] + [self.depot.point]
        matrix = [[0.0 for _ in all_points] for _ in all_points]
        for left in range(len(all_points)):
            for right in range(left + 1, len(all_points)):
                distance = haversine_km(all_points[left], all_points[right])
                matrix[left][right] = distance
                matrix[right][left] = distance
        return matrix

    def _route_distance(self, route: list[int]) -> float:
        if not route:
            return 0.0
        depot_index = len(self.orders)
        total = self.distance_matrix[depot_index][route[0]]
        for left, right in zip(route, route[1:]):
            total += self.distance_matrix[left][right]
        total += self.distance_matrix[route[-1]][depot_index]
        return total

    def _total_distance(self, routes: list[list[int]]) -> float:
        return sum(self._route_distance(route) for route in routes)

    def _makespan_distance(self, routes: list[list[int]]) -> float:
        if not routes:
            return 0.0
        return max(self._route_distance(route) for route in routes)

    def _solution_objective(self, routes: list[list[int]]) -> tuple[float, float]:
        return (self._makespan_distance(routes), self._total_distance(routes))

    def _distance_between(self, left: int | None, right: int | None) -> float:
        depot_index = len(self.orders)
        left_index = depot_index if left is None else left
        right_index = depot_index if right is None else right
        return self.distance_matrix[left_index][right_index]

    def _saving(self, left: int, right: int) -> float:
        depot_index = len(self.orders)
        return (
            self.distance_matrix[depot_index][left]
            + self.distance_matrix[depot_index][right]
            - self.distance_matrix[left][right]
        )

    def _to_route_summaries(self, routes: list[list[int]], prefix: str, style: str) -> list[RouteSummary]:
        summaries: list[RouteSummary] = []
        for route_index, route in enumerate(routes, start=1):
            summaries.append(
                RouteSummary(
                    name=f"{prefix} Truck {route_index}",
                    node_ids=self._route_node_ids(route),
                    distance_km=self._route_distance(route),
                    color=ROUTE_COLORS[(route_index - 1) % len(ROUTE_COLORS)],
                    style=style,
                )
            )
        return summaries

    def _route_node_ids(self, route: list[int]) -> list[str]:
        return [self.depot.node_id] + [self.orders[index].node_id for index in route] + [self.depot.node_id]

    def _state_node_id(self, state: int | None) -> str:
        return self.depot.node_id if state is None else self.orders[state].node_id

    def _node_label(self, node_id: str) -> str:
        if node_id == self.depot.node_id:
            return self.depot.label
        for order in self.orders:
            if order.node_id == node_id:
                return order.label
        return node_id

    def _edge_summary(
        self,
        route_index: int,
        edge_index: int,
        left: int | None,
        right: int | None,
    ) -> RouteSummary:
        left_id = self._state_node_id(left)
        right_id = self._state_node_id(right)
        return RouteSummary(
            name=f"Truck {route_index} Edge {edge_index}",
            node_ids=[left_id, right_id],
            distance_km=self._distance_between(left, right),
            color="#16a34a",
            style="final",
        )

    def _edge_outline(
        self,
        route_index: int,
        left: int | None,
        right: int | None,
        score: float,
        reason: str,
        style: str = "selected",
    ) -> RouteOutline:
        left_id = self._state_node_id(left)
        right_id = self._state_node_id(right)
        return RouteOutline(
            name=f"Truck {route_index} Edge",
            node_ids=[left_id, right_id],
            score=score,
            reason=reason,
            style=style,
            color="#16a34a" if style == "selected" else "#dc2626",
        )


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
