"""NiceGUI entrypoint for the VRP platform."""

from __future__ import annotations

import asyncio
from contextlib import contextmanager
from datetime import datetime

from nicegui import app, ui

from vrp_platform.bootstrap import bootstrap_platform
from vrp_platform.domain.entities import (
    AdminSnapshot,
    DeliveryEvent,
    DispatcherSnapshot,
    DriverRouteView,
    MapPoint,
    ShipmentSnapshot,
    VehicleLivePosition,
    WarehouseSnapshot,
)
from vrp_platform.domain.enums import DeliveryEventType, ObjectiveMode, OrderStatus, Role
from vrp_platform.integrations.travel import HybridTravelMatrixProvider
from vrp_platform.optimizer.engine import RouteOptimizer
from vrp_platform.services.auth import UserContext
from vrp_platform.ui.theme import apply_theme

platform = bootstrap_platform()

SAMPLE_MANIFEST = """order_id,customer_name,lat,lon,weight_kg,length_m,width_m,height_m,service_time_min,window_start_min,window_end_min,address,priority,fragile,orientation_locked
SO-1001,Bandra Boutique,19.0596,72.8295,150,1.10,0.80,0.50,15,540,660,Hill Road Bandra,2,false,false
SO-1002,Andheri Medical,19.1136,72.8697,220,1.20,0.80,0.60,20,570,720,Veera Desai Road Andheri,2,true,false
SO-1003,Powai Electronics,19.1176,72.9060,310,1.40,0.80,0.70,25,600,780,Hiranandani Powai,1,false,true
SO-1004,Lower Parel Studio,19.0038,72.8295,180,1.00,0.75,0.55,15,555,705,Senapati Bapat Marg,2,false,false
SO-1005,Colaba Documents,18.9067,72.8147,18,0.40,0.25,0.20,8,510,620,Colaba Causeway,3,false,false
SO-1006,Bhiwandi Bulk Hub,19.2813,73.0483,1800,2.80,1.80,1.80,30,660,900,Bhiwandi Warehouse Park,1,false,true
"""

ROUTE_COLORS = ["#ff7a00", "#145da0", "#1e8e5a", "#9a3412", "#5b21b6", "#0f766e"]
ALL_ROLES = {Role.ADMIN, Role.DISPATCHER, Role.CUSTOMER, Role.DRIVER}
DISPATCHER_ROLES = {Role.ADMIN, Role.DISPATCHER}
WAREHOUSE_ROLES = {Role.ADMIN, Role.DISPATCHER}
ADMIN_ROLES = {Role.ADMIN, Role.DISPATCHER}
CUSTOMER_ROLES = {Role.ADMIN, Role.DISPATCHER, Role.CUSTOMER}
DRIVER_ROLES = {Role.ADMIN, Role.DISPATCHER, Role.DRIVER}

apply_theme()


def _minutes_label(value: float | None) -> str:
    if value is None:
        return "-"
    total = int(round(value))
    return f"{total // 60:02d}:{total % 60:02d}"


def _current_user() -> UserContext | None:
    username = app.storage.user.get("username")
    role_value = app.storage.user.get("role")
    if not username or not role_value:
        return None
    try:
        return UserContext(username=username, role=Role(role_value))
    except ValueError:
        app.storage.user.clear()
        return None


def _store_user(user: UserContext) -> None:
    app.storage.user["username"] = user.username
    app.storage.user["role"] = user.role.value


def _default_route_for(role: Role) -> str:
    if role == Role.ADMIN:
        return "/admin"
    if role == Role.DISPATCHER:
        return "/dispatcher"
    if role == Role.CUSTOMER:
        return "/customer"
    if role == Role.DRIVER:
        return "/driver"
    return "/dispatcher"


def _logout() -> None:
    app.storage.user.clear()
    ui.navigate.to("/login")


def _require_roles(allowed: set[Role]) -> UserContext | None:
    user = _current_user()
    if user is None:
        ui.navigate.to("/login")
        return None
    try:
        platform.auth_service.require_role(user, allowed)
    except PermissionError:
        ui.notify("Access denied for the current role.", color="negative")
        ui.navigate.to(_default_route_for(user.role))
        return None
    return user


def _render_session_bar(user: UserContext) -> None:
    with ui.row().classes("w-full items-center justify-between pb-2"):
        with ui.row().classes("gap-2"):
            if user.role in DISPATCHER_ROLES:
                ui.button("Dispatcher", on_click=lambda: ui.navigate.to("/dispatcher")).props("flat")
            if user.role in WAREHOUSE_ROLES:
                ui.button("Warehouse", on_click=lambda: ui.navigate.to("/warehouse")).props("flat")
            if user.role in ADMIN_ROLES:
                ui.button("Admin", on_click=lambda: ui.navigate.to("/admin")).props("flat")
            if user.role in CUSTOMER_ROLES:
                ui.button("Customer", on_click=lambda: ui.navigate.to("/customer")).props("flat")
            if user.role in DRIVER_ROLES:
                ui.button("Driver", on_click=lambda: ui.navigate.to("/driver")).props("flat")
        with ui.row().classes("items-center gap-3"):
            ui.label(f"{user.username} · {user.role.value.replace('_', ' ').title()}").classes("vrp-pill")
            ui.button("Logout", on_click=_logout).props("flat")


def _nav_sections_for(user: UserContext) -> list[tuple[str, str, str]]:
    sections: list[tuple[str, str, str]] = []
    if user.role in DISPATCHER_ROLES:
        sections.append(("dispatcher", "Dispatcher", "/dispatcher"))
    if user.role in WAREHOUSE_ROLES:
        sections.append(("warehouse", "Warehouse", "/warehouse"))
    if user.role in ADMIN_ROLES:
        sections.append(("admin", "Admin", "/admin"))
    if user.role in CUSTOMER_ROLES:
        sections.append(("customer", "Customer", "/customer"))
    if user.role in DRIVER_ROLES:
        sections.append(("driver", "Driver", "/driver"))
    return sections


@contextmanager
def _workspace_frame(
    user: UserContext,
    active_section: str,
    eyebrow: str,
    title: str,
    subtitle: str,
):
    with ui.row().classes("vrp-shell vrp-workspace w-full gap-5"):
        with ui.column().classes("vrp-rail"):
            with ui.card().classes("vrp-rail-card p-5"):
                ui.label("VRP Mission Grid").classes("text-2xl font-bold")
                ui.label("Dispatch, load, route, deliver. One operational surface.").classes("text-sm opacity-80")
                ui.separator().classes("opacity-20 my-2")
                for section_id, label, route in _nav_sections_for(user):
                    classes = "vrp-nav-button text-white"
                    if section_id == active_section:
                        classes += " vrp-nav-active"
                    ui.button(label, on_click=lambda route=route: ui.navigate.to(route)).props("flat").classes(classes)
                ui.separator().classes("opacity-20 my-2")
                with ui.column().classes("gap-1 vrp-side-note"):
                    ui.label(f"Signed in as {user.username}").classes("text-sm font-semibold")
                    ui.label(user.role.value.replace("_", " ").title()).classes("text-xs opacity-80")
                    ui.label("Use the rail to move across workspaces without losing context.").classes("text-xs opacity-70")
            with ui.card().classes("vrp-rail-card p-5"):
                ui.label("Operator Notes").classes("text-lg font-bold")
                ui.label("Keep warehouse, dispatch, and driver state aligned. Optimize only after manifest integrity is clean.").classes("text-sm opacity-80")
                ui.label("Escalate any route with high utilization, heavy incidents, or repeated failed attempts.").classes("text-sm opacity-80")

        with ui.column().classes("vrp-stage flex-1 gap-5"):
            with ui.card().classes("vrp-panel vrp-command p-7 w-full"):
                _render_session_bar(user)
                ui.label(eyebrow).classes("vrp-overline")
                ui.label(title).classes("text-4xl font-bold")
                ui.label(subtitle).classes("text-base opacity-80 max-w-5xl")
            yield


def _render_workspace_metrics(cards: list[tuple[str, str, str]]) -> None:
    with ui.grid().classes("w-full grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4"):
        for title, value, detail in cards:
            with ui.card().classes("vrp-stat-card p-5"):
                ui.label(title).classes("text-sm font-medium vrp-subtle")
                ui.label(value).classes("vrp-kpi-value text-3xl font-bold")
                ui.label(detail).classes("text-sm vrp-subtle")


def _risk_class(level: str) -> str:
    if level == "critical":
        return "vrp-risk-critical"
    if level == "watch":
        return "vrp-risk-watch"
    return "vrp-risk-stable"


def _render_route_intelligence(title: str, insights) -> None:
    with ui.card().classes("vrp-panel p-5"):
        with ui.row().classes("w-full items-center justify-between"):
            ui.label(title).classes("vrp-panel-title text-2xl")
            ui.label("Route risk, duty pressure, utilization, ETA confidence, and next action").classes("text-sm vrp-subtle")
        if not insights:
            ui.label("No route intelligence is available yet. Create a run first.").classes("vrp-subtle mt-3")
            return
        with ui.grid().classes("w-full grid-cols-1 xl:grid-cols-2 gap-4 mt-4"):
            for insight in insights[:6]:
                with ui.card().classes("vrp-insight-card p-5"):
                    with ui.row().classes("vrp-insight-top w-full"):
                        with ui.column().classes("gap-0"):
                            ui.label(f"{insight.route_id} · {insight.vehicle_name}").classes("vrp-panel-title text-xl")
                            ui.label(
                                f"{insight.vehicle_category.value.replace('_', ' ').title()} · {insight.stop_count} stops · {insight.total_distance_km:.1f} km"
                            ).classes("text-sm vrp-subtle")
                        ui.label(insight.risk_level.title()).classes(f"vrp-pill {_risk_class(insight.risk_level)}")
                    ui.label(insight.headline).classes("text-sm mt-2")
                    with ui.grid().classes("w-full grid-cols-2 2xl:grid-cols-4 gap-3 mt-4"):
                        stats = [
                            ("Utilization", f"{insight.utilization_pct:.0f}%"),
                            ("Duty Cycle", f"{insight.duty_cycle_pct:.0f}%"),
                            ("ETA Confidence", f"{insight.eta_confidence_pct:.0f}%"),
                            ("Risk Score", f"{insight.risk_score:.0f}"),
                        ]
                        for label, value in stats:
                            with ui.column().classes("gap-0 vrp-data-chip"):
                                ui.label(label).classes("text-[0.72rem] vrp-subtle")
                                ui.label(value).classes("vrp-kpi-value text-lg font-semibold")
                    with ui.column().classes("gap-2 mt-4"):
                        for label, value in (
                            ("Load Pressure", insight.utilization_pct),
                            ("Duty Pressure", insight.duty_cycle_pct),
                            ("Traffic Drag", min(100.0, insight.traffic_delay_min * 4.0)),
                        ):
                            with ui.column().classes("gap-1"):
                                with ui.row().classes("w-full items-center justify-between"):
                                    ui.label(label).classes("text-xs vrp-subtle")
                                    ui.label(
                                        f"{insight.traffic_delay_min:.0f} min"
                                        if label == "Traffic Drag"
                                        else f"{value:.0f}%"
                                    ).classes("vrp-mono text-xs")
                                with ui.element("div").classes("vrp-meter"):
                                    ui.element("div").classes("vrp-meter-fill").style(f"width: {min(100.0, value):.1f}%")
                    with ui.row().classes("w-full items-start justify-between mt-4"):
                        with ui.row().classes("gap-2"):
                            ui.label(f"Priority {insight.priority_orders}").classes("vrp-data-chip")
                            ui.label(f"Issues {insight.issue_count}").classes("vrp-data-chip")
                            ui.label(
                                f"Fuel {insight.fuel_used:.1f} · Energy {insight.total_energy_cost:.2f}"
                            ).classes("vrp-data-chip")
                        ui.label(insight.status.value.title()).style(_status_tone(insight.status.value))
                    ui.label(insight.suggested_action).classes("text-sm mt-3 font-medium")


def _status_tone(status: str) -> str:
    if status in {OrderStatus.DELIVERED.value, "completed"}:
        return "color: var(--vrp-success);"
    if status in {OrderStatus.FAILED.value, "failed"}:
        return "color: var(--vrp-danger);"
    if status in {OrderStatus.IN_TRANSIT.value, "dispatched", "optimized"}:
        return "color: var(--vrp-accent-deep);"
    return "color: var(--vrp-ink);"


def _run_live_plan(objective: ObjectiveMode):
    request = platform.build_solve_request(objective)
    response = platform.solve_plan(request)
    platform.publish_customer_updates(response)
    return response


def _preview_plan(objective: ObjectiveMode):
    request = platform.build_solve_request(objective)
    optimizer = RouteOptimizer(HybridTravelMatrixProvider(platform.settings))
    return optimizer.solve(request)


def _map_center(points: list[MapPoint]) -> tuple[float, float]:
    if not points:
        return (19.076, 72.8777)
    return (
        sum(point.latitude for point in points) / len(points),
        sum(point.longitude for point in points) / len(points),
    )


def _map_layer(path_points: list[MapPoint], color: str, marker_points: list[MapPoint] | None = None):
    return (path_points, color, marker_points or path_points)


def _render_map(
    title: str,
    paths,
    live_positions: list[VehicleLivePosition] | None = None,
    incidents=None,
) -> None:
    live_positions = live_positions or []
    incidents = incidents or []
    all_points: list[MapPoint] = []
    normalized_paths: list[tuple[list[MapPoint], str, list[MapPoint]]] = []
    for item in paths:
        if len(item) == 2:
            path_points, color = item
            marker_points = path_points
        else:
            path_points, color, marker_points = item
        normalized_paths.append((path_points, color, marker_points))
        all_points.extend(marker_points or path_points)
    if not all_points:
        with ui.card().classes("vrp-panel p-5"):
            ui.label(title).classes("text-xl font-bold")
            ui.label("No route geometry is available yet.").classes("vrp-subtle")
        return
    with ui.card().classes("vrp-panel p-5"):
        ui.label(title).classes("text-xl font-bold")
        ui.label("Live fleet positions, stop sequence, and traffic blockers on one map.").classes("vrp-subtle")
        leaflet = ui.leaflet(center=_map_center(all_points), zoom=11).classes("w-full h-[30rem] rounded-2xl mt-3")
        leaflet.tile_layer(
            url_template="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
            options={"attribution": "&copy; OpenStreetMap contributors"},
        )
        for path_points, color, marker_points in normalized_paths:
            if len(path_points) >= 2:
                leaflet.generic_layer(
                    name="polyline",
                    args=[[(point.latitude, point.longitude) for point in path_points], {"color": color, "weight": 5, "opacity": 0.9}],
                )
            for point in marker_points:
                leaflet.marker(latlng=(point.latitude, point.longitude), options={"title": point.label})
        for vehicle in live_positions:
            leaflet.marker(
                latlng=(vehicle.latitude, vehicle.longitude),
                options={"title": f"{vehicle.vehicle_name} · {vehicle.status} · {vehicle.next_stop_label}"},
            )
        for incident in incidents:
            leaflet.marker(
                latlng=(incident.latitude, incident.longitude),
                options={"title": f"{incident.name} · {incident.description}"},
            )


def _render_dispatcher_metrics(snapshot: DispatcherSnapshot) -> None:
    live_routes = len(snapshot.routes)
    open_issues = len(snapshot.issues)
    metrics = [
        ("Orders In Scope", str(snapshot.total_order_count), "Persisted operational demand"),
        ("Orders Pending", str(snapshot.pending_order_count), "Demand not yet protected by a route"),
        ("Orders In View", str(snapshot.filtered_order_count), "Filtered dispatcher workbench result"),
        ("Vehicles Live", str(len(snapshot.fleet_positions)), "Estimated active vehicle positions"),
        ("Traffic Blocks", str(len(snapshot.traffic_incidents)), "Incident-aware delay zones"),
        ("Warehouse Plans", str(len(snapshot.warehouse_plans)), "Truck-specific loading instructions"),
        ("Open Issues", str(open_issues), "Unassigned orders and warnings"),
    ]
    with ui.grid().classes("w-full grid-cols-1 md:grid-cols-2 xl:grid-cols-7 gap-4"):
        for title, value, detail in metrics:
            with ui.card().classes("vrp-panel p-5"):
                ui.label(title).classes("text-sm font-medium vrp-subtle")
                ui.label(value).classes("vrp-kpi-value text-3xl font-bold")
                ui.label(detail).classes("text-sm vrp-subtle")


def _render_feedback_panel(lines: list[str], tone: str) -> None:
    if not lines:
        return
    tone_map = {
        "positive": "var(--vrp-success)",
        "warning": "var(--vrp-warn)",
        "negative": "var(--vrp-danger)",
        "info": "var(--vrp-accent-deep)",
    }
    with ui.card().classes("vrp-panel p-5"):
        ui.label("Operational Feedback").classes("text-xl font-bold")
        for line in lines[:8]:
            ui.label(line).style(f"color: {tone_map.get(tone, 'var(--vrp-ink)')};")


def _render_order_workbench(
    snapshot: DispatcherSnapshot,
    selected_order_ids: set[str],
    toggle_selection,
    select_page,
    clear_selection,
    previous_page,
    next_page,
) -> None:
    total_pages = max(1, (max(snapshot.filtered_order_count, 1) + snapshot.order_page_size - 1) // snapshot.order_page_size)
    with ui.card().classes("vrp-panel p-5"):
        with ui.row().classes("w-full items-center justify-between"):
            ui.label("Order Workbench").classes("text-xl font-bold")
            ui.label(
                f"{snapshot.filtered_order_count} matched · page {snapshot.order_page}/{total_pages}"
            ).classes("vrp-pill")
        with ui.row().classes("w-full items-center justify-between mt-3"):
            ui.label(
                f"{len(selected_order_ids)} selected for targeted planning or manual action."
            ).classes("text-sm vrp-subtle")
            with ui.row().classes("gap-2"):
                ui.button("Select Page", on_click=select_page).props("flat color=primary")
                ui.button("Clear Selection", on_click=clear_selection).props("flat")
        if not snapshot.orders:
            ui.label("No orders match the current filters.").classes("vrp-subtle mt-4")
            return
        for order in snapshot.orders:
            with ui.row().classes("w-full items-center justify-between py-2 border-b border-[rgba(17,36,58,0.08)]"):
                with ui.row().classes("items-start gap-3"):
                    ui.checkbox(
                        value=order.id in selected_order_ids,
                        on_change=lambda event, order_id=order.id: toggle_selection(order_id, bool(event.value)),
                    )
                    with ui.column().classes("gap-0"):
                        ui.label(f"{order.external_ref} · {order.customer_name}").classes("font-semibold")
                        ui.label(
                            f"{order.demand_kg:.0f} kg · {order.package_dimensions_m[0]:.2f} x {order.package_dimensions_m[1]:.2f} x {order.package_dimensions_m[2]:.2f} m"
                        ).classes("text-sm vrp-subtle")
                        ui.label(
                            f"TW {_minutes_label(order.time_window_start_min)}-{_minutes_label(order.time_window_end_min)} · Priority {order.priority}"
                        ).classes("text-sm vrp-subtle")
                        if order.address:
                            ui.label(order.address).classes("text-xs vrp-subtle")
                ui.label(order.status.value.replace("_", " ").title()).style(_status_tone(order.status.value))
        with ui.row().classes("w-full items-center justify-between mt-4"):
            ui.label(
                f"Showing {len(snapshot.orders)} of {snapshot.filtered_order_count} matching orders"
            ).classes("text-sm vrp-subtle")
            with ui.row().classes("gap-2"):
                ui.button("Previous", on_click=previous_page).props("flat")
                ui.button("Next", on_click=next_page).props("flat")


def _render_route_board(snapshot: DispatcherSnapshot, refresh_callback) -> None:
    with ui.card().classes("vrp-panel p-5"):
        with ui.row().classes("w-full items-center justify-between"):
            ui.label("Route Board").classes("text-xl font-bold")
            ui.label("Vehicle class, fuel burn, break load, and dispatch status").classes("text-sm vrp-subtle")
        if not snapshot.routes:
            ui.label("No routes yet. Run an optimization from the planning controls.").classes("vrp-subtle")
            return
        for route in snapshot.routes[:10]:
            with ui.card().classes("w-full bg-white/80 border border-[rgba(17,36,58,0.08)] shadow-none"):
                with ui.row().classes("w-full items-start justify-between"):
                    with ui.column().classes("gap-0"):
                        ui.label(f"{route.route_id} · {route.vehicle_name}").classes("font-semibold")
                        ui.label(
                            f"{route.vehicle_category.value.replace('_', ' ').title()} · {route.stop_count} stops · ETA {_minutes_label(route.first_eta_minute)}"
                        ).classes("text-sm vrp-subtle")
                        ui.label(
                            f"Distance {route.total_distance_km:.1f} km · Cost {route.total_cost:.2f} · Fuel {route.fuel_used:.1f} units · Energy {route.total_energy_cost:.2f}"
                        ).classes("text-sm vrp-subtle")
                        ui.label(
                            f"Drive {route.total_drive_min:.0f} min · Breaks {route.total_break_min:.0f} min · Emissions {route.total_emissions_kg:.2f} kg"
                        ).classes("text-sm vrp-subtle")
                    with ui.column().classes("items-end gap-2"):
                        ui.label(route.status.value.title()).style(_status_tone(route.status.value))
                        ui.label(route.driver_id or "Unassigned").classes("vrp-pill")
                        if route.driver_id != platform.settings.driver_demo_id:
                            ui.button(
                                "Assign Demo Driver",
                                on_click=lambda route_id=route.route_id: _assign_demo_driver(route_id, refresh_callback),
                            ).props("flat color=primary")


def _assign_demo_driver(route_id: str, refresh_callback) -> None:
    platform.assign_driver(route_id, platform.settings.driver_demo_id, "dispatcher")
    ui.notify(f"Assigned {platform.settings.driver_demo_id} to {route_id}")
    refresh_callback()


def _render_issue_queue(snapshot: DispatcherSnapshot) -> None:
    with ui.card().classes("vrp-panel p-5"):
        ui.label("Exception Queue").classes("text-xl font-bold")
        if not snapshot.issues:
            ui.label("No open solve issues. The current plan is fully serviceable.").classes("vrp-subtle")
            return
        for issue in snapshot.issues[:12]:
            tone = "var(--vrp-danger)" if issue.severity == "error" else "var(--vrp-warn)"
            with ui.row().classes("w-full items-start justify-between py-2 border-b border-[rgba(17,36,58,0.08)]"):
                with ui.column().classes("gap-0"):
                    ui.label(issue.code.replace("_", " ")).classes("font-semibold")
                    ui.label(issue.message).classes("text-sm vrp-subtle")
                    if issue.order_id:
                        ui.label(f"Order {issue.order_id}").classes("text-xs vrp-subtle")
                ui.label(issue.issue_kind.replace("_", " ").title()).style(f"color: {tone};")


def _render_run_history(snapshot: DispatcherSnapshot) -> None:
    with ui.card().classes("vrp-panel p-5"):
        ui.label("Run History").classes("text-xl font-bold")
        if not snapshot.recent_runs:
            ui.label("No solve runs recorded yet.").classes("vrp-subtle")
            return
        for run in snapshot.recent_runs[:10]:
            with ui.row().classes("w-full items-start justify-between py-2 border-b border-[rgba(17,36,58,0.08)]"):
                with ui.column().classes("gap-0"):
                    ui.label(f"{run.run_id} · {run.objective.value}").classes("font-semibold")
                    ui.label(
                        f"{run.route_count} routes · {run.planned_order_count} planned · {run.unassigned_count} unassigned"
                    ).classes("text-sm vrp-subtle")
                    ui.label(
                        f"Distance {run.total_distance_km:.1f} km · Cost {run.total_cost:.2f}"
                    ).classes("text-sm vrp-subtle")
                ui.label(run.created_at.strftime("%Y-%m-%d %H:%M")).classes("vrp-mono text-sm")


def _render_traffic_panel(snapshot: DispatcherSnapshot) -> None:
    with ui.card().classes("vrp-panel p-5"):
        ui.label("Traffic And Incident Feed").classes("text-xl font-bold")
        if not snapshot.traffic_incidents:
            ui.label("No active incident overlays available.").classes("vrp-subtle")
            return
        for incident in snapshot.traffic_incidents:
            with ui.row().classes("w-full items-start justify-between py-2 border-b border-[rgba(17,36,58,0.08)]"):
                with ui.column().classes("gap-0"):
                    ui.label(incident.name).classes("font-semibold")
                    ui.label(incident.description).classes("text-sm vrp-subtle")
                    ui.label(
                        f"Delay x{incident.delay_multiplier:.2f} · Radius {incident.radius_km:.1f} km"
                    ).classes("text-sm vrp-subtle")
                ui.label(incident.severity.title()).style("color: var(--vrp-warn);")


def _render_warehouse_plans(snapshot: DispatcherSnapshot) -> None:
    with ui.card().classes("vrp-panel p-5"):
        ui.label("Warehouse Load Sheets").classes("text-xl font-bold")
        if not snapshot.warehouse_plans:
            ui.label("Run a plan to generate truck loading instructions.").classes("vrp-subtle")
            return
        for plan in snapshot.warehouse_plans[:4]:
            with ui.card().classes("bg-white/80 shadow-none border border-[rgba(17,36,58,0.08)]"):
                ui.label(f"{plan.vehicle_name} · {plan.route_id}").classes("font-semibold")
                ui.label(
                    f"{plan.vehicle_category.value.replace('_', ' ').title()} · Load {plan.total_weight_kg:.0f} kg · {plan.total_volume_m3:.2f} m3 · Utilization {plan.utilization_pct:.0f}%"
                ).classes("text-sm vrp-subtle")
                for instruction in plan.instructions[:6]:
                    ui.label(
                        f"Load #{instruction.load_sequence} · Stop {instruction.stop_sequence} · {instruction.external_ref} · {instruction.slot_label} · {instruction.notes}"
                    ).classes("text-sm")


def _render_shipment_snapshot(snapshot: ShipmentSnapshot) -> None:
    with ui.card().classes("vrp-panel p-6 w-full"):
        with ui.row().classes("w-full items-start justify-between"):
            with ui.column().classes("gap-1"):
                ui.label(f"{snapshot.order.external_ref} · {snapshot.order.customer_name}").classes("text-2xl font-bold")
                ui.label(snapshot.order.address or "Address not captured").classes("vrp-subtle")
            ui.label(snapshot.order.status.value.replace("_", " ").title()).style(_status_tone(snapshot.order.status.value))
        with ui.grid().classes("w-full grid-cols-1 md:grid-cols-4 gap-4 mt-4"):
            data_points = [
                ("Route", snapshot.route_id or "Not yet planned"),
                ("Vehicle", snapshot.vehicle_id or "-"),
                ("Stop Sequence", str(snapshot.stop_sequence or "-")),
                ("ETA", _minutes_label(snapshot.eta_minute)),
            ]
            for title, value in data_points:
                with ui.card().classes("bg-white/80 shadow-none border border-[rgba(17,36,58,0.08)]"):
                    ui.label(title).classes("text-sm vrp-subtle")
                    ui.label(value).classes("vrp-kpi-value text-xl font-semibold")
        if snapshot.navigation_url:
            ui.link("Open navigation", snapshot.navigation_url, new_tab=True).classes("mt-3")
        _render_map("Shipment Route", [_map_layer(snapshot.path_points, ROUTE_COLORS[0], snapshot.stop_points)])
        with ui.grid().classes("w-full grid-cols-1 lg:grid-cols-2 gap-4 mt-4"):
            with ui.card().classes("bg-white/80 shadow-none border border-[rgba(17,36,58,0.08)]"):
                ui.label("Customer Timeline").classes("text-lg font-bold")
                if not snapshot.customer_events:
                    ui.label("No outbound customer updates published yet.").classes("vrp-subtle")
                for event in snapshot.customer_events[:8]:
                    ui.label(f"{event.occurred_at:%Y-%m-%d %H:%M} · {event.details}").classes("text-sm")
            with ui.card().classes("bg-white/80 shadow-none border border-[rgba(17,36,58,0.08)]"):
                ui.label("Execution Timeline").classes("text-lg font-bold")
                if not snapshot.delivery_events:
                    ui.label("No driver execution events recorded yet.").classes("vrp-subtle")
                for event in snapshot.delivery_events[:8]:
                    ui.label(f"{event.occurred_at:%Y-%m-%d %H:%M} · {event.label} · {event.details}").classes("text-sm")


def _render_driver_route(route_view: DriverRouteView) -> None:
    with ui.card().classes("vrp-panel p-6 w-full"):
        ui.label(f"{route_view.route_id} · {route_view.vehicle_name}").classes("text-2xl font-bold")
        ui.label(
            f"{route_view.vehicle_category.value.replace('_', ' ').title()} · {len(route_view.stops)} stops · Drive {route_view.total_drive_min:.0f} min · Distance {route_view.total_distance_km:.1f} km"
        ).classes("vrp-subtle")
        ui.label(
            f"Fuel {route_view.fuel_used:.1f} units · Energy {route_view.total_energy_cost:.2f} · Breaks {route_view.total_break_min:.0f} min"
        ).classes("vrp-subtle")
        if route_view.navigation_url:
            ui.link("Open navigation", route_view.navigation_url, new_tab=True).classes("mt-2")
    if route_view.break_windows:
        with ui.card().classes("vrp-panel p-5 w-full"):
            ui.label("Driver Break Plan").classes("text-xl font-bold")
            for item in route_view.break_windows:
                ui.label(
                    f"{_minutes_label(item.start_minute)} · {item.duration_min:.0f} min · {item.reason}"
                ).classes("text-sm")
    _render_map("Driver Route Map", [_map_layer(route_view.path_points, ROUTE_COLORS[1], route_view.stop_points)])


def _render_dispatcher_brief(snapshot: DispatcherSnapshot) -> None:
    _render_workspace_metrics(
        [
            ("Demand In View", str(snapshot.filtered_order_count), "Orders matching the current planning lens"),
            ("Routes Live", str(len(snapshot.routes)), "Current board entries available to dispatch"),
            ("Warehouse Plans", str(len(snapshot.warehouse_plans)), "Load sheets generated from the latest runs"),
            ("Issues", str(len(snapshot.issues)), "Open warnings and unassigned orders requiring action"),
        ]
    )


def _readiness_tone(readiness: str) -> str:
    if readiness == "ready":
        return "vrp-tone-ready"
    if readiness == "expedite":
        return "vrp-tone-warn"
    return "vrp-tone-danger"


def _render_warehouse_overview(snapshot: WarehouseSnapshot) -> None:
    _render_workspace_metrics(
        [
            ("Active Bays", str(snapshot.active_routes), "Routes currently staged for loading"),
            ("Ready Bays", str(snapshot.ready_bays), "Docks clear to begin fill sequence"),
            ("Attention Bays", str(snapshot.attention_bays), "Loads needing supervisor review"),
            ("Load Volume", f"{snapshot.total_volume_m3:.1f} m3", "Aggregated cube across staged trucks"),
        ]
    )
    with ui.grid().classes("w-full grid-cols-1 xl:grid-cols-3 gap-4"):
        for dock in snapshot.dock_views:
            with ui.card().classes("vrp-panel p-5"):
                with ui.row().classes("w-full items-start justify-between"):
                    with ui.column().classes("gap-0"):
                        ui.label(f"{dock.bay_label} · {dock.vehicle_name}").classes("text-xl font-bold")
                        ui.label(
                            f"{dock.vehicle_category.value.replace('_', ' ').title()} · {dock.stop_count} loads · Departure {_minutes_label(dock.departure_minute)}"
                        ).classes("text-sm vrp-subtle")
                    ui.label(dock.readiness.title()).classes(f"text-sm font-bold {_readiness_tone(dock.readiness)}")
                ui.label(
                    f"Utilization {dock.utilization_pct:.0f}% · Priority orders {dock.priority_orders}"
                ).classes("text-sm vrp-subtle mt-2")
                ui.label(dock.note).classes("text-sm mt-2")


def _render_admin_overview(snapshot: AdminSnapshot) -> None:
    _render_workspace_metrics(
        [
            ("Optimization Runs", str(snapshot.optimization_runs), "Recent solve runs retained in the platform"),
            ("Dispatched Routes", str(snapshot.dispatched_routes), "Routes currently assigned to drivers"),
            ("Fallback Usage", str(snapshot.fallback_runs), "Runs recovered from primary optimizer failure"),
            ("Energy Cost", f"{snapshot.total_energy_cost:.2f}", "Aggregate energy spend on current visible routes"),
        ]
    )
    with ui.grid().classes("w-full grid-cols-1 xl:grid-cols-2 gap-4"):
        with ui.card().classes("vrp-panel p-5"):
            ui.label("Operational Audit Trail").classes("text-xl font-bold")
            if not snapshot.audits:
                ui.label("No audit entries yet.").classes("vrp-subtle")
            for audit in snapshot.audits[:12]:
                with ui.row().classes("w-full items-start justify-between py-2 border-b border-[rgba(17,36,58,0.08)]"):
                    with ui.column().classes("gap-0"):
                        ui.label(f"{audit.actor} · {audit.action}").classes("font-semibold")
                        ui.label(f"{audit.entity_type} · {audit.entity_id}").classes("text-sm vrp-subtle")
                    ui.label(audit.occurred_at.strftime("%Y-%m-%d %H:%M")).classes("vrp-mono text-sm")
        with ui.card().classes("vrp-panel p-5"):
            ui.label("Run Reliability").classes("text-xl font-bold")
            ui.label(
                f"Visible distance {snapshot.total_distance_km:.1f} km · Emissions {snapshot.total_emissions_kg:.2f} kg · Issues {snapshot.open_issues}"
            ).classes("text-sm vrp-subtle")
            for run in snapshot.recent_runs[:10]:
                ui.label(
                    f"{run.run_id} · {run.objective.value} · {run.route_count} routes · {run.unassigned_count} unassigned"
                ).classes("text-sm py-1")


def _render_issue_list(title: str, issues) -> None:
    with ui.card().classes("vrp-panel p-5"):
        ui.label(title).classes("text-xl font-bold")
        if not issues:
            ui.label("No active issues in this workspace.").classes("vrp-subtle")
            return
        for issue in issues[:12]:
            tone = "var(--vrp-danger)" if issue.severity == "error" else "var(--vrp-warn)"
            with ui.row().classes("w-full items-start justify-between py-2 border-b border-[rgba(17,36,58,0.08)]"):
                with ui.column().classes("gap-0"):
                    ui.label(issue.code.replace("_", " ")).classes("font-semibold")
                    ui.label(issue.message).classes("text-sm vrp-subtle")
                    if issue.order_id:
                        ui.label(f"Order {issue.order_id}").classes("text-xs vrp-subtle")
                ui.label(issue.issue_kind.replace("_", " ").title()).style(f"color: {tone};")


def _render_warehouse_load_sequences(snapshot: WarehouseSnapshot) -> None:
    with ui.card().classes("vrp-panel p-5"):
        ui.label("Truck Fill Instructions").classes("text-xl font-bold")
        ui.label("Each load sheet is sequenced in reverse stop order so the next drop is the most accessible in the truck.").classes("text-sm vrp-subtle")
        if not snapshot.route_plans:
            ui.label("No staged route plans available for the warehouse.").classes("vrp-subtle mt-3")
            return
        for plan in snapshot.route_plans[:8]:
            with ui.card().classes("bg-white/80 shadow-none border border-[rgba(17,36,58,0.08)] mt-3"):
                with ui.row().classes("w-full items-start justify-between"):
                    with ui.column().classes("gap-0"):
                        ui.label(f"{plan.vehicle_name} · {plan.route_id}").classes("font-semibold")
                        ui.label(
                            f"{plan.vehicle_category.value.replace('_', ' ').title()} · {len(plan.instructions)} slots · {plan.total_weight_kg:.0f} kg · {plan.total_volume_m3:.2f} m3"
                        ).classes("text-sm vrp-subtle")
                    ui.label(f"{plan.utilization_pct:.0f}% full").classes("vrp-pill")
                for instruction in plan.instructions[:7]:
                    ui.label(
                        f"Load #{instruction.load_sequence} -> Stop {instruction.stop_sequence} -> {instruction.external_ref} -> {instruction.slot_label} -> {instruction.notes}"
                    ).classes("text-sm py-1")


def _render_admin_route_watch(snapshot: AdminSnapshot) -> None:
    with ui.card().classes("vrp-panel p-5"):
        ui.label("Fleet And Route Watch").classes("text-xl font-bold")
        if not snapshot.routes:
            ui.label("No routes are currently visible in the admin view.").classes("vrp-subtle")
            return
        for route in snapshot.routes[:12]:
            with ui.row().classes("w-full items-start justify-between py-2 border-b border-[rgba(17,36,58,0.08)]"):
                with ui.column().classes("gap-0"):
                    ui.label(f"{route.route_id} · {route.vehicle_name}").classes("font-semibold")
                    ui.label(
                        f"{route.vehicle_category.value.replace('_', ' ').title()} · {route.stop_count} stops · ETA {_minutes_label(route.first_eta_minute)}"
                    ).classes("text-sm vrp-subtle")
                    ui.label(
                        f"Cost {route.total_cost:.2f} · Energy {route.total_energy_cost:.2f} · Fuel {route.fuel_used:.1f}"
                    ).classes("text-sm vrp-subtle")
                ui.label(route.status.value.title()).style(_status_tone(route.status.value))


@ui.page("/login")
def login_page() -> None:
    existing_user = _current_user()
    if existing_user is not None:
        ui.navigate.to(_default_route_for(existing_user.role))
        return

    with ui.column().classes("vrp-shell w-full gap-6"):
        with ui.card().classes("vrp-panel vrp-hero p-8 w-full"):
            ui.label("VRP Platform Login").classes("text-4xl font-bold")
            ui.label(
                "Sign in to the control tower, customer portal, or driver workflow."
            ).classes("text-lg opacity-90")
        with ui.card().classes("vrp-panel p-6 w-full max-w-xl self-center"):
            username = ui.input("Username", value="dispatcher").classes("w-full")
            password = ui.input("Password", password=True, password_toggle_button=True).classes("w-full")
            feedback = ui.label("").classes("text-sm")

            def submit() -> None:
                try:
                    user = platform.auth_service.login(
                        username.value.strip(),
                        password.value,
                    )
                    _store_user(user)
                    ui.notify(f"Signed in as {user.username}", color="positive")
                    ui.navigate.to(_default_route_for(user.role))
                except Exception as exc:
                    feedback.text = str(exc)
                    feedback.style("color: var(--vrp-danger);")

            with ui.row().classes("gap-3 mt-4"):
                ui.button("Sign In", on_click=submit).props("color=primary")
            with ui.column().classes("gap-1 mt-4"):
                ui.label("Demo accounts").classes("text-base font-bold")
                ui.label("dispatcher / dispatcher123").classes("vrp-mono text-sm")
                ui.label("customer / customer123").classes("vrp-mono text-sm")
                ui.label("driver / driver123").classes("vrp-mono text-sm")
                ui.label("admin / admin123").classes("vrp-mono text-sm")


@ui.page("/")
def home() -> None:
    user = _current_user()
    if user is None:
        ui.navigate.to("/login")
        return
    ui.navigate.to(_default_route_for(user.role))


@ui.page("/dispatcher")
def dispatcher_page() -> None:
    user = _require_roles(DISPATCHER_ROLES)
    if user is None:
        return
    with _workspace_frame(
        user,
        "dispatcher",
        "Dispatcher Workbench",
        "Dispatcher Control Tower",
        "Run fuel-aware planning, watch the live route picture, control incident response, and hand the warehouse a truck-specific fill plan.",
    ):

        dashboard = ui.column().classes("w-full gap-4")
        comparison = ui.grid().classes("w-full grid-cols-1 md:grid-cols-3 gap-4")
        manifest_input = None
        objective_select = None
        search_input = None
        status_select = None
        sort_select = None
        descending_switch = None
        page_size_select = None
        snapshot_state = {"value": None}
        feedback_state = {"lines": [], "tone": "info"}
        planner_scope = {"order_ids": None, "label": "all filtered orders"}
        selection_state = {"order_ids": set()}
        filter_state = {
            "search_term": "",
            "status_filter": "all",
            "sort_by": "external_ref",
            "descending": False,
            "page": 1,
            "page_size": 8,
        }

        status_options = {
            "all": "All statuses",
            OrderStatus.PENDING.value: "Pending",
            OrderStatus.PLANNED.value: "Planned",
            OrderStatus.IN_TRANSIT.value: "In transit",
            OrderStatus.FAILED.value: "Failed",
            OrderStatus.DELIVERED.value: "Delivered",
        }
        sort_options = {
            "external_ref": "Order reference",
            "customer_name": "Customer name",
            "priority": "Priority",
            "demand_kg": "Weight",
            "window_start": "Window start",
            "status": "Status",
        }

        with ui.dialog() as progress_dialog, ui.card().classes("vrp-panel p-6 min-w-[24rem]"):
            progress_title = ui.label("Running operation").classes("text-xl font-bold")
            progress_detail = ui.label("Preparing").classes("vrp-subtle")
            progress_bar = ui.linear_progress(value=0.0).classes("w-full mt-3")

        with ui.dialog() as ingest_confirm, ui.card().classes("vrp-panel p-6 min-w-[24rem]"):
            ui.label("Confirm manifest ingest").classes("text-xl font-bold")
            ui.label(
                "Persist these orders into the operational queue and validate them immediately."
            ).classes("vrp-subtle")
            with ui.row().classes("justify-end gap-2 mt-4"):
                ui.button("Cancel", on_click=ingest_confirm.close).props("flat")
                ui.button("Ingest", on_click=lambda: asyncio.create_task(run_manifest_ingest())).props("color=primary")

        with ui.dialog() as optimize_confirm, ui.card().classes("vrp-panel p-6 min-w-[26rem]"):
            ui.label("Confirm route optimization").classes("text-xl font-bold")
            optimize_scope_label = ui.label("Optimize all filtered orders.").classes("vrp-subtle")
            with ui.row().classes("justify-end gap-2 mt-4"):
                ui.button("Cancel", on_click=optimize_confirm.close).props("flat")
                ui.button("Optimize", on_click=lambda: asyncio.create_task(run_live_solve())).props("color=primary")

        def _selected_statuses() -> list[OrderStatus] | None:
            if filter_state["status_filter"] == "all":
                return None
            return [OrderStatus(filter_state["status_filter"])]

        def _set_feedback(lines: list[str], tone: str = "info") -> None:
            feedback_state["lines"] = lines
            feedback_state["tone"] = tone

        async def _open_progress(title: str, detail: str, value: float) -> None:
            progress_title.text = title
            progress_detail.text = detail
            progress_bar.value = value
            progress_dialog.open()
            await asyncio.sleep(0.05)

        def refresh_dashboard() -> None:
            snapshot = platform.dispatcher_snapshot(
                search_term=filter_state["search_term"],
                statuses=_selected_statuses(),
                sort_by=filter_state["sort_by"],
                descending=filter_state["descending"],
                page=filter_state["page"],
                page_size=filter_state["page_size"],
            )
            total_pages = max(
                1,
                (max(snapshot.filtered_order_count, 1) + snapshot.order_page_size - 1) // snapshot.order_page_size,
            )
            if filter_state["page"] > total_pages:
                filter_state["page"] = total_pages
                snapshot = platform.dispatcher_snapshot(
                    search_term=filter_state["search_term"],
                    statuses=_selected_statuses(),
                    sort_by=filter_state["sort_by"],
                    descending=filter_state["descending"],
                    page=filter_state["page"],
                    page_size=filter_state["page_size"],
                )
            snapshot_state["value"] = snapshot
            dashboard.clear()
            with dashboard:
                _render_dispatcher_metrics(snapshot)
                _render_feedback_panel(feedback_state["lines"], feedback_state["tone"])
                _render_map(
                    "Live Route Map",
                    [
                        _map_layer(route.path_points, ROUTE_COLORS[index % len(ROUTE_COLORS)], route.stop_points)
                        for index, route in enumerate(snapshot.map_routes[:6])
                    ],
                    snapshot.fleet_positions,
                    snapshot.traffic_incidents,
                )
                with ui.grid().classes("w-full grid-cols-1 xl:grid-cols-2 gap-4"):
                    _render_order_workbench(
                        snapshot,
                        selection_state["order_ids"],
                        toggle_order_selection,
                        select_visible_orders,
                        clear_selection,
                        previous_page,
                        next_page,
                    )
                    _render_route_board(snapshot, refresh_dashboard)
                _render_route_intelligence("Dispatcher Route Intelligence", snapshot.route_insights)
                with ui.grid().classes("w-full grid-cols-1 xl:grid-cols-2 gap-4"):
                    _render_traffic_panel(snapshot)
                    _render_warehouse_plans(snapshot)
                with ui.grid().classes("w-full grid-cols-1 xl:grid-cols-2 gap-4"):
                    _render_issue_queue(snapshot)
                    _render_run_history(snapshot)

        def load_sample() -> None:
            manifest_input.value = SAMPLE_MANIFEST
            _set_feedback(["Loaded sample manifest into the intake editor."], "info")
            refresh_dashboard()

        def apply_filters() -> None:
            filter_state["search_term"] = (search_input.value or "").strip()
            filter_state["status_filter"] = status_select.value or "all"
            filter_state["sort_by"] = sort_select.value or "external_ref"
            filter_state["descending"] = bool(descending_switch.value)
            filter_state["page_size"] = int(page_size_select.value or 8)
            filter_state["page"] = 1
            refresh_dashboard()

        def reset_filters() -> None:
            search_input.value = ""
            status_select.value = "all"
            sort_select.value = "external_ref"
            descending_switch.value = False
            page_size_select.value = 8
            filter_state.update(
                search_term="",
                status_filter="all",
                sort_by="external_ref",
                descending=False,
                page=1,
                page_size=8,
            )
            refresh_dashboard()

        def toggle_order_selection(order_id: str, selected: bool) -> None:
            if selected:
                selection_state["order_ids"].add(order_id)
            else:
                selection_state["order_ids"].discard(order_id)
            refresh_dashboard()

        def select_visible_orders() -> None:
            snapshot = snapshot_state["value"]
            if snapshot is None:
                return
            selection_state["order_ids"].update(order.id for order in snapshot.orders)
            refresh_dashboard()

        def clear_selection() -> None:
            selection_state["order_ids"].clear()
            refresh_dashboard()

        def previous_page() -> None:
            filter_state["page"] = max(1, filter_state["page"] - 1)
            refresh_dashboard()

        def next_page() -> None:
            snapshot = snapshot_state["value"]
            if snapshot is None:
                return
            total_pages = max(
                1,
                (max(snapshot.filtered_order_count, 1) + snapshot.order_page_size - 1) // snapshot.order_page_size,
            )
            filter_state["page"] = min(total_pages, filter_state["page"] + 1)
            refresh_dashboard()

        def open_ingest_confirm() -> None:
            ingest_confirm.open()

        def open_optimize_confirm(selected_only: bool) -> None:
            if selected_only:
                if not selection_state["order_ids"]:
                    _set_feedback(
                        ["Select one or more orders before running targeted optimization."],
                        "warning",
                    )
                    refresh_dashboard()
                    return
                planner_scope["order_ids"] = sorted(selection_state["order_ids"])
                planner_scope["label"] = f"{len(selection_state['order_ids'])} selected orders"
            else:
                planner_scope["order_ids"] = None
                planner_scope["label"] = "all filtered active orders"
            optimize_scope_label.text = f"Optimize {planner_scope['label']} using the current objective."
            optimize_confirm.open()

        async def run_manifest_ingest() -> None:
            ingest_confirm.close()
            try:
                await _open_progress("Manifest Intake", "Parsing and validating manifest rows...", 0.12)
                payload = (manifest_input.value or "").encode("utf-8")
                orders, warnings = await asyncio.to_thread(platform.ingest_manifest, payload)
                progress_detail.text = "Refreshing dispatcher workbench..."
                progress_bar.value = 0.9
                await asyncio.sleep(0.05)
                lines = [f"Ingested {len(orders)} orders into the operational queue."]
                if warnings:
                    lines.extend(warnings[:6])
                    _set_feedback(lines, "warning")
                else:
                    _set_feedback(lines, "positive")
                ui.notify(lines[0], color="positive")
                refresh_dashboard()
            except Exception as exc:
                _set_feedback([f"Manifest ingest failed: {exc}"], "negative")
                ui.notify(str(exc), color="negative")
                refresh_dashboard()
            finally:
                progress_dialog.close()

        async def run_live_solve() -> None:
            optimize_confirm.close()
            try:
                objective = ObjectiveMode(objective_select.value)
                await _open_progress("Planning Run", "Building solve request...", 0.12)
                request = await asyncio.to_thread(platform.build_solve_request, objective, planner_scope["order_ids"])
                progress_detail.text = "Optimizing routes and evaluating constraints..."
                progress_bar.value = 0.55
                await asyncio.sleep(0.05)
                response = await asyncio.to_thread(platform.solve_plan, request)
                progress_detail.text = "Publishing downstream customer updates..."
                progress_bar.value = 0.82
                await asyncio.sleep(0.05)
                published = await asyncio.to_thread(platform.publish_customer_updates, response)
                progress_bar.value = 1.0
                await asyncio.sleep(0.08)
                selection_state["order_ids"].difference_update(
                    {violation.order_id for violation in response.unassigned_orders if violation.order_id}
                )
                _set_feedback(
                    [
                        f"Created {response.run_id} for {planner_scope['label']}.",
                        f"Routes {len(response.routes)} · Unassigned {len(response.unassigned_orders)} · Customer updates {published}",
                    ],
                    "positive" if not response.unassigned_orders else "warning",
                )
                ui.notify(
                    f"Created {response.run_id} with {len(response.routes)} routes and {len(response.unassigned_orders)} exceptions",
                    color="positive" if not response.unassigned_orders else "warning",
                )
                refresh_dashboard()
            except Exception as exc:
                _set_feedback([f"Optimization failed: {exc}"], "negative")
                ui.notify(str(exc), color="negative")
                refresh_dashboard()
            finally:
                progress_dialog.close()

        async def compare_scenarios() -> None:
            comparison.clear()
            try:
                scenarios = (ObjectiveMode.COST, ObjectiveMode.ON_TIME, ObjectiveMode.EMISSIONS)
                await _open_progress("Scenario Preview", "Evaluating objective scenarios...", 0.1)
                results = []
                for index, objective in enumerate(scenarios, start=1):
                    progress_detail.text = f"Previewing {objective.value.replace('_', ' ')} scenario..."
                    progress_bar.value = index / (len(scenarios) + 1)
                    await asyncio.sleep(0.05)
                    results.append((objective, await asyncio.to_thread(_preview_plan, objective)))
                progress_bar.value = 1.0
                with comparison:
                    for objective, response in results:
                        total_cost = sum(route.total_cost for route in response.routes)
                        total_distance = sum(route.total_distance_km for route in response.routes)
                        total_fuel = sum(route.fuel_used for route in response.routes)
                        with ui.card().classes("vrp-panel p-5"):
                            ui.label(objective.value.replace("_", " ").title()).classes("text-xl font-bold")
                            ui.label(f"{len(response.routes)} routes").classes("vrp-kpi-value text-2xl")
                            ui.label(
                                f"Cost {total_cost:.2f} · Distance {total_distance:.1f} km · Fuel {total_fuel:.1f}"
                            ).classes("text-sm vrp-subtle")
                            ui.label(
                                f"{len(response.unassigned_orders)} unassigned · Incidents {response.metadata['travel_provider'].get('active_incident_count', 0)}"
                            ).classes("text-sm vrp-subtle")
                _set_feedback(["Scenario preview refreshed for cost, on-time, and emissions."], "info")
                refresh_dashboard()
            except Exception as exc:
                _set_feedback([f"Scenario preview failed: {exc}"], "negative")
                ui.notify(str(exc), color="negative")
                refresh_dashboard()
            finally:
                progress_dialog.close()

        with ui.grid().classes("w-full grid-cols-1 xl:grid-cols-[1.4fr_1fr] gap-4"):
            with ui.card().classes("vrp-panel p-5"):
                ui.label("Manifest Intake").classes("text-xl font-bold")
                ui.label(
                    "Paste a CSV manifest with deterministic dimensions so the optimizer can choose the right truck class."
                ).classes("vrp-subtle")
                manifest_input = ui.textarea("Paste manifest CSV", value=SAMPLE_MANIFEST).classes("w-full min-h-[17rem]")
                with ui.row().classes("gap-3 mt-3"):
                    ui.button("Load Sample", on_click=load_sample).props("flat color=secondary")
                    ui.button("Ingest Manifest", on_click=open_ingest_confirm).props("color=primary")
            with ui.card().classes("vrp-panel p-5"):
                ui.label("Planning Controls").classes("text-xl font-bold")
                ui.label(
                    "Optimize persisted demand with mixed fleet economics, break compliance, and live incident penalties."
                ).classes("vrp-subtle")
                objective_select = ui.select(
                    {
                        ObjectiveMode.COST.value: "Cost",
                        ObjectiveMode.ON_TIME.value: "On-time",
                        ObjectiveMode.EMISSIONS.value: "Emissions",
                        ObjectiveMode.BALANCE.value: "Balance",
                        ObjectiveMode.DISTANCE.value: "Distance",
                    },
                    value=ObjectiveMode.COST.value,
                    label="Live plan objective",
                ).classes("w-56")
                with ui.column().classes("w-full gap-3 mt-4"):
                    ui.button("Optimize Filtered Orders", on_click=lambda: open_optimize_confirm(False)).props("color=primary")
                    ui.button("Optimize Selected Orders", on_click=lambda: open_optimize_confirm(True)).props("outline color=primary")
                    ui.button("Preview Scenario Trio", on_click=lambda: asyncio.create_task(compare_scenarios())).props("outline color=primary")
                    ui.label(
                        f"Demo driver ID: {platform.settings.driver_demo_id}. Assign it from the route board to activate the driver page."
                    ).classes("text-sm vrp-subtle")

        with ui.card().classes("vrp-panel p-5"):
            ui.label("Order Filters And Bulk Actions").classes("text-xl font-bold")
            ui.label(
                "Search and page through live demand before running a full plan or a targeted solve."
            ).classes("vrp-subtle")
            with ui.grid().classes("w-full grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-3 mt-4"):
                search_input = ui.input("Search ref / customer / address", value=filter_state["search_term"]).classes("w-full")
                status_select = ui.select(status_options, value=filter_state["status_filter"], label="Status").classes("w-full")
                sort_select = ui.select(sort_options, value=filter_state["sort_by"], label="Sort by").classes("w-full")
                page_size_select = ui.select({8: "8", 12: "12", 20: "20"}, value=filter_state["page_size"], label="Page size").classes("w-full")
                descending_switch = ui.switch("Descending", value=filter_state["descending"]).classes("pt-6")
            with ui.row().classes("gap-3 mt-4"):
                ui.button("Apply Filters", on_click=apply_filters).props("color=primary")
                ui.button("Reset", on_click=reset_filters).props("flat")
                ui.button("Select Visible Orders", on_click=select_visible_orders).props("flat color=primary")
                ui.button("Clear Selection", on_click=clear_selection).props("flat")

        comparison
        refresh_dashboard()


@ui.page("/warehouse")
def warehouse_page() -> None:
    user = _require_roles(WAREHOUSE_ROLES)
    if user is None:
        return
    with _workspace_frame(
        user,
        "warehouse",
        "Warehouse Operations",
        "Warehouse Floor",
        "Turn route plans into disciplined truck-fill execution with dock readiness, stop-aware load sequence, and supervisor exception handling.",
    ):
        stage = ui.column().classes("w-full gap-4")

        def refresh() -> None:
            snapshot = platform.warehouse_snapshot()
            dispatcher_snapshot = platform.dispatcher_snapshot(page_size=8)
            stage.clear()
            with stage:
                _render_warehouse_overview(snapshot)
                with ui.grid().classes("w-full grid-cols-1 xl:grid-cols-[1.1fr_0.9fr] gap-4"):
                    _render_map(
                        "Dock Release Map",
                        [
                            _map_layer(route.path_points, ROUTE_COLORS[index % len(ROUTE_COLORS)], route.stop_points)
                            for index, route in enumerate(dispatcher_snapshot.map_routes[:6])
                        ],
                        dispatcher_snapshot.fleet_positions,
                        dispatcher_snapshot.traffic_incidents,
                    )
                    with ui.column().classes("gap-4"):
                        with ui.card().classes("vrp-panel p-5"):
                            ui.label("Staging Summary").classes("text-xl font-bold")
                            ui.label(
                                f"{snapshot.total_weight_kg:.0f} kg across {snapshot.active_routes} staged routes and {snapshot.total_volume_m3:.2f} m3 of cube."
                            ).classes("text-sm vrp-subtle")
                            ui.label(
                                "Clear ready bays first, expedite priority loads next, and hold attention bays for dock review."
                            ).classes("text-sm mt-2")
                        with ui.card().classes("vrp-panel p-5"):
                            ui.label("Bay Queue").classes("text-xl font-bold")
                            if not snapshot.dock_views:
                                ui.label("No bay allocations exist yet.").classes("vrp-subtle")
                            for dock in snapshot.dock_views[:8]:
                                with ui.row().classes("w-full items-start justify-between py-2 border-b border-[rgba(17,36,58,0.08)]"):
                                    with ui.column().classes("gap-0"):
                                        ui.label(f"{dock.bay_label} · {dock.vehicle_name}").classes("font-semibold")
                                        ui.label(
                                            f"Departure {_minutes_label(dock.departure_minute)} · Utilization {dock.utilization_pct:.0f}%"
                                        ).classes("text-sm vrp-subtle")
                                    ui.label(dock.readiness.title()).classes(f"text-sm font-bold {_readiness_tone(dock.readiness)}")
                with ui.grid().classes("w-full grid-cols-1 xl:grid-cols-[0.9fr_1.1fr] gap-4"):
                    with ui.card().classes("vrp-panel p-5"):
                        ui.label("Dock Readiness Board").classes("text-xl font-bold")
                        if not snapshot.dock_views:
                            ui.label("No routes are currently staged for the warehouse.").classes("vrp-subtle")
                        for dock in snapshot.dock_views:
                            with ui.card().classes("bg-white/80 shadow-none border border-[rgba(17,36,58,0.08)] mt-3"):
                                with ui.row().classes("w-full items-start justify-between"):
                                    with ui.column().classes("gap-0"):
                                        ui.label(f"{dock.bay_label} · {dock.route_id}").classes("font-semibold")
                                        ui.label(
                                            f"{dock.vehicle_name} · {dock.vehicle_category.value.replace('_', ' ').title()} · {dock.stop_count} drops"
                                        ).classes("text-sm vrp-subtle")
                                    ui.label(dock.readiness.title()).classes(f"text-sm font-bold {_readiness_tone(dock.readiness)}")
                                ui.label(dock.note).classes("text-sm mt-2")
                    _render_warehouse_load_sequences(snapshot)
                with ui.grid().classes("w-full grid-cols-1 xl:grid-cols-2 gap-4"):
                    _render_issue_list("Warehouse Exceptions", snapshot.issues)
                    with ui.card().classes("vrp-panel p-5"):
                        ui.label("Release Rules").classes("text-xl font-bold")
                        ui.label("1. Freeze sequence after supervisor release.").classes("text-sm py-1")
                        ui.label("2. Re-check fragile and orientation-locked freight before sealing the truck.").classes("text-sm py-1")
                        ui.label("3. Priority orders load first only when they are earliest route drops.").classes("text-sm py-1")
                        ui.label("4. Escalate any bay above 92% utilization or with unresolved incidents.").classes("text-sm py-1")

        with ui.row().classes("w-full items-center justify-between"):
            ui.label("Warehouse execution updates in one surface.").classes("vrp-subtle")
            ui.button("Refresh Warehouse State", on_click=refresh).props("outline color=primary")
        refresh()


@ui.page("/admin")
def admin_page() -> None:
    user = _require_roles(ADMIN_ROLES)
    if user is None:
        return
    with _workspace_frame(
        user,
        "admin",
        "Operational Oversight",
        "Admin Pulse",
        "Track route reliability, audit activity, fallback usage, energy cost, and open exceptions across the live operating picture.",
    ):
        stage = ui.column().classes("w-full gap-4")

        def refresh() -> None:
            snapshot = platform.admin_snapshot()
            dispatcher_snapshot = platform.dispatcher_snapshot(page_size=8)
            stage.clear()
            with stage:
                _render_admin_overview(snapshot)
                with ui.grid().classes("w-full grid-cols-1 xl:grid-cols-[1.1fr_0.9fr] gap-4"):
                    _render_map(
                        "Admin Network Watch",
                        [
                            _map_layer(route.path_points, ROUTE_COLORS[index % len(ROUTE_COLORS)], route.stop_points)
                            for index, route in enumerate(dispatcher_snapshot.map_routes[:6])
                        ],
                        dispatcher_snapshot.fleet_positions,
                        dispatcher_snapshot.traffic_incidents,
                    )
                    with ui.column().classes("gap-4"):
                        with ui.card().classes("vrp-panel p-5"):
                            ui.label("Reliability Summary").classes("text-xl font-bold")
                            ui.label(
                                f"{snapshot.optimization_runs} runs retained · {snapshot.fallback_runs} fallback recoveries · {snapshot.open_issues} open issues."
                            ).classes("text-sm vrp-subtle")
                            ui.label(
                                f"Distance {snapshot.total_distance_km:.1f} km · Energy {snapshot.total_energy_cost:.2f} · Emissions {snapshot.total_emissions_kg:.2f} kg."
                            ).classes("text-sm vrp-subtle mt-2")
                        with ui.card().classes("vrp-panel p-5"):
                            ui.label("Incident Pulse").classes("text-xl font-bold")
                            if not dispatcher_snapshot.traffic_incidents:
                                ui.label("No active traffic overlays in the current planning horizon.").classes("vrp-subtle")
                            for incident in dispatcher_snapshot.traffic_incidents:
                                ui.label(
                                    f"{incident.name} · {incident.severity.title()} · Delay x{incident.delay_multiplier:.2f}"
                                ).classes("text-sm py-1")
                with ui.grid().classes("w-full grid-cols-1 xl:grid-cols-[0.95fr_1.05fr] gap-4"):
                    _render_admin_route_watch(snapshot)
                    _render_issue_list("Cross-System Exceptions", snapshot.issues)
                _render_route_intelligence("Admin Route Intelligence", snapshot.route_insights)

        with ui.row().classes("w-full items-center justify-between"):
            ui.label("Admin view stays focused on reliability, cost, and auditability.").classes("vrp-subtle")
            ui.button("Refresh Admin Pulse", on_click=refresh).props("outline color=primary")
        refresh()


@ui.page("/customer")
def customer_page() -> None:
    user = _require_roles(CUSTOMER_ROLES)
    if user is None:
        return
    with _workspace_frame(
        user,
        "customer",
        "Customer Experience",
        "Customer Portal",
        "Resolve a shipment by reference and show the route context, ETA, timeline, and live map without exposing dispatcher complexity.",
    ):
        with ui.card().classes("vrp-panel p-5"):
            ui.label("Shipment Lookup").classes("text-xl font-bold")
            ui.label("Use the operational order reference to resolve a shipment with live route context.").classes("text-sm vrp-subtle")
        reference = ui.input("Shipment reference", value="SO-1001").classes("w-80")
        results = ui.column().classes("w-full gap-4")

        def lookup() -> None:
            results.clear()
            snapshot = platform.find_shipment(reference.value)
            if snapshot is None:
                with results:
                    with ui.card().classes("vrp-panel p-6 w-full"):
                        ui.label("Shipment not found").classes("text-xl font-bold")
                        ui.label("Use a persisted order reference from the dispatcher intake flow.").classes("vrp-subtle")
                return
            with results:
                _render_shipment_snapshot(snapshot)

        with ui.row().classes("gap-3"):
            ui.button("Lookup Shipment", on_click=lookup).props("color=primary")
            if user.role == Role.ADMIN:
                ui.button("Open Admin", on_click=lambda: ui.navigate.to("/admin")).props("flat")
            elif user.role in DISPATCHER_ROLES:
                ui.button("Open Dispatcher", on_click=lambda: ui.navigate.to("/dispatcher")).props("flat")
        lookup()


@ui.page("/driver")
def driver_page() -> None:
    user = _require_roles(DRIVER_ROLES)
    if user is None:
        return
    with _workspace_frame(
        user,
        "driver",
        "Driver Execution",
        "Driver Workflow",
        "Load the assigned route, follow the map, execute each stop, and stay inside break and duty limits.",
    ):
        with ui.card().classes("vrp-panel p-5"):
            ui.label("Route Loader").classes("text-xl font-bold")
            ui.label("Load the route assigned to the driver identity below and record execution events stop by stop.").classes("text-sm vrp-subtle")
        driver_input = ui.input("Driver ID", value=platform.settings.driver_demo_id).classes("w-72")
        route_container = ui.column().classes("w-full gap-4")

        def record_event(order_id: str, event_type: DeliveryEventType) -> None:
            try:
                platform.record_delivery_event(
                    DeliveryEvent(
                        event_id=f"evt-{datetime.now().strftime('%H%M%S%f')}",
                        order_id=order_id,
                        driver_id=driver_input.value.strip() or platform.settings.driver_demo_id,
                        event_type=event_type,
                        occurred_at=datetime.now(),
                        notes=f"Recorded {event_type.value} from driver workflow",
                    )
                )
                ui.notify(f"Recorded {event_type.value} for {order_id}")
                load_route()
            except Exception as exc:
                ui.notify(str(exc), color="negative")

        def load_route() -> None:
            route_container.clear()
            route_view = platform.driver_route(driver_input.value.strip() or platform.settings.driver_demo_id)
            with route_container:
                if route_view is None:
                    with ui.card().classes("vrp-panel p-6 w-full"):
                        ui.label("No active route assigned").classes("text-xl font-bold")
                        ui.label(
                            "Assign the demo driver from the dispatcher route board after running an optimization."
                        ).classes("vrp-subtle")
                    return
                _render_driver_route(route_view)
                for stop in route_view.stops:
                    with ui.card().classes("vrp-panel p-5 w-full"):
                        with ui.row().classes("w-full items-start justify-between"):
                            with ui.column().classes("gap-0"):
                                ui.label(f"Stop {stop.sequence} · {stop.external_ref}").classes("text-xl font-bold")
                                ui.label(f"{stop.customer_name} · ETA {_minutes_label(stop.eta_minute)}").classes("vrp-subtle")
                                ui.label(stop.address or "Address not captured").classes("text-sm vrp-subtle")
                            ui.label(stop.status.value.replace("_", " ").title()).style(_status_tone(stop.status.value))
                        with ui.row().classes("gap-3 mt-3"):
                            ui.button(
                                "Arrived",
                                on_click=lambda order_id=stop.order_id: record_event(order_id, DeliveryEventType.ARRIVED),
                            ).props("outline color=primary")
                            ui.button(
                                "Delivered",
                                on_click=lambda order_id=stop.order_id: record_event(order_id, DeliveryEventType.DELIVERED),
                            ).props("color=positive")
                            ui.button(
                                "Failed Attempt",
                                on_click=lambda order_id=stop.order_id: record_event(order_id, DeliveryEventType.FAILED_ATTEMPT),
                            ).props("color=negative")

        with ui.row().classes("gap-3"):
            ui.button("Load Assigned Route", on_click=load_route).props("color=primary")
            if user.role == Role.ADMIN:
                ui.button("Open Admin", on_click=lambda: ui.navigate.to("/admin")).props("flat")
            elif user.role in DISPATCHER_ROLES:
                ui.button("Open Dispatcher", on_click=lambda: ui.navigate.to("/dispatcher")).props("flat")
        load_route()


def run() -> None:
    ui.run(
        title=platform.settings.app_name,
        reload=False,
        storage_secret=platform.settings.secret_key,
    )


if __name__ in {"__main__", "__mp_main__"}:
    run()
