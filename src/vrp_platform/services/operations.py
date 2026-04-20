"""Operational read and orchestration helpers for the UI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from vrp_platform.config import PlatformSettings
from vrp_platform.domain.entities import (
    Depot,
    DispatcherSnapshot,
    DriverBreakWindow,
    DriverRouteView,
    DriverStopView,
    MapPoint,
    RouteMapView,
    ShipmentSnapshot,
    SolveRequest,
    TrafficIncident,
    Vehicle,
    VehicleLivePosition,
)
from vrp_platform.domain.enums import ObjectiveMode, OrderStatus
from vrp_platform.repos.catalog import CatalogRepository
from vrp_platform.repos.events import EventRepository
from vrp_platform.repos.orders import OrderRepository
from vrp_platform.repos.planning import PlanningRepository
from vrp_platform.services.manifests import ManifestService


@dataclass(slots=True)
class OperationsService:
    """Read models and solve-request builders used by UI and workers."""

    settings: PlatformSettings
    catalog_repo: CatalogRepository
    order_repo: OrderRepository
    planning_repo: PlanningRepository
    event_repo: EventRepository

    def dispatcher_snapshot(self) -> DispatcherSnapshot:
        return self.dispatcher_snapshot_filtered()

    def dispatcher_snapshot_filtered(
        self,
        search_term: str = "",
        statuses: list[OrderStatus] | None = None,
        sort_by: str = "external_ref",
        descending: bool = False,
        page: int = 1,
        page_size: int = 25,
    ) -> DispatcherSnapshot:
        depots = self.catalog_repo.list_depots()
        vehicles = self.catalog_repo.list_vehicles()
        routes = self.planning_repo.list_recent_route_plans()
        all_route_order_ids = [stop.order_id for route in routes for stop in route.stops]
        route_orders = self.order_repo.get_orders(all_route_order_ids)
        incidents = self.active_traffic_incidents(depots[0]) if depots else []
        map_routes = self._map_routes(routes, route_orders, vehicles, depots, incidents)
        warehouse_plans = ManifestService().generate_warehouse_plans(routes, route_orders, vehicles)
        safe_page = max(page, 1)
        safe_page_size = max(page_size, 1)
        offset = (safe_page - 1) * safe_page_size
        filtered_orders = self.order_repo.list_orders(
            statuses=statuses,
            search_term=search_term,
            sort_by=sort_by,
            descending=descending,
            limit=safe_page_size,
            offset=offset,
        )
        return DispatcherSnapshot(
            orders=filtered_orders,
            total_order_count=self.order_repo.count_orders(),
            filtered_order_count=self.order_repo.count_orders(statuses=statuses, search_term=search_term),
            pending_order_count=self.order_repo.count_orders(statuses=[OrderStatus.PENDING]),
            order_page=safe_page,
            order_page_size=safe_page_size,
            routes=self.planning_repo.list_route_board(),
            recent_runs=self.planning_repo.recent_runs(),
            issues=self.planning_repo.list_recent_issues(),
            map_routes=map_routes,
            fleet_positions=[route.live_position for route in map_routes if route.live_position is not None],
            traffic_incidents=incidents,
            warehouse_plans=warehouse_plans,
        )

    def build_solve_request(
        self,
        objective: ObjectiveMode,
        order_ids: list[str] | None = None,
    ) -> SolveRequest:
        depots = self.catalog_repo.list_depots()
        vehicles = self.catalog_repo.list_vehicles()
        shifts = self.catalog_repo.list_shifts()
        if order_ids:
            orders = self.order_repo.get_orders(order_ids)
        else:
            orders = self.order_repo.list_orders(
                statuses=[
                    OrderStatus.PENDING,
                    OrderStatus.PLANNED,
                    OrderStatus.FAILED,
                ]
            )

        if not depots:
            raise ValueError("No depots are configured")
        if not vehicles:
            raise ValueError("No vehicles are configured")
        if not orders:
            raise ValueError("No active orders are available to plan")

        return SolveRequest(
            depots=depots,
            vehicles=vehicles,
            orders=orders,
            shifts=shifts,
            objective=objective,
            traffic_incidents=self.active_traffic_incidents(depots[0]),
        )

    def find_shipment(self, external_ref: str) -> ShipmentSnapshot | None:
        order = self.order_repo.get_order_by_external_ref(external_ref.strip())
        if order is None:
            return None
        depots = self.catalog_repo.list_depots()
        vehicles = self.catalog_repo.list_vehicles()
        route = self.planning_repo.get_route_by_order(order.id)
        stop = None
        path_points: list[MapPoint] = []
        navigation_url = ""
        if route is not None and depots:
            order_lookup = {item.id: item for item in self.order_repo.get_orders([step.order_id for step in route.stops])}
            route_map = self._route_map(route, order_lookup, {item.id: item for item in vehicles}, depots[0], [])
            path_points = route_map.path_points
            navigation_url = route_map.navigation_url
            stop = next((item for item in route.stops if item.order_id == order.id), None)
        return ShipmentSnapshot(
            order=order,
            route_id=route.route_id if route else None,
            vehicle_id=route.vehicle_id if route else None,
            route_status=route.status if route else None,
            stop_sequence=stop.sequence if stop else None,
            eta_minute=stop.arrival_minute if stop else None,
            path_points=path_points,
            navigation_url=navigation_url,
            customer_events=self.event_repo.list_customer_events(order.id),
            delivery_events=self.event_repo.list_delivery_events(order.id),
        )

    def driver_route(self, driver_id: str) -> DriverRouteView | None:
        route = self.planning_repo.get_active_route_for_driver(driver_id)
        if route is None:
            return None
        depots = self.catalog_repo.list_depots()
        vehicles = {vehicle.id: vehicle for vehicle in self.catalog_repo.list_vehicles()}
        order_lookup = {
            order.id: order for order in self.order_repo.get_orders([stop.order_id for stop in route.stops])
        }
        vehicle = vehicles.get(route.vehicle_id)
        if vehicle is None or not depots:
            return None
        route_map = self._route_map(route, order_lookup, vehicles, depots[0], [])
        return DriverRouteView(
            route_id=route.route_id,
            vehicle_id=route.vehicle_id,
            vehicle_name=vehicle.name,
            vehicle_category=vehicle.category,
            driver_id=driver_id,
            status=route.status,
            total_distance_km=route.total_distance_km,
            total_drive_min=route.total_drive_min,
            total_energy_cost=route.total_energy_cost,
            fuel_used=route.fuel_used,
            total_break_min=route.total_break_min,
            break_windows=self._driver_break_windows(route, vehicle),
            path_points=route_map.path_points,
            navigation_url=route_map.navigation_url,
            stops=[
                DriverStopView(
                    stop_id=stop.stop_id,
                    order_id=stop.order_id,
                    external_ref=order_lookup[stop.order_id].external_ref,
                    customer_name=order_lookup[stop.order_id].customer_name,
                    sequence=stop.sequence,
                    eta_minute=stop.arrival_minute,
                    address=order_lookup[stop.order_id].address,
                    latitude=order_lookup[stop.order_id].latitude,
                    longitude=order_lookup[stop.order_id].longitude,
                    status=order_lookup[stop.order_id].status,
                )
                for stop in route.stops
                if stop.order_id in order_lookup
            ],
        )

    def active_traffic_incidents(self, depot: Depot) -> list[TrafficIncident]:
        if not self.settings.demo_live_traffic:
            return []
        return [
            TrafficIncident(
                incident_id="incident-sion",
                name="Sion junction bottleneck",
                latitude=depot.latitude + 0.022,
                longitude=depot.longitude + 0.038,
                radius_km=self.settings.default_incident_radius_km,
                delay_multiplier=1.32,
                severity="high",
                description="Heavy traffic buildup and restricted lane movement.",
            ),
            TrafficIncident(
                incident_id="incident-andheri",
                name="Andheri flyover blockage",
                latitude=depot.latitude + 0.038,
                longitude=depot.longitude - 0.011,
                radius_km=self.settings.default_incident_radius_km,
                delay_multiplier=1.24,
                severity="medium",
                description="Accident clearance reducing throughput on the corridor.",
            ),
        ]

    def _map_routes(
        self,
        routes,
        orders,
        vehicles: list[Vehicle],
        depots: list[Depot],
        incidents: list[TrafficIncident],
    ) -> list[RouteMapView]:
        order_lookup = {order.id: order for order in orders}
        vehicle_lookup = {vehicle.id: vehicle for vehicle in vehicles}
        depot = depots[0]
        return [
            self._route_map(route, order_lookup, vehicle_lookup, depot, incidents)
            for route in routes
            if route.vehicle_id in vehicle_lookup
        ]

    def _route_map(
        self,
        route,
        order_lookup,
        vehicle_lookup: dict[str, Vehicle],
        depot: Depot,
        incidents: list[TrafficIncident],
    ) -> RouteMapView:
        vehicle = vehicle_lookup[route.vehicle_id]
        path_points = [MapPoint(depot.latitude, depot.longitude, depot.name, "depot")]
        for stop in route.stops:
            order = order_lookup.get(stop.order_id)
            if order is None:
                continue
            path_points.append(
                MapPoint(
                    latitude=order.latitude,
                    longitude=order.longitude,
                    label=f"{stop.sequence}. {order.external_ref}",
                    kind="stop",
                )
            )
        path_points.append(MapPoint(depot.latitude, depot.longitude, f"{depot.name} return", "depot"))
        live_position = self._live_position(route, vehicle, order_lookup, depot)
        traffic_delay = route.total_drive_min - (route.total_distance_km / max(vehicle.average_speed_kmh, 1.0) * 60.0)
        return RouteMapView(
            route_id=route.route_id,
            vehicle_id=route.vehicle_id,
            vehicle_name=vehicle.name,
            vehicle_category=vehicle.category,
            driver_id=None,
            status=route.status,
            path_points=path_points,
            live_position=live_position,
            traffic_delay_min=max(0.0, traffic_delay),
            navigation_url=self._navigation_url(path_points),
        )

    def _live_position(
        self,
        route,
        vehicle: Vehicle,
        order_lookup,
        depot: Depot,
    ) -> VehicleLivePosition | None:
        now_minute = self._current_minute()
        if not route.stops:
            return None
        if route.status.value != "dispatched" or now_minute <= route.stops[0].arrival_minute:
            first_order = order_lookup.get(route.stops[0].order_id)
            return VehicleLivePosition(
                route_id=route.route_id,
                vehicle_id=vehicle.id,
                vehicle_name=vehicle.name,
                vehicle_category=vehicle.category,
                driver_id=vehicle.assigned_driver_id,
                latitude=depot.latitude,
                longitude=depot.longitude,
                status="awaiting_dispatch" if route.status.value != "dispatched" else "departing",
                next_stop_label=first_order.external_ref if first_order else route.stops[0].order_id,
                eta_minute=route.stops[0].arrival_minute,
            )

        previous_point = (depot.latitude, depot.longitude)
        previous_departure = route.stops[0].arrival_minute - route.stops[0].travel_time_from_previous_min
        for stop in route.stops:
            order = order_lookup.get(stop.order_id)
            if order is None:
                continue
            target = (order.latitude, order.longitude)
            if stop.arrival_minute <= now_minute <= stop.departure_minute:
                return VehicleLivePosition(
                    route_id=route.route_id,
                    vehicle_id=vehicle.id,
                    vehicle_name=vehicle.name,
                    vehicle_category=vehicle.category,
                    driver_id=vehicle.assigned_driver_id,
                    latitude=target[0],
                    longitude=target[1],
                    status="at_stop",
                    next_stop_label=order.external_ref,
                    eta_minute=stop.arrival_minute,
                )
            if previous_departure <= now_minute < stop.arrival_minute:
                progress = (now_minute - previous_departure) / max(stop.arrival_minute - previous_departure, 1.0)
                latitude = previous_point[0] + (target[0] - previous_point[0]) * progress
                longitude = previous_point[1] + (target[1] - previous_point[1]) * progress
                return VehicleLivePosition(
                    route_id=route.route_id,
                    vehicle_id=vehicle.id,
                    vehicle_name=vehicle.name,
                    vehicle_category=vehicle.category,
                    driver_id=vehicle.assigned_driver_id,
                    latitude=latitude,
                    longitude=longitude,
                    status="en_route",
                    next_stop_label=order.external_ref,
                    eta_minute=stop.arrival_minute,
                )
            previous_point = target
            previous_departure = stop.departure_minute

        last_stop = route.stops[-1]
        last_order = order_lookup.get(last_stop.order_id)
        if last_order is None:
            return None
        return VehicleLivePosition(
            route_id=route.route_id,
            vehicle_id=vehicle.id,
            vehicle_name=vehicle.name,
            vehicle_category=vehicle.category,
            driver_id=vehicle.assigned_driver_id,
            latitude=last_order.latitude,
            longitude=last_order.longitude,
            status="route_complete",
            next_stop_label="Return to depot",
            eta_minute=None,
        )

    def _driver_break_windows(self, route, vehicle: Vehicle) -> list[DriverBreakWindow]:
        if vehicle.max_continuous_drive_min <= 0 or vehicle.required_break_min <= 0:
            return []
        windows: list[DriverBreakWindow] = []
        continuous_drive = 0.0
        for leg in route.legs:
            projected = continuous_drive + leg.travel_time_min
            break_count = int(max(0.0, (projected - 1e-6) // vehicle.max_continuous_drive_min))
            if break_count > 0:
                for break_index in range(break_count):
                    windows.append(
                        DriverBreakWindow(
                            start_minute=max(0.0, leg.eta_minute - leg.travel_time_min + (break_index + 1) * vehicle.max_continuous_drive_min),
                            duration_min=vehicle.required_break_min,
                            reason="Regulatory driving break",
                        )
                    )
            continuous_drive = 0.0
        return windows

    def _navigation_url(self, path_points: list[MapPoint]) -> str:
        if len(path_points) < 2:
            return ""
        points = "/".join(f"{point.latitude},{point.longitude}" for point in path_points[:-1])
        return f"https://www.google.com/maps/dir/{points}"

    def _current_minute(self) -> float:
        now = datetime.now(ZoneInfo(self.settings.timezone))
        return float(now.hour * 60 + now.minute)
