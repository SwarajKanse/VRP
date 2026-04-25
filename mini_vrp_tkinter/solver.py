"""Explainable VRP solver for the Tkinter mini-project."""

from __future__ import annotations

import math
from dataclasses import dataclass

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
        baseline_routes = self._nearest_neighbor_baseline()
        baseline_distance = self._total_distance(baseline_routes)
        self._validate_routes(baseline_routes)
        self._record_initial_step(baseline_routes, baseline_distance)

        savings_routes = self._clarke_wright()
        savings_distance = self._total_distance(savings_routes)
        self._validate_routes(savings_routes)
        self.steps.append(
            SolveStep(
                index=len(self.steps) + 1,
                title="Savings Construction",
                detail=(
                    f"Built {len(savings_routes)} route(s) with Clarke-Wright savings. "
                    f"Distance after merge stage: {savings_distance:.2f} km."
                ),
                context_routes=self._to_route_summaries(savings_routes, "Savings", "savings"),
            )
        )

        improved_routes = [route[:] for route in savings_routes]
        self._improve_routes(improved_routes)
        improved_distance = self._total_distance(improved_routes)
        self._validate_routes(improved_routes)

        heuristic_routes, heuristic_distance, heuristic_name = min(
            (
                (baseline_routes, baseline_distance, "baseline"),
                (improved_routes, improved_distance, "improved"),
            ),
            key=lambda item: item[1],
        )

        final_index_routes = [route[:] for route in heuristic_routes]
        final_distance = heuristic_distance

        if len(self.orders) <= EXACT_ORDER_LIMIT:
            exact_routes = self._exact_optimal_routes()
            exact_distance = self._total_distance(exact_routes)
            self._validate_routes(exact_routes)
            final_index_routes = exact_routes
            final_distance = exact_distance
            self.steps.append(
                SolveStep(
                    index=len(self.steps) + 1,
                    title="Exact Optimization",
                    detail=(
                        f"Used exact subset dynamic programming across {len(self.orders)} order node(s). "
                        f"Optimal distance is {exact_distance:.2f} km."
                    ),
                    context_routes=self._to_route_summaries(exact_routes, "Exact", "final"),
                )
            )
        elif heuristic_name == "baseline":
            self.steps.append(
                SolveStep(
                    index=len(self.steps) + 1,
                    title="Best Heuristic",
                    detail=(
                        "Kept the baseline construction because the savings plus local-search path "
                        "did not beat it on total distance."
                    ),
                    context_routes=self._to_route_summaries(baseline_routes, "Baseline", "baseline"),
                )
            )

        final_routes = self._to_route_summaries(final_index_routes, "Final", "final")
        self.steps.append(
            SolveStep(
                index=len(self.steps) + 1,
                title="Final Answer",
                detail=(
                    f"Final highlighted solution uses {len(final_routes)} vehicle route(s). "
                    f"Distance: {final_distance:.2f} km. Improvement over baseline: "
                    f"{baseline_distance - final_distance:.2f} km."
                ),
                context_routes=final_routes,
            )
        )

        return SolveResult(
            baseline_routes=self._to_route_summaries(baseline_routes, "Baseline", "baseline"),
            savings_routes=self._to_route_summaries(savings_routes, "Savings", "savings"),
            final_routes=final_routes,
            steps=self.steps,
            baseline_distance_km=baseline_distance,
            savings_distance_km=savings_distance,
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

    def _record_initial_step(self, baseline_routes: list[list[int]], baseline_distance: float) -> None:
        top_edges = []
        depot_index = len(self.orders)
        for order_index, order in enumerate(self.orders):
            top_edges.append((self.distance_matrix[depot_index][order_index], order))
        top_edges.sort(key=lambda item: item[0])
        alternatives = [
            RouteOutline(
                name=f"Seed {index + 1}",
                node_ids=[self.depot.node_id, order.node_id],
                score=distance,
                reason=f"{order.label} is {distance:.2f} km from the depot.",
                style="alternative",
                color="#7b8a8b",
            )
            for index, (distance, order) in enumerate(top_edges[:3])
        ]
        self.steps.append(
            SolveStep(
                index=1,
                title="Prepared Distance Matrix",
                detail=(
                    f"Loaded {len(self.orders)} order node(s) and {self.vehicle_count} vehicle(s). "
                    f"Nearest-neighbor baseline distance is {baseline_distance:.2f} km."
                ),
                alternatives=alternatives,
                context_routes=self._to_route_summaries(baseline_routes, "Baseline", "baseline"),
            )
        )

    def _nearest_neighbor_baseline(self) -> list[list[int]]:
        if not self.orders:
            return []
        remaining = set(range(len(self.orders)))
        routes = [[] for _ in range(self.vehicle_count)]
        depot_index = len(self.orders)

        for route in routes:
            if not remaining:
                break
            seed = min(remaining, key=lambda idx: self.distance_matrix[depot_index][idx])
            route.append(seed)
            remaining.remove(seed)

        while remaining:
            best_pick = None
            for route_index, route in enumerate(routes):
                anchor = route[-1] if route else depot_index
                for candidate in remaining:
                    distance = self.distance_matrix[anchor][candidate]
                    if best_pick is None or distance < best_pick[0]:
                        best_pick = (distance, route_index, candidate)
            assert best_pick is not None
            _, route_index, candidate = best_pick
            routes[route_index].append(candidate)
            remaining.remove(candidate)

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

    def _improve_routes(self, routes: list[list[int]]) -> None:
        while True:
            improved = False
            for route_index, route in enumerate(routes):
                opt_candidates = self._two_opt_candidates(route)
                if not opt_candidates:
                    continue
                best_route, improvement, left_customer, right_customer = opt_candidates[0]
                routes[route_index] = best_route
                improved = True
                self.steps.append(
                    SolveStep(
                        index=len(self.steps) + 1,
                        title="2-opt Improvement",
                        detail=(
                            f"Reversed a segment inside Truck {route_index + 1} to remove an inefficient bend. "
                            f"Distance improved by {improvement:.2f} km."
                        ),
                        chosen=RouteOutline(
                            name=f"Truck {route_index + 1}",
                            node_ids=self._route_node_ids(best_route),
                            score=improvement,
                            reason=f"2-opt reversal between {left_customer} and {right_customer}.",
                            style="selected",
                            color=ROUTE_COLORS[route_index % len(ROUTE_COLORS)],
                        ),
                        focus_node_ids=[left_customer, right_customer],
                        context_routes=self._to_route_summaries(routes, "Final", "final"),
                    )
                )
            relocate = self._best_relocate(routes)
            if relocate is not None and relocate.improvement > 1e-6:
                routes[:] = relocate.updated_routes
                improved = True
                moved = self.orders[relocate.source_customer].label
                self.steps.append(
                    SolveStep(
                        index=len(self.steps) + 1,
                        title="Relocate Improvement",
                        detail=(
                            f"Moved {moved} into a better vehicle route because that shortened the total drive by "
                            f"{relocate.improvement:.2f} km."
                        ),
                        chosen=RouteOutline(
                            name=f"Move {moved}",
                            node_ids=self._route_node_ids(routes[relocate.target_index]),
                            score=relocate.improvement,
                            reason=f"{moved} fits better earlier in Truck {relocate.target_index + 1}.",
                            style="selected",
                            color=ROUTE_COLORS[relocate.target_index % len(ROUTE_COLORS)],
                        ),
                        focus_node_ids=[self.orders[relocate.source_customer].node_id],
                        context_routes=self._to_route_summaries(routes, "Final", "final"),
                    )
                )
            swap = self._best_swap(routes)
            if swap is not None and swap.improvement > 1e-6:
                routes[:] = swap.updated_routes
                improved = True
                left_label = self.orders[swap.left_customer].label
                right_label = self.orders[swap.right_customer].label
                self.steps.append(
                    SolveStep(
                        index=len(self.steps) + 1,
                        title="Swap Improvement",
                        detail=(
                            f"Swapped {left_label} with {right_label} because the exchange shortened the combined routes "
                            f"by {swap.improvement:.2f} km."
                        ),
                        chosen=RouteOutline(
                            name=f"Swap {left_label} / {right_label}",
                            node_ids=self._route_node_ids(routes[swap.left_index]),
                            score=swap.improvement,
                            reason="Swap reduced cross-route travel overlap.",
                            style="selected",
                            color=ROUTE_COLORS[swap.left_index % len(ROUTE_COLORS)],
                        ),
                        focus_node_ids=[
                            self.orders[swap.left_customer].node_id,
                            self.orders[swap.right_customer].node_id,
                        ],
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

    def _exact_optimal_routes(self) -> list[list[int]]:
        order_count = len(self.orders)
        if order_count == 0:
            return []

        full_mask = (1 << order_count) - 1
        route_costs, route_orders = self._subset_route_catalog()
        max_routes = min(self.vehicle_count, order_count)

        partition_costs = [[math.inf for _ in range(full_mask + 1)] for _ in range(max_routes + 1)]
        partition_choice = [[0 for _ in range(full_mask + 1)] for _ in range(max_routes + 1)]
        partition_costs[0][0] = 0.0

        for route_count in range(1, max_routes + 1):
            for mask in range(1, full_mask + 1):
                anchor = mask & -mask
                submask = mask
                while submask:
                    if submask & anchor:
                        previous_cost = partition_costs[route_count - 1][mask ^ submask]
                        if previous_cost < math.inf:
                            candidate_cost = previous_cost + route_costs[submask]
                            if candidate_cost + EPSILON < partition_costs[route_count][mask]:
                                partition_costs[route_count][mask] = candidate_cost
                                partition_choice[route_count][mask] = submask
                    submask = (submask - 1) & mask

        best_route_count = min(
            range(1, max_routes + 1),
            key=lambda route_count: partition_costs[route_count][full_mask],
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
