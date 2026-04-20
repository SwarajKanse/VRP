"""Application bootstrap helpers."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session, sessionmaker

from vrp_platform.config import PlatformSettings, get_settings
from vrp_platform.db import Base, create_session_factory, ensure_schema, session_scope
from vrp_platform.domain.entities import (
    ConstraintSet,
    DeliveryEvent,
    Depot,
    DispatcherSnapshot,
    Order,
    ShipmentSnapshot,
    Shift,
    SolveRequest,
    SolveResponse,
    Vehicle,
)
from vrp_platform.domain.enums import ObjectiveMode, OrderStatus, VehicleEnergyType
from vrp_platform.domain.enums import VehicleCategory
from vrp_platform.integrations.travel import HybridTravelMatrixProvider
from vrp_platform.logging import configure_logging
from vrp_platform.optimizer.engine import RouteOptimizer
from vrp_platform.optimizer.fallback import FallbackSolver
from vrp_platform.repos.catalog import CatalogRepository
from vrp_platform.repos.events import EventRepository
from vrp_platform.repos.models import DepotRecord, ShiftRecord, VehicleRecord
from vrp_platform.repos.orders import OrderRepository
from vrp_platform.repos.planning import PlanningRepository
from vrp_platform.services.auth import AuthService
from vrp_platform.services.ingestion import IngestionService
from vrp_platform.services.operations import OperationsService
from vrp_platform.services.planning import PlanningService


@dataclass(slots=True)
class PlatformApp:
    settings: PlatformSettings
    session_factory: sessionmaker[Session]
    auth_service: AuthService

    def ingest_manifest(self, manifest_bytes: bytes) -> tuple[list[Order], list[str]]:
        with session_scope(self.session_factory) as session:
            service = self._ingestion_service(session)
            orders = service.ingest_manifest(manifest_bytes)
            warnings = service.validate_orders(orders)
            return orders, warnings

    def validate_orders(self, orders: list[Order]) -> list[str]:
        with session_scope(self.session_factory) as session:
            return self._ingestion_service(session).validate_orders(orders)

    def solve_plan(self, request: SolveRequest) -> SolveResponse:
        with session_scope(self.session_factory) as session:
            return self._planning_service(session).solve_plan(request)

    def reoptimize_plan(self, request: SolveRequest, reason: str) -> SolveResponse:
        with session_scope(self.session_factory) as session:
            return self._planning_service(session).reoptimize_plan(request, reason)

    def assign_driver(self, route_plan_id: str, driver_id: str, actor: str) -> None:
        with session_scope(self.session_factory) as session:
            self._planning_service(session).assign_driver(route_plan_id, driver_id, actor)

    def publish_customer_updates(self, response: SolveResponse) -> int:
        with session_scope(self.session_factory) as session:
            return self._planning_service(session).publish_customer_updates(response)

    def record_delivery_event(self, event: DeliveryEvent) -> None:
        with session_scope(self.session_factory) as session:
            self._planning_service(session).record_delivery_event(event)

    def generate_manifests(self, response: SolveResponse) -> dict[str, str]:
        with session_scope(self.session_factory) as session:
            return self._planning_service(session).generate_manifests(response)

    def dispatcher_snapshot(
        self,
        search_term: str = "",
        statuses: list[OrderStatus] | None = None,
        sort_by: str = "external_ref",
        descending: bool = False,
        page: int = 1,
        page_size: int = 25,
    ) -> DispatcherSnapshot:
        with session_scope(self.session_factory) as session:
            return self._operations_service(session).dispatcher_snapshot_filtered(
                search_term=search_term,
                statuses=statuses,
                sort_by=sort_by,
                descending=descending,
                page=page,
                page_size=page_size,
            )

    def build_solve_request(
        self,
        objective: ObjectiveMode,
        order_ids: list[str] | None = None,
    ) -> SolveRequest:
        with session_scope(self.session_factory) as session:
            return self._operations_service(session).build_solve_request(objective, order_ids)

    def find_shipment(self, external_ref: str) -> ShipmentSnapshot | None:
        with session_scope(self.session_factory) as session:
            return self._operations_service(session).find_shipment(external_ref)

    def driver_route(self, driver_id: str):
        with session_scope(self.session_factory) as session:
            return self._operations_service(session).driver_route(driver_id)

    def _planning_service(self, session: Session) -> PlanningService:
        return PlanningService(
            optimizer=RouteOptimizer(HybridTravelMatrixProvider(self.settings)),
            fallback_solver=FallbackSolver(HybridTravelMatrixProvider(self.settings)),
            order_repo=OrderRepository(session),
            planning_repo=PlanningRepository(session),
            event_repo=EventRepository(session),
        )

    def _ingestion_service(self, session: Session) -> IngestionService:
        return IngestionService(OrderRepository(session))

    def _operations_service(self, session: Session) -> OperationsService:
        return OperationsService(
            settings=self.settings,
            catalog_repo=CatalogRepository(session),
            order_repo=OrderRepository(session),
            planning_repo=PlanningRepository(session),
            event_repo=EventRepository(session),
        )


def bootstrap_platform(settings: PlatformSettings | None = None) -> PlatformApp:
    """Create the platform application services."""

    settings = settings or get_settings()
    configure_logging(settings.log_level)
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    session_factory = create_session_factory(settings)
    engine = session_factory.kw["bind"]
    ensure_schema(engine)
    Base.metadata.create_all(bind=engine)
    ensure_schema(engine)
    _seed_demo_catalog(session_factory, settings)
    return PlatformApp(
        settings=settings,
        session_factory=session_factory,
        auth_service=AuthService(),
    )


def build_demo_request() -> SolveRequest:
    """Return a small demo planning request."""

    depot = Depot(id="depot-mumbai", name="Mumbai Hub", latitude=19.076, longitude=72.8777, address="Mumbai")
    vehicles = [
        Vehicle(
            id="veh-pickup-1",
            name="Pickup Truck 1",
            capacity_kg=900,
            capacity_volume_m3=8,
            depot_id=depot.id,
            average_speed_kmh=32,
            category=VehicleCategory.PICKUP_TRUCK,
            cost_per_km=1.35,
            labor_cost_per_hour=14,
            emissions_kg_per_km=0.19,
            energy_type=VehicleEnergyType.DIESEL,
            fuel_consumption_per_km=0.14,
            energy_unit_cost=97.0,
            max_continuous_drive_min=210,
            required_break_min=25,
            cargo_length_m=2.4,
            cargo_width_m=1.6,
            cargo_height_m=1.5,
        ),
        Vehicle(
            id="veh-van-ev-1",
            name="EV Van 1",
            capacity_kg=800,
            capacity_volume_m3=9,
            depot_id=depot.id,
            average_speed_kmh=30,
            category=VehicleCategory.VAN,
            cost_per_km=0.9,
            labor_cost_per_hour=14,
            emissions_kg_per_km=0.02,
            energy_type=VehicleEnergyType.EV,
            fuel_consumption_per_km=0.18,
            energy_unit_cost=11.0,
            max_continuous_drive_min=180,
            required_break_min=20,
            cargo_length_m=2.7,
            cargo_width_m=1.7,
            cargo_height_m=1.6,
        ),
        Vehicle(
            id="veh-bike-1",
            name="Bike Courier 1",
            capacity_kg=35,
            capacity_volume_m3=0.25,
            depot_id=depot.id,
            average_speed_kmh=24,
            category=VehicleCategory.TWO_WHEELER,
            cost_per_km=0.45,
            labor_cost_per_hour=10,
            emissions_kg_per_km=0.05,
            energy_type=VehicleEnergyType.PETROL,
            fuel_consumption_per_km=0.03,
            energy_unit_cost=106.0,
            max_continuous_drive_min=120,
            required_break_min=15,
            cargo_length_m=0.6,
            cargo_width_m=0.45,
            cargo_height_m=0.45,
        ),
    ]
    orders = [
        Order(
            id="ord-1",
            external_ref="SO-1001",
            customer_name="Bandra Boutique",
            latitude=19.0596,
            longitude=72.8295,
            demand_kg=150,
            volume_m3=1.2,
            service_time_min=15,
            time_window_start_min=540,
            time_window_end_min=660,
            package_dimensions_m=(1.1, 0.8, 0.5),
        ),
        Order(
            id="ord-2",
            external_ref="SO-1002",
            customer_name="Andheri Medical",
            latitude=19.1136,
            longitude=72.8697,
            demand_kg=220,
            volume_m3=1.4,
            service_time_min=20,
            time_window_start_min=570,
            time_window_end_min=720,
            fragile=True,
            package_dimensions_m=(1.2, 0.8, 0.6),
        ),
        Order(
            id="ord-3",
            external_ref="SO-1003",
            customer_name="Powai Electronics",
            latitude=19.1176,
            longitude=72.906,
            demand_kg=310,
            volume_m3=2.0,
            service_time_min=25,
            time_window_start_min=600,
            time_window_end_min=780,
            orientation_locked=True,
            package_dimensions_m=(1.4, 0.8, 0.7),
        ),
    ]
    shifts = [
        Shift(id="shift-pickup-1", vehicle_id="veh-pickup-1", start_minute=480, end_minute=1080),
        Shift(id="shift-van-ev-1", vehicle_id="veh-van-ev-1", start_minute=480, end_minute=1080),
        Shift(id="shift-bike-1", vehicle_id="veh-bike-1", start_minute=480, end_minute=960),
    ]
    return SolveRequest(
        depots=[depot],
        vehicles=vehicles,
        orders=orders,
        shifts=shifts,
        constraints=ConstraintSet(departure_minute=480),
        objective=ObjectiveMode.COST,
    )


def _seed_demo_catalog(session_factory: sessionmaker[Session], settings: PlatformSettings) -> None:
    if not settings.seed_demo_data:
        return
    with session_scope(session_factory) as session:
        depot = session.get(DepotRecord, "depot-mumbai")
        if depot is None:
            depot = DepotRecord(
                id="depot-mumbai",
                name="Mumbai Hub",
                latitude=19.076,
                longitude=72.8777,
                address="Mumbai",
            )
            session.add(depot)

        vehicle_profiles = [
            {
                "id": "veh-bike-1",
                "name": "Bike Courier 1",
                "category": VehicleCategory.TWO_WHEELER,
                "capacity_kg": 35,
                "capacity_volume_m3": 0.25,
                "average_speed_kmh": 24,
                "max_shift_minutes": 420,
                "cost_per_km": 0.45,
                "labor_cost_per_hour": 10,
                "emissions_kg_per_km": 0.05,
                "energy_type": VehicleEnergyType.PETROL,
                "fuel_consumption_per_km": 0.03,
                "energy_unit_cost": 106.0,
                "max_continuous_drive_min": 120.0,
                "required_break_min": 15.0,
                "cargo_length_m": 0.6,
                "cargo_width_m": 0.45,
                "cargo_height_m": 0.45,
            },
            {
                "id": "veh-tempo-1",
                "name": "Mini Tempo 1",
                "category": VehicleCategory.MINI_TEMPO,
                "capacity_kg": 450,
                "capacity_volume_m3": 4.5,
                "average_speed_kmh": 28,
                "max_shift_minutes": 540,
                "cost_per_km": 0.95,
                "labor_cost_per_hour": 12,
                "emissions_kg_per_km": 0.12,
                "energy_type": VehicleEnergyType.DIESEL,
                "fuel_consumption_per_km": 0.09,
                "energy_unit_cost": 97.0,
                "max_continuous_drive_min": 180.0,
                "required_break_min": 20.0,
                "cargo_length_m": 1.8,
                "cargo_width_m": 1.4,
                "cargo_height_m": 1.4,
            },
            {
                "id": "veh-pickup-1",
                "name": "Pickup Truck 1",
                "category": VehicleCategory.PICKUP_TRUCK,
                "capacity_kg": 900,
                "capacity_volume_m3": 8,
                "average_speed_kmh": 32,
                "max_shift_minutes": 600,
                "cost_per_km": 1.35,
                "labor_cost_per_hour": 14,
                "emissions_kg_per_km": 0.19,
                "energy_type": VehicleEnergyType.DIESEL,
                "fuel_consumption_per_km": 0.14,
                "energy_unit_cost": 97.0,
                "max_continuous_drive_min": 210.0,
                "required_break_min": 25.0,
                "cargo_length_m": 2.4,
                "cargo_width_m": 1.6,
                "cargo_height_m": 1.5,
            },
            {
                "id": "veh-van-ev-1",
                "name": "EV Van 1",
                "category": VehicleCategory.VAN,
                "capacity_kg": 800,
                "capacity_volume_m3": 9,
                "average_speed_kmh": 30,
                "max_shift_minutes": 600,
                "cost_per_km": 0.9,
                "labor_cost_per_hour": 14,
                "emissions_kg_per_km": 0.02,
                "energy_type": VehicleEnergyType.EV,
                "fuel_consumption_per_km": 0.18,
                "energy_unit_cost": 11.0,
                "max_continuous_drive_min": 180.0,
                "required_break_min": 20.0,
                "cargo_length_m": 2.7,
                "cargo_width_m": 1.7,
                "cargo_height_m": 1.6,
            },
            {
                "id": "veh-truck-small-1",
                "name": "Small Truck 1",
                "category": VehicleCategory.SMALL_TRUCK,
                "capacity_kg": 2200,
                "capacity_volume_m3": 18,
                "average_speed_kmh": 28,
                "max_shift_minutes": 660,
                "cost_per_km": 1.8,
                "labor_cost_per_hour": 16,
                "emissions_kg_per_km": 0.31,
                "energy_type": VehicleEnergyType.DIESEL,
                "fuel_consumption_per_km": 0.22,
                "energy_unit_cost": 97.0,
                "max_continuous_drive_min": 210.0,
                "required_break_min": 30.0,
                "cargo_length_m": 4.6,
                "cargo_width_m": 2.0,
                "cargo_height_m": 2.2,
            },
            {
                "id": "veh-truck-large-1",
                "name": "Large Truck 1",
                "category": VehicleCategory.LARGE_TRUCK,
                "capacity_kg": 4800,
                "capacity_volume_m3": 34,
                "average_speed_kmh": 26,
                "max_shift_minutes": 720,
                "cost_per_km": 2.35,
                "labor_cost_per_hour": 18,
                "emissions_kg_per_km": 0.42,
                "energy_type": VehicleEnergyType.DIESEL,
                "fuel_consumption_per_km": 0.31,
                "energy_unit_cost": 97.0,
                "max_continuous_drive_min": 210.0,
                "required_break_min": 30.0,
                "cargo_length_m": 6.4,
                "cargo_width_m": 2.3,
                "cargo_height_m": 2.6,
            },
        ]
        shift_profiles = [
            ("shift-bike-1", "veh-bike-1", 480, 960),
            ("shift-tempo-1", "veh-tempo-1", 480, 1020),
            ("shift-pickup-1", "veh-pickup-1", 480, 1080),
            ("shift-van-ev-1", "veh-van-ev-1", 480, 1080),
            ("shift-truck-small-1", "veh-truck-small-1", 480, 1140),
            ("shift-truck-large-1", "veh-truck-large-1", 480, 1200),
        ]

        for profile in vehicle_profiles:
            vehicle = session.get(VehicleRecord, profile["id"])
            if vehicle is None:
                session.add(VehicleRecord(depot_id=depot.id, **profile))
            else:
                for key, value in profile.items():
                    setattr(vehicle, key, value)

        for shift_id, vehicle_id, start_minute, end_minute in shift_profiles:
            shift = session.get(ShiftRecord, shift_id)
            if shift is None:
                session.add(
                    ShiftRecord(
                        id=shift_id,
                        vehicle_id=vehicle_id,
                        start_minute=start_minute,
                        end_minute=end_minute,
                    )
                )
            else:
                shift.vehicle_id = vehicle_id
                shift.start_minute = start_minute
                shift.end_minute = end_minute
