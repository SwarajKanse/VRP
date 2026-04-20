"""Background task wrappers."""

from __future__ import annotations

from vrp_platform.bootstrap import bootstrap_platform
from vrp_platform.domain.entities import DeliveryEvent, SolveRequest


def solve_plan_job(request: SolveRequest) -> dict:
    app = bootstrap_platform()
    response = app.solve_plan(request)
    return {
        "run_id": response.run_id,
        "routes": len(response.routes),
        "unassigned": len(response.unassigned_orders),
    }


def reoptimize_plan_job(request: SolveRequest, reason: str) -> dict:
    app = bootstrap_platform()
    response = app.reoptimize_plan(request, reason)
    return {"run_id": response.run_id, "reason": reason}


def publish_customer_updates_job(request: SolveRequest) -> int:
    app = bootstrap_platform()
    response = app.solve_plan(request)
    return app.publish_customer_updates(response)


def generate_manifests_job(request: SolveRequest) -> dict[str, str]:
    app = bootstrap_platform()
    response = app.solve_plan(request)
    return app.generate_manifests(response)


def record_delivery_event_job(event: DeliveryEvent) -> None:
    app = bootstrap_platform()
    app.record_delivery_event(event)
