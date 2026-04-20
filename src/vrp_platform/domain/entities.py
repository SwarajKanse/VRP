"""Primary domain entities."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from vrp_platform.domain.enums import (
    DeliveryEventType,
    ObjectiveMode,
    OrderStatus,
    PlanStatus,
    VehicleCategory,
    VehicleEnergyType,
)


@dataclass(slots=True)
class Depot:
    id: str
    name: str
    latitude: float
    longitude: float
    address: str = ""


@dataclass(slots=True)
class Vehicle:
    id: str
    name: str
    capacity_kg: float
    capacity_volume_m3: float
    depot_id: str
    average_speed_kmh: float
    category: VehicleCategory = VehicleCategory.VAN
    max_shift_minutes: float = 600.0
    cost_per_km: float = 1.0
    labor_cost_per_hour: float = 12.0
    emissions_kg_per_km: float = 0.25
    energy_type: VehicleEnergyType = VehicleEnergyType.DIESEL
    fuel_consumption_per_km: float = 0.12
    energy_unit_cost: float = 1.0
    max_continuous_drive_min: float = 240.0
    required_break_min: float = 30.0
    cargo_length_m: float = 2.5
    cargo_width_m: float = 1.5
    cargo_height_m: float = 1.5
    assigned_driver_id: str | None = None


@dataclass(slots=True)
class Shift:
    id: str
    vehicle_id: str
    start_minute: float
    end_minute: float


@dataclass(slots=True)
class Order:
    id: str
    external_ref: str
    customer_name: str
    latitude: float
    longitude: float
    demand_kg: float
    volume_m3: float
    service_time_min: float
    time_window_start_min: float
    time_window_end_min: float
    address: str = ""
    priority: int = 1
    fragile: bool = False
    orientation_locked: bool = False
    package_dimensions_m: tuple[float, float, float] = (0.4, 0.3, 0.3)
    status: OrderStatus = OrderStatus.PENDING


@dataclass(slots=True)
class Stop:
    stop_id: str
    order_id: str
    sequence: int
    arrival_minute: float
    service_start_minute: float
    departure_minute: float
    distance_from_previous_km: float
    travel_time_from_previous_min: float


@dataclass(slots=True)
class RouteLeg:
    from_stop_id: str
    to_stop_id: str
    distance_km: float
    travel_time_min: float
    eta_minute: float


@dataclass(slots=True)
class RoutePlan:
    route_id: str
    vehicle_id: str
    depot_id: str
    stops: list[Stop] = field(default_factory=list)
    legs: list[RouteLeg] = field(default_factory=list)
    status: PlanStatus = PlanStatus.OPTIMIZED
    total_distance_km: float = 0.0
    total_drive_min: float = 0.0
    total_service_min: float = 0.0
    total_cost: float = 0.0
    total_emissions_kg: float = 0.0
    total_energy_cost: float = 0.0
    fuel_used: float = 0.0
    total_break_min: float = 0.0


@dataclass(slots=True)
class Violation:
    code: str
    order_id: str | None
    message: str
    severity: str = "error"


@dataclass(slots=True)
class ConstraintSet:
    enforce_time_windows: bool = True
    enforce_capacity: bool = True
    enforce_volume: bool = True
    enforce_shift_time: bool = True
    enforce_breaks: bool = True
    consider_live_traffic: bool = True
    avoid_incidents: bool = True
    departure_minute: float = 480.0


@dataclass(slots=True)
class TrafficIncident:
    incident_id: str
    name: str
    latitude: float
    longitude: float
    radius_km: float
    delay_multiplier: float
    status: str = "active"
    severity: str = "medium"
    description: str = ""


@dataclass(slots=True)
class MapPoint:
    latitude: float
    longitude: float
    label: str
    kind: str


@dataclass(slots=True)
class DriverBreakWindow:
    start_minute: float
    duration_min: float
    reason: str


@dataclass(slots=True)
class VehicleLivePosition:
    route_id: str
    vehicle_id: str
    vehicle_name: str
    vehicle_category: VehicleCategory
    driver_id: str | None
    latitude: float
    longitude: float
    status: str
    next_stop_label: str
    eta_minute: float | None


@dataclass(slots=True)
class RouteMapView:
    route_id: str
    vehicle_id: str
    vehicle_name: str
    vehicle_category: VehicleCategory
    driver_id: str | None
    status: PlanStatus
    path_points: list[MapPoint] = field(default_factory=list)
    live_position: VehicleLivePosition | None = None
    traffic_delay_min: float = 0.0
    navigation_url: str = ""


@dataclass(slots=True)
class WarehouseLoadInstruction:
    load_sequence: int
    stop_sequence: int
    order_id: str
    external_ref: str
    customer_name: str
    slot_label: str
    notes: str


@dataclass(slots=True)
class WarehouseRoutePlan:
    route_id: str
    vehicle_id: str
    vehicle_name: str
    vehicle_category: VehicleCategory
    total_weight_kg: float
    total_volume_m3: float
    utilization_pct: float
    instructions: list[WarehouseLoadInstruction] = field(default_factory=list)


@dataclass(slots=True)
class ReoptimizationEvent:
    event_id: str
    triggered_at: datetime
    reason: str
    added_order_ids: list[str] = field(default_factory=list)
    removed_order_ids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DeliveryEvent:
    event_id: str
    order_id: str
    driver_id: str
    event_type: DeliveryEventType
    occurred_at: datetime
    notes: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SolveRequest:
    depots: list[Depot]
    vehicles: list[Vehicle]
    orders: list[Order]
    shifts: list[Shift] = field(default_factory=list)
    constraints: ConstraintSet = field(default_factory=ConstraintSet)
    objective: ObjectiveMode = ObjectiveMode.COST
    travel_provider: str = "hybrid"
    traffic_incidents: list[TrafficIncident] = field(default_factory=list)


@dataclass(slots=True)
class SolveResponse:
    run_id: str
    routes: list[RoutePlan]
    unassigned_orders: list[Violation]
    objective_breakdown: dict[str, float]
    validation_warnings: list[str]
    packing_status: dict[str, Any]
    metadata: dict[str, Any]


@dataclass(slots=True)
class RunSummary:
    run_id: str
    objective: ObjectiveMode
    status: PlanStatus
    created_at: datetime
    route_count: int
    planned_order_count: int
    unassigned_count: int
    total_distance_km: float
    total_cost: float


@dataclass(slots=True)
class RouteBoardEntry:
    route_id: str
    run_id: str
    vehicle_id: str
    vehicle_name: str
    vehicle_category: VehicleCategory
    depot_id: str
    driver_id: str | None
    status: PlanStatus
    stop_count: int
    total_distance_km: float
    total_drive_min: float
    total_cost: float
    total_emissions_kg: float
    total_energy_cost: float
    fuel_used: float
    total_break_min: float
    first_eta_minute: float | None
    last_departure_minute: float | None


@dataclass(slots=True)
class SolveIssueView:
    run_id: str
    code: str
    message: str
    severity: str
    order_id: str | None = None
    issue_kind: str = "unassigned_order"
    created_at: datetime | None = None


@dataclass(slots=True)
class TimelineEvent:
    event_id: str
    source: str
    occurred_at: datetime
    label: str
    details: str


@dataclass(slots=True)
class ShipmentSnapshot:
    order: Order
    route_id: str | None
    vehicle_id: str | None
    route_status: PlanStatus | None
    stop_sequence: int | None
    eta_minute: float | None
    path_points: list[MapPoint] = field(default_factory=list)
    navigation_url: str = ""
    customer_events: list[TimelineEvent] = field(default_factory=list)
    delivery_events: list[TimelineEvent] = field(default_factory=list)


@dataclass(slots=True)
class DriverStopView:
    stop_id: str
    order_id: str
    external_ref: str
    customer_name: str
    sequence: int
    eta_minute: float
    address: str
    latitude: float
    longitude: float
    status: OrderStatus


@dataclass(slots=True)
class DriverRouteView:
    route_id: str
    vehicle_id: str
    vehicle_name: str
    vehicle_category: VehicleCategory
    driver_id: str
    status: PlanStatus
    total_distance_km: float
    total_drive_min: float
    total_energy_cost: float = 0.0
    fuel_used: float = 0.0
    total_break_min: float = 0.0
    break_windows: list[DriverBreakWindow] = field(default_factory=list)
    path_points: list[MapPoint] = field(default_factory=list)
    navigation_url: str = ""
    stops: list[DriverStopView] = field(default_factory=list)


@dataclass(slots=True)
class DispatcherSnapshot:
    orders: list[Order] = field(default_factory=list)
    total_order_count: int = 0
    filtered_order_count: int = 0
    pending_order_count: int = 0
    order_page: int = 1
    order_page_size: int = 25
    routes: list[RouteBoardEntry] = field(default_factory=list)
    recent_runs: list[RunSummary] = field(default_factory=list)
    issues: list[SolveIssueView] = field(default_factory=list)
    map_routes: list[RouteMapView] = field(default_factory=list)
    fleet_positions: list[VehicleLivePosition] = field(default_factory=list)
    traffic_incidents: list[TrafficIncident] = field(default_factory=list)
    warehouse_plans: list[WarehouseRoutePlan] = field(default_factory=list)
