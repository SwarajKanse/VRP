"""Planning persistence and operational read models."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from vrp_platform.domain.entities import (
    RouteBoardEntry,
    RoutePlan,
    RunSummary,
    SolveIssueView,
    SolveResponse,
    Stop,
)
from vrp_platform.domain.enums import ObjectiveMode, OrderStatus, PlanStatus, VehicleCategory
from vrp_platform.repos.models import (
    OrderRecord,
    RoutePlanRecord,
    RouteStopRecord,
    SolveIssueRecord,
    SolveRunRecord,
    VehicleRecord,
)


class PlanningRepository:
    """Store solve runs, route plans, and solve diagnostics."""

    def __init__(self, session: Session):
        self.session = session

    def save_solve_response(self, response: SolveResponse, objective: ObjectiveMode) -> None:
        run_record = SolveRunRecord(
            id=response.run_id,
            objective=objective,
            metadata_json={
                **response.metadata,
                "validation_warnings": response.validation_warnings,
                "packing_status": response.packing_status,
            },
            objective_breakdown=response.objective_breakdown,
        )
        self.session.add(run_record)
        self.session.flush()

        for route in response.routes:
            route_record = RoutePlanRecord(
                id=route.route_id,
                solve_run_id=response.run_id,
                vehicle_id=route.vehicle_id,
                depot_id=route.depot_id,
                status=route.status,
                total_distance_km=route.total_distance_km,
                total_drive_min=route.total_drive_min,
                total_service_min=route.total_service_min,
                total_cost=route.total_cost,
                total_emissions_kg=route.total_emissions_kg,
            )
            self.session.add(route_record)
            self.session.flush()
            for stop in route.stops:
                self.session.add(self._stop_record(route.route_id, stop))
                order_row = self.session.get(OrderRecord, stop.order_id)
                if order_row is not None:
                    order_row.status = OrderStatus.PLANNED
                    order_row.route_plan_id = route.route_id

        for violation in response.unassigned_orders:
            self.session.add(
                SolveIssueRecord(
                    id=f"issue-{uuid.uuid4().hex[:10]}",
                    solve_run_id=response.run_id,
                    issue_kind="unassigned_order",
                    code=violation.code,
                    message=violation.message,
                    severity=violation.severity,
                    order_id=violation.order_id,
                )
            )
            if violation.order_id:
                order_row = self.session.get(OrderRecord, violation.order_id)
                if order_row is not None:
                    order_row.status = OrderStatus.PENDING
                    order_row.route_plan_id = None

        for warning in response.validation_warnings:
            self.session.add(
                SolveIssueRecord(
                    id=f"issue-{uuid.uuid4().hex[:10]}",
                    solve_run_id=response.run_id,
                    issue_kind="validation_warning",
                    code="VALIDATION_WARNING",
                    message=warning,
                    severity="warning",
                )
            )

        self.session.flush()

    def assign_driver(self, route_plan_id: str, driver_id: str) -> None:
        route = self.session.get(RoutePlanRecord, route_plan_id)
        if route is None:
            raise ValueError(f"Route plan {route_plan_id} not found")
        route.assigned_driver_id = driver_id
        route.status = PlanStatus.DISPATCHED
        self.session.flush()

    def recent_runs(self, limit: int = 10) -> list[RunSummary]:
        stmt = (
            select(SolveRunRecord)
            .options(
                selectinload(SolveRunRecord.routes).selectinload(RoutePlanRecord.stops),
                selectinload(SolveRunRecord.issues),
            )
            .order_by(SolveRunRecord.created_at.desc())
            .limit(limit)
        )
        runs = self.session.scalars(stmt).all()
        return [
            RunSummary(
                run_id=run.id,
                objective=run.objective,
                status=run.status,
                created_at=run.created_at,
                route_count=len(run.routes),
                planned_order_count=sum(len(route.stops) for route in run.routes),
                unassigned_count=sum(1 for issue in run.issues if issue.issue_kind == "unassigned_order"),
                total_distance_km=round(sum(route.total_distance_km for route in run.routes), 2),
                total_cost=round(sum(route.total_cost for route in run.routes), 2),
            )
            for run in runs
        ]

    def list_route_board(self, limit: int = 20) -> list[RouteBoardEntry]:
        stmt = (
            select(RoutePlanRecord)
            .join(OrderRecord, OrderRecord.route_plan_id == RoutePlanRecord.id)
            .join(SolveRunRecord, SolveRunRecord.id == RoutePlanRecord.solve_run_id)
            .options(selectinload(RoutePlanRecord.stops))
            .distinct()
            .order_by(SolveRunRecord.created_at.desc())
            .limit(limit)
        )
        rows = self.session.scalars(stmt).all()
        board: list[RouteBoardEntry] = []
        for row in rows:
            ordered_stops = sorted(row.stops, key=lambda item: item.sequence)
            vehicle = self.session.get(VehicleRecord, row.vehicle_id)
            fuel_used = row.total_distance_km * (vehicle.fuel_consumption_per_km if vehicle else 0.0)
            total_break_min = self._estimate_breaks(row.total_drive_min, vehicle)
            board.append(
                RouteBoardEntry(
                    route_id=row.id,
                    run_id=row.solve_run_id,
                    vehicle_id=row.vehicle_id,
                    vehicle_name=vehicle.name if vehicle else row.vehicle_id,
                    vehicle_category=vehicle.category if vehicle else VehicleCategory.VAN,
                    depot_id=row.depot_id,
                    driver_id=row.assigned_driver_id,
                    status=row.status,
                    stop_count=len(ordered_stops),
                    total_distance_km=row.total_distance_km,
                    total_drive_min=row.total_drive_min,
                    total_cost=row.total_cost,
                    total_emissions_kg=row.total_emissions_kg,
                    total_energy_cost=fuel_used * (vehicle.energy_unit_cost if vehicle else 0.0),
                    fuel_used=fuel_used,
                    total_break_min=total_break_min,
                    first_eta_minute=ordered_stops[0].arrival_minute if ordered_stops else None,
                    last_departure_minute=ordered_stops[-1].departure_minute if ordered_stops else None,
                )
            )
        return board

    def list_recent_issues(self, limit: int = 20) -> list[SolveIssueView]:
        stmt = select(SolveIssueRecord).order_by(SolveIssueRecord.created_at.desc()).limit(limit)
        rows = self.session.scalars(stmt).all()
        issues = [
            SolveIssueView(
                run_id=row.solve_run_id,
                code=row.code,
                message=row.message,
                severity=row.severity,
                order_id=row.order_id,
                issue_kind=row.issue_kind,
                created_at=row.created_at,
            )
            for row in rows
        ]
        return sorted(
            issues,
            key=lambda issue: (
                0 if issue.severity == "error" else 1,
                -(issue.created_at.timestamp() if issue.created_at else 0.0),
            ),
        )

    def get_route(self, route_plan_id: str) -> RoutePlan | None:
        route_row = self.session.get(RoutePlanRecord, route_plan_id)
        if route_row is None:
            return None
        return self._route_from_record(route_row)

    def list_recent_route_plans(self, limit: int = 10) -> list[RoutePlan]:
        stmt = (
            select(RoutePlanRecord)
            .join(OrderRecord, OrderRecord.route_plan_id == RoutePlanRecord.id)
            .join(SolveRunRecord, SolveRunRecord.id == RoutePlanRecord.solve_run_id)
            .distinct()
            .order_by(SolveRunRecord.created_at.desc())
            .limit(limit)
        )
        rows = self.session.scalars(stmt).all()
        return [self._route_from_record(row) for row in rows]

    def get_route_by_order(self, order_id: str) -> RoutePlan | None:
        order_row = self.session.get(OrderRecord, order_id)
        if order_row is None or not order_row.route_plan_id:
            return None
        return self.get_route(order_row.route_plan_id)

    def get_active_route_for_driver(self, driver_id: str) -> RoutePlan | None:
        stmt = (
            select(RoutePlanRecord)
            .join(OrderRecord, OrderRecord.route_plan_id == RoutePlanRecord.id)
            .join(SolveRunRecord, SolveRunRecord.id == RoutePlanRecord.solve_run_id)
            .where(RoutePlanRecord.assigned_driver_id == driver_id)
            .where(RoutePlanRecord.status.in_([PlanStatus.OPTIMIZED, PlanStatus.DISPATCHED]))
            .distinct()
            .order_by(SolveRunRecord.created_at.desc())
        )
        route_row = self.session.scalars(stmt).first()
        if route_row is None:
            return None
        return self._route_from_record(route_row)

    def _route_from_record(self, route_row: RoutePlanRecord) -> RoutePlan:
        vehicle = self.session.get(VehicleRecord, route_row.vehicle_id)
        stop_rows = list(
            self.session.scalars(
                select(RouteStopRecord)
                .where(RouteStopRecord.route_plan_id == route_row.id)
                .order_by(RouteStopRecord.sequence)
            ).all()
        )
        return RoutePlan(
            route_id=route_row.id,
            vehicle_id=route_row.vehicle_id,
            depot_id=route_row.depot_id,
            stops=[
                Stop(
                    stop_id=row.id,
                    order_id=row.order_id,
                    sequence=row.sequence,
                    arrival_minute=row.arrival_minute,
                    service_start_minute=row.service_start_minute,
                    departure_minute=row.departure_minute,
                    distance_from_previous_km=row.distance_from_previous_km,
                    travel_time_from_previous_min=row.travel_time_from_previous_min,
                )
                for row in stop_rows
            ],
            total_distance_km=route_row.total_distance_km,
            total_drive_min=route_row.total_drive_min,
            total_service_min=route_row.total_service_min,
            total_cost=route_row.total_cost,
            total_emissions_kg=route_row.total_emissions_kg,
            total_energy_cost=route_row.total_distance_km * (vehicle.fuel_consumption_per_km if vehicle else 0.0) * (vehicle.energy_unit_cost if vehicle else 0.0),
            fuel_used=route_row.total_distance_km * (vehicle.fuel_consumption_per_km if vehicle else 0.0),
            total_break_min=self._estimate_breaks(route_row.total_drive_min, vehicle),
            status=route_row.status,
        )

    def _stop_record(self, route_id: str, stop: Stop) -> RouteStopRecord:
        return RouteStopRecord(
            id=stop.stop_id,
            route_plan_id=route_id,
            order_id=stop.order_id,
            sequence=stop.sequence,
            arrival_minute=stop.arrival_minute,
            service_start_minute=stop.service_start_minute,
            departure_minute=stop.departure_minute,
            distance_from_previous_km=stop.distance_from_previous_km,
            travel_time_from_previous_min=stop.travel_time_from_previous_min,
        )

    def _estimate_breaks(self, total_drive_min: float, vehicle: VehicleRecord | None) -> float:
        if vehicle is None or vehicle.max_continuous_drive_min <= 0:
            return 0.0
        break_count = int(max(0.0, (total_drive_min - 1e-6) // vehicle.max_continuous_drive_min))
        return break_count * vehicle.required_break_min if break_count > 0 else 0.0
