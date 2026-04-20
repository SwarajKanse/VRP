"""Planning service orchestration."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Protocol

from vrp_platform.domain.entities import DeliveryEvent, SolveRequest, SolveResponse, Violation
from vrp_platform.repos.events import EventRepository
from vrp_platform.repos.orders import OrderRepository
from vrp_platform.repos.planning import PlanningRepository
from vrp_platform.services.events import ExecutionService
from vrp_platform.services.manifests import ManifestService


class Solver(Protocol):
    """Minimal protocol for primary and fallback solvers."""

    def solve(self, request: SolveRequest) -> SolveResponse:
        """Solve a planning request."""


@dataclass(slots=True)
class PlanningService:
    """High-level planning use cases exposed to UI and worker layers."""

    optimizer: Solver
    order_repo: OrderRepository
    planning_repo: PlanningRepository
    event_repo: EventRepository
    fallback_solver: Solver | None = None

    def solve_plan(self, request: SolveRequest) -> SolveResponse:
        try:
            response = self.optimizer.solve(request)
            response.metadata.setdefault("solver", "primary_route_optimizer")
        except Exception as exc:
            self.event_repo.add_audit_log(
                "system",
                "solve_plan_failed",
                "optimizer",
                f"opt-{uuid.uuid4().hex[:8]}",
                {
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
            )
            response = self._fallback_response(request, exc)
        self.planning_repo.save_solve_response(response, request.objective)
        self.event_repo.add_audit_log("system", "solve_plan", "solve_run", response.run_id, response.metadata)
        return response

    def reoptimize_plan(self, request: SolveRequest, reason: str) -> SolveResponse:
        response = self.solve_plan(request)
        self.event_repo.add_audit_log(
            "system",
            "reoptimize_plan",
            "solve_run",
            response.run_id,
            {"reason": reason, **response.metadata},
        )
        return response

    def assign_driver(self, route_plan_id: str, driver_id: str, actor: str) -> None:
        self.planning_repo.assign_driver(route_plan_id, driver_id)
        self.event_repo.add_audit_log(
            actor, "assign_driver", "route_plan", route_plan_id, {"driver_id": driver_id}
        )

    def publish_customer_updates(self, response: SolveResponse) -> int:
        return ExecutionService(self.order_repo, self.event_repo).publish_customer_updates(response)

    def record_delivery_event(self, event: DeliveryEvent) -> None:
        ExecutionService(self.order_repo, self.event_repo).record_delivery_event(event)
        self.event_repo.add_audit_log(
            event.driver_id,
            "record_delivery_event",
            "order",
            event.order_id,
            {"event_type": event.event_type.value},
        )

    def generate_manifests(self, response: SolveResponse) -> dict[str, str]:
        planned_order_ids = [stop.order_id for route in response.routes for stop in route.stops]
        orders = self.order_repo.get_orders(planned_order_ids)
        manifests = ManifestService().generate_manifests(response.routes, orders)
        self.event_repo.add_audit_log(
            "system",
            "generate_manifests",
            "solve_run",
            response.run_id,
            {"manifest_count": len(manifests)},
        )
        return manifests

    def _fallback_response(self, request: SolveRequest, exc: Exception) -> SolveResponse:
        if self.fallback_solver is not None:
            try:
                response = self.fallback_solver.solve(request)
                response.validation_warnings.append(
                    f"Main optimizer failed: {type(exc).__name__}: {exc}"
                )
                response.metadata["primary_optimizer_error"] = str(exc)
                response.metadata["primary_optimizer_error_type"] = type(exc).__name__
                response.metadata.setdefault("solver", "fallback_nearest_neighbor")
                self.event_repo.add_audit_log(
                    "system",
                    "solve_plan_fallback",
                    "solve_run",
                    response.run_id,
                    response.metadata,
                )
                return response
            except Exception as fallback_exc:
                self.event_repo.add_audit_log(
                    "system",
                    "solve_plan_fallback_failed",
                    "optimizer",
                    f"opt-{uuid.uuid4().hex[:8]}",
                    {
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                        "fallback_error_type": type(fallback_exc).__name__,
                        "fallback_error": str(fallback_exc),
                    },
                )
                return SolveResponse(
                    run_id=f"error-{uuid.uuid4().hex[:10]}",
                    routes=[],
                    unassigned_orders=[
                        Violation(
                            code="SOLVER_ERROR",
                            order_id=None,
                            message=(
                                "Both primary and fallback planning failed: "
                                f"{type(exc).__name__}: {exc}; "
                                f"{type(fallback_exc).__name__}: {fallback_exc}"
                            ),
                        )
                    ],
                    objective_breakdown={},
                    validation_warnings=[
                        "Both primary and fallback solvers failed; no routes were generated."
                    ],
                    packing_status={},
                    metadata={
                        "solver": "error_response",
                        "primary_optimizer_error": str(exc),
                        "fallback_error": str(fallback_exc),
                    },
                )

        return SolveResponse(
            run_id=f"error-{uuid.uuid4().hex[:10]}",
            routes=[],
            unassigned_orders=[
                Violation(
                    code="SOLVER_ERROR",
                    order_id=None,
                    message=f"Primary planning failed and no fallback solver is configured: {type(exc).__name__}: {exc}",
                )
            ],
            objective_breakdown={},
            validation_warnings=[
                "Primary solver failed and no fallback solver is configured."
            ],
            packing_status={},
            metadata={
                "solver": "error_response",
                "primary_optimizer_error": str(exc),
                "primary_optimizer_error_type": type(exc).__name__,
            },
        )
