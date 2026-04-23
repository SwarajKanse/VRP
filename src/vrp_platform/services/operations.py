"""Operational read and orchestration helpers for the UI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from vrp_platform.config import PlatformSettings
from vrp_platform.domain.entities import (
    AdminSnapshot,
    Depot,
    DispatcherSnapshot,
    DriverBreakWindow,
    DriverRouteView,
    DriverStopView,
    MapPoint,
    RouteInsightView,
    RouteMapView,
    ShipmentSnapshot,
    SolveRequest,
    TrafficIncident,
    Vehicle,
    VehicleLivePosition,
    WarehouseDockView,
    WarehouseSnapshot,
)
from vrp_platform.domain.enums import ObjectiveMode, OrderStatus, PlanStatus
from vrp_platform.integrations.travel import RouteGeometryProvider
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
    route_geometry_provider: RouteGeometryProvider

    def dispatcher_snapshot(self) -> DispatcherSnapshot:
        return self.dispatcher_snapshot_filtered()

    def warehouse_snapshot(self) -> WarehouseSnapshot:
        depots = self.catalog_repo.list_depots()
        vehicles = self.catalog_repo.list_vehicles()
        routes = self.planning_repo.list_recent_route_plans(limit=24)
        route_orders = self.order_repo.get_orders([stop.order_id for route in routes for stop in route.stops])
        issues = self.planning_repo.list_recent_issues(limit=24)
        route_board = self.planning_repo.list_route_board(limit=24)
        warehouse_plans = ManifestService().generate_warehouse_plans(routes, route_orders, vehicles)

        route_index = {route.route_id: route for route in route_board}
        dock_views: list[WarehouseDockView] = []
        for bay_index, plan in enumerate(warehouse_plans, start=1):
            board_entry = route_index.get(plan.route_id)
            priority_orders = sum(1 for instruction in plan.instructions if "Priority stop" in instruction.notes)
            readiness = "ready"
            note = "Staged for loading"
            if plan.utilization_pct > 92:
                readiness = "attention"
                note = "High utilization; verify dock balance and fragile placement"
            elif priority_orders > 0:
                readiness = "expedite"
                note = "Contains priority drops; load this bay early"
            dock_views.append(
                WarehouseDockView(
                    bay_label=f"Bay {bay_index:02d}",
                    route_id=plan.route_id,
                    vehicle_name=plan.vehicle_name,
                    vehicle_category=plan.vehicle_category,
                    departure_minute=board_entry.first_eta_minute if board_entry else None,
                    readiness=readiness,
                    utilization_pct=plan.utilization_pct,
                    stop_count=len(plan.instructions),
                    priority_orders=priority_orders,
                    note=note,
                )
            )

        return WarehouseSnapshot(
            active_routes=len(warehouse_plans),
            ready_bays=sum(1 for view in dock_views if view.readiness == "ready"),
            attention_bays=sum(1 for view in dock_views if view.readiness != "ready"),
            total_weight_kg=round(sum(plan.total_weight_kg for plan in warehouse_plans), 2),
            total_volume_m3=round(sum(plan.total_volume_m3 for plan in warehouse_plans), 2),
            dock_views=dock_views,
            route_plans=warehouse_plans,
            issues=issues,
        )

    def admin_snapshot(self) -> AdminSnapshot:
        depots = self.catalog_repo.list_depots()
        vehicles = self.catalog_repo.list_vehicles()
        shifts = self.catalog_repo.list_shifts()
        current_orders = self.order_repo.list_orders()
        routes = self.planning_repo.list_route_board(limit=40)
        route_plans = self.planning_repo.list_recent_route_plans(limit=40)
        route_orders = self.order_repo.get_orders([stop.order_id for route in route_plans for stop in route.stops])
        incidents = self.active_traffic_incidents(depots[0]) if depots else []
        map_routes = self._map_routes(route_plans, route_orders, vehicles, depots, incidents) if depots else []
        recent_runs = self.planning_repo.recent_runs(limit=20)
        issues = self._live_issues(self.planning_repo.list_recent_issues(limit=40), routes, current_orders)
        audits = self.event_repo.list_audit_logs(limit=40)
        return AdminSnapshot(
            total_routes=len(routes),
            dispatched_routes=sum(1 for route in routes if route.status == PlanStatus.DISPATCHED),
            optimization_runs=len(recent_runs),
            open_issues=len(issues),
            fallback_runs=self.event_repo.count_audit_logs("solve_plan_fallback"),
            total_distance_km=round(sum(route.total_distance_km for route in routes), 2),
            total_energy_cost=round(sum(route.total_energy_cost for route in routes), 2),
            total_emissions_kg=round(sum(route.total_emissions_kg for route in routes), 2),
            routes=routes,
            recent_runs=recent_runs,
            issues=issues,
            audits=audits,
            route_insights=self._build_route_insights(routes, route_plans, route_orders, vehicles, shifts, map_routes, issues),
        )

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
        shifts = self.catalog_repo.list_shifts()
        current_orders = self.order_repo.list_orders()
        routes = self.planning_repo.list_recent_route_plans()
        all_route_order_ids = [stop.order_id for route in routes for stop in route.stops]
        route_orders = self.order_repo.get_orders(all_route_order_ids)
        incidents = self.active_traffic_incidents(depots[0]) if depots else []
        map_routes = self._map_routes(routes, route_orders, vehicles, depots, incidents)
        warehouse_plans = ManifestService().generate_warehouse_plans(routes, route_orders, vehicles)
        route_board = self.planning_repo.list_route_board()
        recent_runs = self.planning_repo.recent_runs()
        issues = self._live_issues(self.planning_repo.list_recent_issues(), route_board, current_orders)
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
            routes=route_board,
            recent_runs=recent_runs,
            issues=issues,
            map_routes=map_routes,
            fleet_positions=[route.live_position for route in map_routes if route.live_position is not None],
            traffic_incidents=incidents,
            warehouse_plans=warehouse_plans,
            route_insights=self._build_route_insights(route_board, routes, route_orders, vehicles, shifts, map_routes, issues),
        )

    def _live_issues(self, issues, route_board, current_orders: list[Order]):
        live_run_ids = {route.run_id for route in route_board}
        live_order_ids = {order.id for order in current_orders}
        filtered = [
            issue
            for issue in issues
            if issue.run_id in live_run_ids or (issue.order_id is not None and issue.order_id in live_order_ids)
        ]
        return filtered if filtered else issues[:8]

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
        stop_points: list[MapPoint] = []
        navigation_url = ""
        if route is not None and depots:
            order_lookup = {item.id: item for item in self.order_repo.get_orders([step.order_id for step in route.stops])}
            depot_lookup = {item.id: item for item in depots}
            route_depot = depot_lookup.get(route.depot_id, depots[0])
            route_map = self._route_map(route, order_lookup, {item.id: item for item in vehicles}, route_depot, [])
            path_points = route_map.path_points
            stop_points = route_map.stop_points
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
            stop_points=stop_points if route else [],
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
        depot_lookup = {depot.id: depot for depot in depots}
        route_depot = depot_lookup.get(route.depot_id) if depots else None
        if vehicle is None or route_depot is None:
            return None
        route_map = self._route_map(route, order_lookup, vehicles, route_depot, [])
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
            stop_points=route_map.stop_points,
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
        if not depots or not vehicles:
            return []
        order_lookup = {order.id: order for order in orders}
        vehicle_lookup = {vehicle.id: vehicle for vehicle in vehicles}
        depot_lookup = {depot.id: depot for depot in depots}
        return [
            self._route_map(
                route,
                order_lookup,
                vehicle_lookup,
                depot_lookup.get(route.depot_id, depots[0]),
                incidents,
            )
            for route in routes
            if route.vehicle_id in vehicle_lookup
        ]

    def _build_route_insights(
        self,
        route_board,
        route_plans,
        route_orders,
        vehicles: list[Vehicle],
        shifts,
        map_routes: list[RouteMapView],
        issues,
    ) -> list[RouteInsightView]:
        vehicle_lookup = {vehicle.id: vehicle for vehicle in vehicles}
        shift_lookup = {shift.vehicle_id: shift for shift in shifts}
        route_lookup = {route.route_id: route for route in route_plans}
        map_lookup = {route.route_id: route for route in map_routes}
        order_lookup = {order.id: order for order in route_orders}
        issue_lookup: dict[str, int] = {}
        for route in route_plans:
            order_ids = {stop.order_id for stop in route.stops}
            issue_lookup[route.route_id] = sum(1 for issue in issues if issue.order_id in order_ids)

        insights: list[RouteInsightView] = []
        for route in route_board:
            vehicle = vehicle_lookup.get(route.vehicle_id)
            route_plan = route_lookup.get(route.route_id)
            if vehicle is None or route_plan is None:
                continue
            plan_orders = [order_lookup[stop.order_id] for stop in route_plan.stops if stop.order_id in order_lookup]
            total_weight = sum(order.demand_kg for order in plan_orders)
            total_volume = sum(order.volume_m3 for order in plan_orders)
            utilization_pct = round(
                max(
                    (total_weight / max(vehicle.capacity_kg, 1.0)) * 100.0,
                    (total_volume / max(vehicle.capacity_volume_m3, 1.0)) * 100.0,
                ),
                1,
            )
            shift = shift_lookup.get(vehicle.id)
            route_limit = (
                max(shift.end_minute - shift.start_minute, 1.0)
                if shift is not None
                else max(vehicle.max_shift_minutes, 1.0)
            )
            duty_used = route.total_drive_min + route_plan.total_service_min + route.total_break_min
            duty_cycle_pct = round((duty_used / route_limit) * 100.0, 1)
            priority_orders = sum(1 for order in plan_orders if order.priority <= 1)
            issue_count = issue_lookup.get(route.route_id, 0)
            traffic_delay = map_lookup.get(route.route_id).traffic_delay_min if route.route_id in map_lookup else 0.0
            eta_confidence_pct = round(
                max(
                    52.0,
                    min(
                        97.0,
                        95.0
                        - traffic_delay * 1.2
                        - max(0.0, utilization_pct - 78.0) * 0.35
                        - max(0.0, duty_cycle_pct - 76.0) * 0.4
                        - priority_orders * 2.5
                        - issue_count * 4.5,
                    ),
                ),
                1,
            )
            risk_score = round(
                min(
                    99.0,
                    max(0.0, utilization_pct - 72.0) * 0.8
                    + max(0.0, duty_cycle_pct - 70.0) * 0.7
                    + traffic_delay * 1.1
                    + priority_orders * 4.5
                    + issue_count * 8.0
                    + (8.0 if route.driver_id is None else 0.0),
                ),
                1,
            )
            if risk_score >= 58.0:
                risk_level = "critical"
            elif risk_score >= 36.0:
                risk_level = "watch"
            else:
                risk_level = "stable"

            headline = "Release ready with good operational slack."
            suggested_action = "Keep route as planned."
            if issue_count > 0:
                headline = "Open route issues are reducing execution certainty."
                suggested_action = "Resolve exceptions before releasing the truck."
            elif utilization_pct >= 92.0:
                headline = "Truck is close to hard capacity or cube saturation."
                suggested_action = "Rebalance dense freight or verify the fill sequence."
            elif duty_cycle_pct >= 90.0:
                headline = "Route is close to the driver duty envelope."
                suggested_action = "Shift one stop or extend the shift before dispatch."
            elif traffic_delay >= 18.0:
                headline = "Traffic exposure is materially degrading ETA confidence."
                suggested_action = "Consider incident-aware resequencing or delayed release."
            elif route.driver_id is None:
                headline = "The route is planned but still missing a driver."
                suggested_action = "Assign a driver and confirm readiness."

            insights.append(
                RouteInsightView(
                    route_id=route.route_id,
                    vehicle_name=route.vehicle_name,
                    vehicle_category=route.vehicle_category,
                    depot_id=route.depot_id,
                    driver_id=route.driver_id,
                    status=route.status,
                    stop_count=route.stop_count,
                    total_distance_km=route.total_distance_km,
                    total_cost=route.total_cost,
                    total_energy_cost=route.total_energy_cost,
                    fuel_used=route.fuel_used,
                    traffic_delay_min=round(traffic_delay, 1),
                    utilization_pct=utilization_pct,
                    duty_cycle_pct=round(duty_cycle_pct, 1),
                    eta_confidence_pct=eta_confidence_pct,
                    priority_orders=priority_orders,
                    issue_count=issue_count,
                    risk_score=risk_score,
                    risk_level=risk_level,
                    headline=headline,
                    suggested_action=suggested_action,
                )
            )
        return sorted(insights, key=lambda item: (-item.risk_score, -item.utilization_pct, item.route_id))

    def _route_map(
        self,
        route,
        order_lookup,
        vehicle_lookup: dict[str, Vehicle],
        depot: Depot,
        incidents: list[TrafficIncident],
    ) -> RouteMapView:
        vehicle = vehicle_lookup[route.vehicle_id]
        stop_points = [MapPoint(depot.latitude, depot.longitude, depot.name, "depot")]
        for stop in route.stops:
            order = order_lookup.get(stop.order_id)
            if order is None:
                continue
            stop_points.append(
                MapPoint(
                    latitude=order.latitude,
                    longitude=order.longitude,
                    label=f"{stop.sequence}. {order.external_ref}",
                    kind="stop",
                )
            )
        stop_points.append(MapPoint(depot.latitude, depot.longitude, f"{depot.name} return", "depot"))
        path_points = self._geometry_points(stop_points)
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
            stop_points=stop_points,
            live_position=live_position,
            traffic_delay_min=max(0.0, traffic_delay),
            navigation_url=self._navigation_url(stop_points),
        )

    def _geometry_points(self, stop_points: list[MapPoint]) -> list[MapPoint]:
        waypoints = [(point.latitude, point.longitude) for point in stop_points]
        result = self.route_geometry_provider.build(waypoints)
        points = result.points or waypoints
        return [
            MapPoint(
                latitude=latitude,
                longitude=longitude,
                label=f"road-{index}",
                kind="geometry",
            )
            for index, (latitude, longitude) in enumerate(points, start=1)
        ]

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
