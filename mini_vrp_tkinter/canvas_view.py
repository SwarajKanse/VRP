"""Canvas-based route visualization and animation."""

from __future__ import annotations

import math
import queue
import threading
import tkinter as tk
from tkinter import ttk

from mini_vrp_tkinter.geo import RoadService
from mini_vrp_tkinter.models import AnimationRoute, GeoPoint, Node, RouteOutline, RouteSummary, SolveStep

DEFAULT_CENTER = GeoPoint(19.0760, 72.8777)
MIN_ZOOM = 3
MAX_ZOOM = 18
TILE_SIZE = 256
SIM_SECONDS_PER_KM = 0.22
MIN_ROUTE_ANIMATION_SECONDS = 4.0
OPTIMAL_COLOR = "#16a34a"
COMPARISON_COLOR = "#dc2626"


class RouteCanvas(ttk.Frame):
    """Blank or map-backed canvas with pan, zoom, selection, and truck animation."""

    def __init__(self, master, road_service: RoadService, path_mode: str = "road"):
        super().__init__(master, padding=0)
        self.road_service = road_service
        self.path_mode = path_mode
        self.canvas = tk.Canvas(self, bg="#f7f8fa", highlightthickness=0, cursor="fleur")
        self.canvas.pack(fill="both", expand=True)

        self._click_callback = None
        self._show_map = False
        self._nodes: dict[str, Node] = {}
        self._step: SolveStep | None = None
        self._baseline: list[RouteSummary] = []
        self._final: list[RouteSummary] = []
        self._view_mode = "final"
        self._selected_node_id: str | None = None

        self._center = DEFAULT_CENTER
        self._zoom = 12
        self._needs_fit = True
        self._node_signature: tuple[tuple[str, float, float], ...] = ()

        self._drag_origin: tuple[float, float, float, float] | None = None
        self._drag_distance = 0.0

        self._images: dict[tuple[int, int, int], tk.PhotoImage] = {}
        self._tile_downloads: queue.Queue[tuple[int, int, int]] = queue.Queue()
        self._tile_results: queue.Queue[tuple[int, int, int, bool]] = queue.Queue()
        self._pending_tiles: set[tuple[int, int, int]] = set()
        self._tile_thread = threading.Thread(target=self._tile_worker, daemon=True)
        self._tile_thread.start()

        self._geometry_cache: dict[tuple[str, ...], list[GeoPoint]] = {}
        self._screen_geometry_cache: dict[tuple[tuple[str, ...], int, float, float], list[tuple[float, float]]] = {}

        self._animation_job = None
        self._animation_routes: list[dict] = []
        self._redraw_pending = False

        self.canvas.bind("<Configure>", lambda _event: self.redraw())
        self.canvas.bind("<ButtonPress-1>", self._handle_press)
        self.canvas.bind("<B1-Motion>", self._handle_drag)
        self.canvas.bind("<ButtonRelease-1>", self._handle_release)
        self.canvas.bind("<MouseWheel>", self._handle_mousewheel)
        self.canvas.bind("<Button-4>", lambda event: self._zoom_at(event.x, event.y, 1))
        self.canvas.bind("<Button-5>", lambda event: self._zoom_at(event.x, event.y, -1))

        self.after(100, self._poll_tile_results)

    def set_click_callback(self, callback) -> None:
        self._click_callback = callback

    def set_scene(
        self,
        nodes: list[Node],
        show_map: bool,
        view_mode: str,
        step: SolveStep | None,
        baseline_routes: list[RouteSummary],
        final_routes: list[RouteSummary],
        selected_node_id: str | None,
    ) -> None:
        signature = tuple(
            sorted(
                (node.node_id, round(node.point.latitude, 6), round(node.point.longitude, 6))
                for node in nodes
            )
        )
        if signature != self._node_signature:
            self._node_signature = signature
            self._needs_fit = True
            self._geometry_cache.clear()
            self._screen_geometry_cache.clear()
        self._nodes = {node.node_id: node for node in nodes}
        self._show_map = show_map
        self._view_mode = view_mode
        self._step = step
        self._baseline = baseline_routes
        self._final = final_routes
        self._selected_node_id = selected_node_id
        self.redraw()

    def redraw(self) -> None:
        if self._redraw_pending:
            return
        self._redraw_pending = True
        self.after_idle(self._draw_now)

    def zoom_in(self) -> None:
        width = max(self.canvas.winfo_width(), 200)
        height = max(self.canvas.winfo_height(), 200)
        self._zoom_at(width / 2.0, height / 2.0, 1)

    def zoom_out(self) -> None:
        width = max(self.canvas.winfo_width(), 200)
        height = max(self.canvas.winfo_height(), 200)
        self._zoom_at(width / 2.0, height / 2.0, -1)

    def fit_scene(self) -> None:
        self._needs_fit = True
        self.redraw()

    def start_animation(self, routes: list[AnimationRoute]) -> None:
        self.stop_animation()
        for index, route in enumerate(routes):
            geometry = self._route_geometry(route.node_ids)
            if len(geometry) < 2:
                continue
            distance_km = route.distance_km if route.distance_km > 0 else self._geometry_length_km(geometry)
            duration_seconds = max(MIN_ROUTE_ANIMATION_SECONDS, distance_km * SIM_SECONDS_PER_KM)
            self._animation_routes.append(
                {
                    "name": route.name,
                    "color": route.color,
                    "geometry": geometry,
                    "progress": 0.0,
                    "duration_seconds": duration_seconds,
                    "start_delay_s": index * 0.6,
                    "elapsed_s": 0.0,
                }
            )
        self._animate()

    def stop_animation(self) -> None:
        if self._animation_job is not None:
            self.after_cancel(self._animation_job)
            self._animation_job = None
        self._animation_routes = []
        self.canvas.delete("truck")

    def _draw_now(self) -> None:
        self._redraw_pending = False
        self.canvas.delete("static")

        width = max(self.canvas.winfo_width(), 200)
        height = max(self.canvas.winfo_height(), 200)
        self._ensure_camera(width, height)

        if self._show_map:
            self._draw_tiles(width, height)
        else:
            self._draw_blank_background(width, height)

        if self._nodes:
            self._draw_route_layers()
            self._draw_nodes()
        else:
            self.canvas.create_text(
                width / 2,
                height / 2,
                text="Add a depot and orders to begin.",
                fill="#6b7280",
                font=("Segoe UI", 14, "normal"),
                tags="static",
            )

        self._draw_header(width)
        self._draw_controls(width, height)
        if self._animation_routes:
            self._draw_trucks()

    def _draw_blank_background(self, width: int, height: int) -> None:
        self.canvas.create_rectangle(0, 0, width, height, fill="#fbfcfd", outline="", tags="static")
        grid = 120
        for x in range(0, width, grid):
            self.canvas.create_line(x, 0, x, height, fill="#eef2f7", tags="static")
        for y in range(0, height, grid):
            self.canvas.create_line(0, y, width, y, fill="#eef2f7", tags="static")

    def _draw_tiles(self, width: int, height: int) -> None:
        center_x, center_y = self.road_service.latlon_to_world(self._center, self._zoom)
        left_world = center_x - (width / 2.0)
        top_world = center_y - (height / 2.0)
        right_world = center_x + (width / 2.0)
        bottom_world = center_y + (height / 2.0)

        min_tile_x = int(math.floor(left_world / TILE_SIZE))
        max_tile_x = int(math.floor(right_world / TILE_SIZE))
        min_tile_y = int(math.floor(top_world / TILE_SIZE))
        max_tile_y = int(math.floor(bottom_world / TILE_SIZE))
        max_tile = 2**self._zoom

        self.canvas.create_rectangle(0, 0, width, height, fill="#d9e8ef", outline="", tags="static")

        for tile_x in range(min_tile_x, max_tile_x + 1):
            for tile_y in range(min_tile_y, max_tile_y + 1):
                wrapped_x = tile_x % max_tile
                if tile_y < 0 or tile_y >= max_tile:
                    continue
                tile_key = (self._zoom, wrapped_x, tile_y)
                canvas_x = (tile_x * TILE_SIZE) - left_world
                canvas_y = (tile_y * TILE_SIZE) - top_world
                image = self._load_tile_image(tile_key)
                if image is not None:
                    self.canvas.create_image(canvas_x, canvas_y, image=image, anchor="nw", tags="static")
                    continue
                self.canvas.create_rectangle(
                    canvas_x,
                    canvas_y,
                    canvas_x + TILE_SIZE,
                    canvas_y + TILE_SIZE,
                    fill="#e7eef3",
                    outline="#d6dee6",
                    tags="static",
                )
                self._request_tile(tile_key)

    def _draw_header(self, width: int) -> None:
        route_label = "Road" if self.path_mode == "road" else "Polyline"
        label = f"{route_label} Map" if self._show_map else f"{route_label} Network"
        self.canvas.create_text(
            16,
            16,
            text=label,
            anchor="nw",
            fill="#0f172a",
            font=("Segoe UI", 11, "bold"),
            tags="static",
        )
        if self._view_mode == "step" and self._step is not None:
            self.canvas.create_text(
                width - 16,
                16,
                text=f"Step {self._step.index}: {self._step.title}",
                anchor="ne",
                fill="#4b5563",
                font=("Segoe UI", 10, "normal"),
                tags="static",
            )

    def _draw_controls(self, width: int, height: int) -> None:
        self.canvas.create_rectangle(
            width - 126,
            height - 126,
            width - 16,
            height - 16,
            fill="#ffffff",
            outline="#d0d7de",
            tags="static",
        )
        self.canvas.create_text(width - 71, height - 108, text=f"Zoom {self._zoom}", fill="#334155", font=("Segoe UI", 9, "bold"), tags="static")
        self.canvas.create_text(width - 71, height - 88, text="Wheel: zoom", fill="#64748b", font=("Segoe UI", 8), tags="static")
        self.canvas.create_text(width - 71, height - 54, text="Drag: pan", fill="#64748b", font=("Segoe UI", 8), tags="static")
        self.canvas.create_text(width - 71, height - 34, text="Delete: remove", fill="#64748b", font=("Segoe UI", 8), tags="static")

    def _draw_route_layers(self) -> None:
        if self._view_mode == "baseline":
            for route in self._baseline:
                self._draw_route_summary(route, color=COMPARISON_COLOR, width=3, dash=(6, 4))
            return
        if self._view_mode == "final":
            for route in self._final:
                self._draw_route_summary(route, color=OPTIMAL_COLOR, width=4)
            return
        if self._step is None:
            return
        for route in self._step.context_routes:
            color = OPTIMAL_COLOR if route.style == "final" else COMPARISON_COLOR
            width = 4 if route.style == "final" else 2
            self._draw_route_summary(route, color=color, width=width)
        if self._step.chosen is not None:
            self._draw_route_outline(self._step.chosen, color=OPTIMAL_COLOR, width=4)
        for alternative in self._step.alternatives:
            self._draw_route_outline(alternative, color=COMPARISON_COLOR, width=2, dash=(6, 4))

    def _draw_route_summary(self, route: RouteSummary, color: str | None = None, width: int = 3, dash=()) -> None:
        outline = RouteOutline(
            name=route.name,
            node_ids=route.node_ids,
            score=route.distance_km,
            reason="",
            style=route.style,
            color=color or route.color,
        )
        self._draw_route_outline(outline, color=color, width=width, dash=dash)

    def _draw_route_outline(self, outline: RouteOutline, color: str | None = None, width: int = 3, dash=()) -> None:
        polyline = self._project_route_points(outline.node_ids)
        flat_points: list[float] = []
        for x, y in polyline:
            flat_points.extend((x, y))
        if len(flat_points) < 4:
            return

        main_color = color or outline.color
        outer_width = width + (6 if self._show_map else 4)
        middle_width = width + (3 if self._show_map else 2)
        smooth = self.path_mode == "road"
        splinesteps = 24 if smooth else 1
        self.canvas.create_line(
            *flat_points,
            fill="#0f172a" if self._show_map else "#ffffff",
            width=outer_width,
            smooth=smooth,
            splinesteps=splinesteps,
            dash=dash,
            tags="static",
        )
        self.canvas.create_line(
            *flat_points,
            fill="#ffffff" if self._show_map else "#dbeafe",
            width=middle_width,
            smooth=smooth,
            splinesteps=splinesteps,
            dash=dash,
            tags="static",
        )
        self.canvas.create_line(
            *flat_points,
            fill=main_color,
            width=width,
            smooth=smooth,
            splinesteps=splinesteps,
            dash=dash,
            tags="static",
        )

    def _draw_nodes(self) -> None:
        focus_ids = set(self._step.focus_node_ids) if self._step is not None and self._view_mode == "step" else set()
        for node in self._nodes.values():
            x, y = self._project(node.point)
            if node.node_id == self._selected_node_id:
                radius = 11
            elif node.node_id in focus_ids:
                radius = 10
            else:
                radius = 7

            fill = "#0b3b53" if node.kind == "depot" else "#c96a2d"
            if node.node_id in focus_ids:
                fill = "#2f7f5f"

            outline = "#111827" if node.node_id == self._selected_node_id else "#ffffff"
            outline_width = 3 if node.node_id == self._selected_node_id else 2
            self.canvas.create_oval(
                x - radius,
                y - radius,
                x + radius,
                y + radius,
                fill=fill,
                outline=outline,
                width=outline_width,
                tags="static",
            )
            self.canvas.create_text(
                x,
                y - 14,
                text=node.label,
                fill="#0f172a",
                font=("Segoe UI", 9, "bold"),
                tags="static",
            )

    def _draw_trucks(self) -> None:
        self.canvas.delete("truck")
        for item in self._animation_routes:
            polyline = self._project_geometry_points(item["geometry"])
            total = self._polyline_length(polyline)
            if total <= 0:
                continue
            x, y = self._point_along_polyline(polyline, item["progress"] * total)
            self.canvas.create_oval(
                x - 7,
                y - 7,
                x + 7,
                y + 7,
                fill=item["color"],
                outline="#ffffff",
                width=2,
                tags="truck",
            )
            self.canvas.create_text(
                x,
                y - 13,
                text=item["name"].split()[-1],
                fill="#0f172a",
                font=("Segoe UI", 8, "bold"),
                tags="truck",
            )

    def _animate(self) -> None:
        if not self._animation_routes:
            return
        for item in self._animation_routes:
            item["elapsed_s"] += 0.04
            if item["elapsed_s"] < item["start_delay_s"]:
                continue
            active_time = item["elapsed_s"] - item["start_delay_s"]
            item["progress"] = (active_time / item["duration_seconds"]) % 1.0
        self._draw_trucks()
        self._animation_job = self.after(40, self._animate)

    def _route_geometry(self, node_ids: list[str]) -> list[GeoPoint]:
        key = tuple(node_ids)
        if key in self._geometry_cache:
            return self._geometry_cache[key]
        nodes = [self._nodes[node_id] for node_id in node_ids if node_id in self._nodes]
        if self.path_mode == "polyline":
            geometry = [node.point for node in nodes]
        else:
            geometry = self.road_service.compose_route(nodes)
        self._geometry_cache[key] = geometry
        return geometry

    def _project_route_points(self, node_ids: list[str]) -> list[tuple[float, float]]:
        camera_key = (self._zoom, round(self._center.latitude, 6), round(self._center.longitude, 6))
        cache_key = (tuple(node_ids),) + camera_key
        if cache_key in self._screen_geometry_cache:
            return self._screen_geometry_cache[cache_key]
        polyline = self._project_geometry_points(self._route_geometry(node_ids))
        self._screen_geometry_cache[cache_key] = polyline
        return polyline

    def _project_geometry_points(self, geometry: list[GeoPoint]) -> list[tuple[float, float]]:
        return [self._project(point) for point in geometry]

    def _ensure_camera(self, width: int, height: int) -> None:
        if self._needs_fit and self._nodes:
            self._fit_camera(width, height)
            self._needs_fit = False
            return
        if self._center is None:
            self._center = DEFAULT_CENTER

    def _fit_camera(self, width: int, height: int) -> None:
        points = [node.point for node in self._nodes.values()]
        if not points:
            self._center = DEFAULT_CENTER
            self._zoom = 12
            return
        self._zoom = self.road_service.best_zoom(points, width, height)
        world_points = [self.road_service.latlon_to_world(point, self._zoom) for point in points]
        xs = [point[0] for point in world_points]
        ys = [point[1] for point in world_points]
        center_world_x = (min(xs) + max(xs)) / 2.0
        center_world_y = (min(ys) + max(ys)) / 2.0
        self._center = self.road_service.world_to_latlon(center_world_x, center_world_y, self._zoom)
        self._screen_geometry_cache.clear()

    def _project(self, point: GeoPoint) -> tuple[float, float]:
        width = max(self.canvas.winfo_width(), 200)
        height = max(self.canvas.winfo_height(), 200)
        center_world_x, center_world_y = self.road_service.latlon_to_world(self._center, self._zoom)
        world_x, world_y = self.road_service.latlon_to_world(point, self._zoom)
        return (
            (world_x - center_world_x) + (width / 2.0),
            (world_y - center_world_y) + (height / 2.0),
        )

    def _screen_to_geo(self, x: float, y: float) -> GeoPoint:
        width = max(self.canvas.winfo_width(), 200)
        height = max(self.canvas.winfo_height(), 200)
        center_world_x, center_world_y = self.road_service.latlon_to_world(self._center, self._zoom)
        world_x = center_world_x + (x - (width / 2.0))
        world_y = center_world_y + (y - (height / 2.0))
        return self.road_service.world_to_latlon(world_x, world_y, self._zoom)

    def _load_tile_image(self, tile_key: tuple[int, int, int]) -> tk.PhotoImage | None:
        if tile_key in self._images:
            return self._images[tile_key]
        zoom, tile_x, tile_y = tile_key
        tile_path = self.road_service.tile_dir / str(zoom) / str(tile_x) / f"{tile_y}.png"
        if not tile_path.exists():
            return None
        image = tk.PhotoImage(file=str(tile_path))
        self._images[tile_key] = image
        return image

    def _request_tile(self, tile_key: tuple[int, int, int]) -> None:
        if tile_key in self._pending_tiles:
            return
        self._pending_tiles.add(tile_key)
        self._tile_downloads.put(tile_key)

    def _tile_worker(self) -> None:
        while True:
            zoom, tile_x, tile_y = self._tile_downloads.get()
            path = self.road_service.fetch_tile(zoom, tile_x, tile_y)
            self._tile_results.put((zoom, tile_x, tile_y, path is not None))

    def _poll_tile_results(self) -> None:
        should_redraw = False
        while True:
            try:
                zoom, tile_x, tile_y, _success = self._tile_results.get_nowait()
            except queue.Empty:
                break
            self._pending_tiles.discard((zoom, tile_x, tile_y))
            should_redraw = True
        if should_redraw:
            self.redraw()
        self.after(100, self._poll_tile_results)

    def _handle_press(self, event) -> None:
        center_world_x, center_world_y = self.road_service.latlon_to_world(self._center, self._zoom)
        self._drag_origin = (event.x, event.y, center_world_x, center_world_y)
        self._drag_distance = 0.0

    def _handle_drag(self, event) -> None:
        if self._drag_origin is None:
            return
        start_x, start_y, center_world_x, center_world_y = self._drag_origin
        dx = event.x - start_x
        dy = event.y - start_y
        self._drag_distance = max(self._drag_distance, abs(dx) + abs(dy))
        self._center = self.road_service.world_to_latlon(center_world_x - dx, center_world_y - dy, self._zoom)
        self._screen_geometry_cache.clear()
        self.redraw()

    def _handle_release(self, event) -> None:
        if self._drag_origin is None:
            return
        was_drag = self._drag_distance > 6
        self._drag_origin = None
        self._drag_distance = 0.0
        if was_drag or self._click_callback is None:
            return
        point = self._screen_to_geo(event.x, event.y)
        self._click_callback(point, self._hit_test_node(event.x, event.y))

    def _handle_mousewheel(self, event) -> None:
        direction = 1 if event.delta > 0 else -1
        self._zoom_at(event.x, event.y, direction)

    def _zoom_at(self, x: float, y: float, direction: int) -> None:
        new_zoom = max(MIN_ZOOM, min(MAX_ZOOM, self._zoom + direction))
        if new_zoom == self._zoom:
            return

        width = max(self.canvas.winfo_width(), 200)
        height = max(self.canvas.winfo_height(), 200)
        focus_point = self._screen_to_geo(x, y)
        focus_world_x, focus_world_y = self.road_service.latlon_to_world(focus_point, new_zoom)

        self._zoom = new_zoom
        center_world_x = focus_world_x - (x - (width / 2.0))
        center_world_y = focus_world_y - (y - (height / 2.0))
        self._center = self.road_service.world_to_latlon(center_world_x, center_world_y, self._zoom)
        self._screen_geometry_cache.clear()
        self.redraw()

    def _polyline_length(self, points: list[tuple[float, float]]) -> float:
        total = 0.0
        for left, right in zip(points, points[1:]):
            total += math.dist(left, right)
        return total

    def _geometry_length_km(self, points: list[GeoPoint]) -> float:
        total = 0.0
        for left, right in zip(points, points[1:]):
            total += self.road_service.haversine_km(left, right)
        return total

    def _point_along_polyline(self, points: list[tuple[float, float]], distance: float) -> tuple[float, float]:
        if len(points) < 2:
            return points[0] if points else (0.0, 0.0)
        remaining = distance
        for left, right in zip(points, points[1:]):
            segment = math.dist(left, right)
            if remaining <= segment:
                if segment == 0:
                    return right
                ratio = remaining / segment
                return (
                    left[0] + (right[0] - left[0]) * ratio,
                    left[1] + (right[1] - left[1]) * ratio,
                )
            remaining -= segment
        return points[-1]

    def _hit_test_node(self, x: float, y: float) -> str | None:
        best_node_id = None
        best_distance = 18.0
        for node_id, node in self._nodes.items():
            node_x, node_y = self._project(node.point)
            distance = math.dist((x, y), (node_x, node_y))
            if distance <= best_distance:
                best_distance = distance
                best_node_id = node_id
        return best_node_id
