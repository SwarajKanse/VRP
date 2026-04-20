"""SQLAlchemy ORM models."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vrp_platform.db import Base
from vrp_platform.domain.enums import (
    DeliveryEventType,
    ObjectiveMode,
    OrderStatus,
    PlanStatus,
    VehicleCategory,
    VehicleEnergyType,
)


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class DepotRecord(Base):
    __tablename__ = "depots"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    address: Mapped[str] = mapped_column(Text, default="")


class VehicleRecord(Base):
    __tablename__ = "vehicles"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    depot_id: Mapped[str] = mapped_column(ForeignKey("depots.id"))
    category: Mapped[VehicleCategory] = mapped_column(
        Enum(VehicleCategory),
        default=VehicleCategory.VAN,
    )
    capacity_kg: Mapped[float] = mapped_column(Float)
    capacity_volume_m3: Mapped[float] = mapped_column(Float)
    average_speed_kmh: Mapped[float] = mapped_column(Float)
    max_shift_minutes: Mapped[float] = mapped_column(Float, default=600.0)
    cost_per_km: Mapped[float] = mapped_column(Float, default=1.0)
    labor_cost_per_hour: Mapped[float] = mapped_column(Float, default=12.0)
    emissions_kg_per_km: Mapped[float] = mapped_column(Float, default=0.25)
    energy_type: Mapped[VehicleEnergyType] = mapped_column(
        Enum(VehicleEnergyType),
        default=VehicleEnergyType.DIESEL,
    )
    fuel_consumption_per_km: Mapped[float] = mapped_column(Float, default=0.12)
    energy_unit_cost: Mapped[float] = mapped_column(Float, default=1.0)
    max_continuous_drive_min: Mapped[float] = mapped_column(Float, default=240.0)
    required_break_min: Mapped[float] = mapped_column(Float, default=30.0)
    cargo_length_m: Mapped[float] = mapped_column(Float, default=2.5)
    cargo_width_m: Mapped[float] = mapped_column(Float, default=1.5)
    cargo_height_m: Mapped[float] = mapped_column(Float, default=1.5)


class ShiftRecord(Base):
    __tablename__ = "shifts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    vehicle_id: Mapped[str] = mapped_column(ForeignKey("vehicles.id"))
    start_minute: Mapped[float] = mapped_column(Float)
    end_minute: Mapped[float] = mapped_column(Float)


class OrderRecord(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    external_ref: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    customer_name: Mapped[str] = mapped_column(String(128))
    latitude: Mapped[float] = mapped_column(Float, index=True)
    longitude: Mapped[float] = mapped_column(Float, index=True)
    demand_kg: Mapped[float] = mapped_column(Float)
    volume_m3: Mapped[float] = mapped_column(Float)
    service_time_min: Mapped[float] = mapped_column(Float, default=10.0)
    time_window_start_min: Mapped[float] = mapped_column(Float, default=0.0)
    time_window_end_min: Mapped[float] = mapped_column(Float, default=600.0)
    address: Mapped[str] = mapped_column(Text, default="")
    priority: Mapped[int] = mapped_column(Integer, default=1)
    fragile: Mapped[bool] = mapped_column(default=False)
    orientation_locked: Mapped[bool] = mapped_column(default=False)
    package_dimensions: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), default=OrderStatus.PENDING, index=True)
    route_plan_id: Mapped[str | None] = mapped_column(ForeignKey("route_plans.id"), nullable=True, index=True)


class SolveRunRecord(Base):
    __tablename__ = "solve_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    objective: Mapped[ObjectiveMode] = mapped_column(Enum(ObjectiveMode))
    status: Mapped[PlanStatus] = mapped_column(Enum(PlanStatus), default=PlanStatus.OPTIMIZED)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    objective_breakdown: Mapped[dict] = mapped_column(JSON, default=dict)

    routes: Mapped[list["RoutePlanRecord"]] = relationship(back_populates="solve_run")
    issues: Mapped[list["SolveIssueRecord"]] = relationship(back_populates="solve_run")


class RoutePlanRecord(Base):
    __tablename__ = "route_plans"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    solve_run_id: Mapped[str] = mapped_column(ForeignKey("solve_runs.id"))
    vehicle_id: Mapped[str] = mapped_column(ForeignKey("vehicles.id"))
    depot_id: Mapped[str] = mapped_column(ForeignKey("depots.id"))
    status: Mapped[PlanStatus] = mapped_column(Enum(PlanStatus), default=PlanStatus.OPTIMIZED)
    total_distance_km: Mapped[float] = mapped_column(Float, default=0.0)
    total_drive_min: Mapped[float] = mapped_column(Float, default=0.0)
    total_service_min: Mapped[float] = mapped_column(Float, default=0.0)
    total_cost: Mapped[float] = mapped_column(Float, default=0.0)
    total_emissions_kg: Mapped[float] = mapped_column(Float, default=0.0)
    assigned_driver_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    solve_run: Mapped[SolveRunRecord] = relationship(back_populates="routes")
    stops: Mapped[list["RouteStopRecord"]] = relationship(back_populates="route_plan")


class SolveIssueRecord(Base):
    __tablename__ = "solve_issues"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    solve_run_id: Mapped[str] = mapped_column(ForeignKey("solve_runs.id"))
    issue_kind: Mapped[str] = mapped_column(String(64), default="unassigned_order")
    code: Mapped[str] = mapped_column(String(64))
    message: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(32), default="error")
    order_id: Mapped[str | None] = mapped_column(ForeignKey("orders.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    solve_run: Mapped[SolveRunRecord] = relationship(back_populates="issues")


class RouteStopRecord(Base):
    __tablename__ = "route_stops"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    route_plan_id: Mapped[str] = mapped_column(ForeignKey("route_plans.id"))
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"))
    sequence: Mapped[int] = mapped_column(Integer)
    arrival_minute: Mapped[float] = mapped_column(Float)
    service_start_minute: Mapped[float] = mapped_column(Float)
    departure_minute: Mapped[float] = mapped_column(Float)
    distance_from_previous_km: Mapped[float] = mapped_column(Float)
    travel_time_from_previous_min: Mapped[float] = mapped_column(Float)

    route_plan: Mapped[RoutePlanRecord] = relationship(back_populates="stops")


class CustomerEventRecord(Base):
    __tablename__ = "customer_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    order_id: Mapped[str] = mapped_column(String(64))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


class DeliveryEventRecord(Base):
    __tablename__ = "delivery_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"))
    driver_id: Mapped[str] = mapped_column(String(64))
    event_type: Mapped[DeliveryEventType] = mapped_column(Enum(DeliveryEventType))
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    notes: Mapped[str] = mapped_column(Text, default="")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


class AuditLogRecord(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    actor: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(128))
    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
