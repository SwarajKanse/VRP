"""Tkinter entrypoint for the VRP solver."""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from mini_vrp_tkinter.canvas_view import OPTIMAL_COLOR, RouteCanvas
from mini_vrp_tkinter.geo import KNOWN_LOCATIONS, RoadService
from mini_vrp_tkinter.models import AnimationRoute, GeoPoint, Node, SolveResult, SolveStep
from mini_vrp_tkinter.solver import ExplainableVRPSolver

ACCENT = "#c96a2d"
INK = "#0f172a"
SURFACE = "#f7f8fa"
PANEL = "#fbfcfd"
BLUE = "#1f4f6f"
GREEN = "#2f7f5f"


def next_order_id(existing_ids: list[str]) -> str:
    next_index = 1
    for node_id in existing_ids:
        if not node_id.startswith("order-"):
            continue
        suffix = node_id.split("-", 1)[1]
        if suffix.isdigit():
            next_index = max(next_index, int(suffix) + 1)
    return f"order-{next_index}"


class MiniVRPApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("VRP Solver")
        self.root.geometry("1480x920")
        self.root.minsize(1280, 760)
        self.root.configure(bg=SURFACE)

        self.app_dir = Path(__file__).resolve().parent
        self.road_service = RoadService(self.app_dir / "cache")
        self.depot: Node | None = None
        self.orders: list[Node] = []
        self.solution: SolveResult | None = None
        self.route_canvas: RouteCanvas | None = None
        self.polyline_canvas: RouteCanvas | None = None
        self.canvas_tabs: ttk.Notebook | None = None
        self.current_step_index = 0
        self.selected_node_id: str | None = None
        self.pin_mode = ""
        self.location_hint = "Mumbai, Maharashtra, India"
        self.show_map = tk.BooleanVar(value=False)
        self.view_mode = tk.StringVar(value="step")
        self.vehicle_count = tk.IntVar(value=2)
        self.status_text = tk.StringVar(value="Set the depot, add orders, and solve.")
        self.selection_text = tk.StringVar(value="No node selected")
        self.background_queue: queue.Queue = queue.Queue()

        self._build_styles()
        self._build_ui()
        self._load_demo_state()
        self.root.after(120, self._drain_queue)
        self.root.bind("<Delete>", lambda _event: self._remove_selected_node())

    def _build_styles(self) -> None:
        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("App.TFrame", background=SURFACE)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("Panel.TLabelframe", background=PANEL, borderwidth=0)
        style.configure("Panel.TLabelframe.Label", background=PANEL, foreground=INK, font=("Segoe UI", 10, "bold"))
        style.configure("Title.TLabel", background=PANEL, foreground=INK, font=("Segoe UI", 12, "bold"))
        style.configure("Body.TLabel", background=PANEL, foreground="#475569", font=("Segoe UI", 10))
        style.configure("Metric.TLabel", background=PANEL, foreground=INK, font=("Consolas", 11, "bold"))
        style.configure("Accent.TButton", background=ACCENT, foreground="white", font=("Segoe UI", 10, "bold"))
        style.map("Accent.TButton", background=[("active", "#b85f28")])
        style.configure("Tool.TButton", background=PANEL, foreground=INK, font=("Segoe UI", 10))
        style.configure("TEntry", fieldbackground="white", padding=6)
        style.configure("TSpinbox", fieldbackground="white", padding=4)
        style.configure("TRadiobutton", background=PANEL, foreground=INK, font=("Segoe UI", 10))
        style.configure("TCheckbutton", background=PANEL, foreground=INK, font=("Segoe UI", 10))

    def _build_ui(self) -> None:
        shell = ttk.Frame(self.root, style="App.TFrame", padding=12)
        shell.pack(fill="both", expand=True)

        header = ttk.Frame(shell, style="Panel.TFrame", padding=(14, 10))
        header.pack(fill="x", pady=(0, 10))
        ttk.Label(header, text="VRP Solver", style="Title.TLabel").pack(side="left")
        ttk.Label(header, textvariable=self.status_text, style="Body.TLabel").pack(side="right")

        body = ttk.Panedwindow(shell, orient="horizontal")
        body.pack(fill="both", expand=True)

        left = ttk.Frame(body, style="Panel.TFrame", padding=12)
        center = ttk.Frame(body, style="Panel.TFrame", padding=0)
        right = ttk.Frame(body, style="Panel.TFrame", padding=12)
        body.add(left, weight=1)
        body.add(center, weight=4)
        body.add(right, weight=2)

        self._build_left_panel(left)
        self.canvas_tabs = ttk.Notebook(center)
        self.canvas_tabs.pack(fill="both", expand=True)
        self.route_canvas = RouteCanvas(self.canvas_tabs, self.road_service, path_mode="road")
        self.route_canvas.set_click_callback(self._handle_canvas_click)
        self.canvas_tabs.add(self.route_canvas, text="Road Route")
        self.polyline_canvas = RouteCanvas(self.canvas_tabs, self.road_service, path_mode="polyline")
        self.polyline_canvas.set_click_callback(self._handle_canvas_click)
        self.canvas_tabs.add(self.polyline_canvas, text="Polyline Route")
        self._build_right_panel(right)

    def _build_left_panel(self, parent) -> None:
        config_box = ttk.LabelFrame(parent, text="Configuration", style="Panel.TLabelframe", padding=12)
        config_box.pack(fill="x", pady=(0, 12))

        ttk.Label(config_box, text="Depot Address", style="Body.TLabel").pack(anchor="w")
        self.depot_entry = ttk.Entry(config_box)
        self.depot_entry.pack(fill="x", pady=(4, 6))
        self.depot_entry.insert(0, "Mumbai Hub")
        ttk.Button(config_box, text="Set Depot", style="Accent.TButton", command=self._set_depot_from_address).pack(fill="x")
        ttk.Button(config_box, text="Place Depot With Pin", style="Tool.TButton", command=lambda: self._set_pin_mode("depot")).pack(fill="x", pady=(6, 0))

        ttk.Separator(config_box).pack(fill="x", pady=10)

        ttk.Label(config_box, text="Order Address", style="Body.TLabel").pack(anchor="w")
        self.order_entry = ttk.Entry(config_box)
        self.order_entry.pack(fill="x", pady=(4, 6))
        self.order_entry.insert(0, "Bandra Boutique")
        ttk.Button(config_box, text="Add Order", style="Accent.TButton", command=self._add_order_from_address).pack(fill="x")
        ttk.Button(config_box, text="Place Order With Pin", style="Tool.TButton", command=lambda: self._set_pin_mode("order")).pack(fill="x", pady=(6, 0))

        ttk.Separator(config_box).pack(fill="x", pady=10)
        ttk.Label(config_box, text="Vehicles", style="Body.TLabel").pack(anchor="w")
        ttk.Spinbox(config_box, from_=1, to=8, textvariable=self.vehicle_count, width=6).pack(anchor="w", pady=(4, 6))
        ttk.Button(config_box, text="Solve", style="Accent.TButton", command=self._solve).pack(fill="x", pady=(6, 0))
        ttk.Button(config_box, text="Clear Orders", style="Tool.TButton", command=self._reset_orders).pack(fill="x", pady=(6, 0))

        view_box = ttk.LabelFrame(parent, text="View", style="Panel.TLabelframe", padding=12)
        view_box.pack(fill="x", pady=(0, 12))
        ttk.Checkbutton(view_box, text="Show Map Background", variable=self.show_map, command=self._refresh_canvas).pack(anchor="w")
        ttk.Radiobutton(view_box, text="Current Step", value="step", variable=self.view_mode, command=self._refresh_canvas).pack(anchor="w")
        ttk.Radiobutton(view_box, text="Construction", value="baseline", variable=self.view_mode, command=self._refresh_canvas).pack(anchor="w")
        ttk.Radiobutton(view_box, text="Final", value="final", variable=self.view_mode, command=self._refresh_canvas).pack(anchor="w")
        ttk.Separator(view_box).pack(fill="x", pady=8)
        ttk.Label(view_box, text="Canvas Navigation", style="Body.TLabel").pack(anchor="w")
        ttk.Button(view_box, text="Zoom In", style="Tool.TButton", command=self._zoom_in_view).pack(fill="x", pady=(6, 0))
        ttk.Button(view_box, text="Zoom Out", style="Tool.TButton", command=self._zoom_out_view).pack(fill="x", pady=(6, 0))
        ttk.Button(view_box, text="Fit To Routes", style="Tool.TButton", command=self._fit_view).pack(fill="x", pady=(6, 0))
        ttk.Label(
            view_box,
            text="Drag to pan. Use the mouse wheel to zoom.",
            style="Body.TLabel",
            wraplength=220,
            justify="left",
        ).pack(anchor="w", pady=(8, 0))

        playback_box = ttk.LabelFrame(parent, text="Playback", style="Panel.TLabelframe", padding=12)
        playback_box.pack(fill="x")
        ttk.Button(playback_box, text="Previous Step", style="Tool.TButton", command=self._previous_step).pack(fill="x")
        ttk.Button(playback_box, text="Next Step", style="Tool.TButton", command=self._next_step).pack(fill="x", pady=(6, 0))
        ttk.Button(playback_box, text="Play Steps", style="Tool.TButton", command=self._play_steps).pack(fill="x", pady=(6, 0))
        ttk.Button(playback_box, text="Animate Trucks", style="Tool.TButton", command=self._animate_final).pack(fill="x", pady=(6, 0))
        ttk.Button(playback_box, text="Stop Animation", style="Tool.TButton", command=self._stop_animation).pack(fill="x", pady=(6, 0))

        orders_box = ttk.LabelFrame(parent, text="Orders", style="Panel.TLabelframe", padding=12)
        orders_box.pack(fill="both", expand=True, pady=(12, 0))
        ttk.Label(orders_box, textvariable=self.selection_text, style="Body.TLabel").pack(anchor="w", pady=(0, 8))
        self.order_list = tk.Listbox(
            orders_box,
            activestyle="none",
            borderwidth=0,
            highlightthickness=0,
            background="#ffffff",
            foreground=INK,
            font=("Segoe UI", 10),
        )
        self.order_list.pack(fill="both", expand=True)
        self.order_list.bind("<Delete>", lambda _event: self._remove_selected_order())
        self.order_list.bind("<<ListboxSelect>>", self._select_order_from_list)
        ttk.Button(orders_box, text="Remove Selected Order", style="Tool.TButton", command=self._remove_selected_order).pack(
            fill="x",
            pady=(8, 0),
        )
        ttk.Button(orders_box, text="Remove Selected Node", style="Tool.TButton", command=self._remove_selected_node).pack(
            fill="x",
            pady=(6, 0),
        )
        ttk.Button(orders_box, text="Remove Depot", style="Tool.TButton", command=self._remove_depot).pack(
            fill="x",
            pady=(6, 0),
        )

    def _build_right_panel(self, parent) -> None:
        steps_box = ttk.LabelFrame(parent, text="Connection Steps", style="Panel.TLabelframe", padding=12)
        steps_box.pack(fill="both", expand=True)

        self.step_list = tk.Listbox(
            steps_box,
            activestyle="none",
            height=14,
            borderwidth=0,
            highlightthickness=0,
            background="#ffffff",
            foreground=INK,
            font=("Segoe UI", 10),
        )
        self.step_list.pack(fill="x")
        self.step_list.bind("<<ListboxSelect>>", self._select_step)

        ttk.Label(steps_box, text="Decision", style="Title.TLabel").pack(anchor="w", pady=(12, 4))
        self.step_detail = tk.Text(
            steps_box,
            height=8,
            wrap="word",
            borderwidth=0,
            highlightthickness=0,
            background="#ffffff",
            foreground=INK,
            font=("Segoe UI", 10),
        )
        self.step_detail.pack(fill="x")

        ttk.Label(steps_box, text="Rejected Alternatives", style="Title.TLabel").pack(anchor="w", pady=(12, 4))
        self.alternative_list = tk.Listbox(
            steps_box,
            activestyle="none",
            height=8,
            borderwidth=0,
            highlightthickness=0,
            background="#ffffff",
            foreground=INK,
            font=("Segoe UI", 10),
        )
        self.alternative_list.pack(fill="x")

        summary_box = ttk.LabelFrame(parent, text="Route Summary", style="Panel.TLabelframe", padding=12)
        summary_box.pack(fill="x", pady=(12, 0))
        self.summary_text = tk.Text(
            summary_box,
            height=11,
            wrap="word",
            borderwidth=0,
            highlightthickness=0,
            background="#ffffff",
            foreground=INK,
            font=("Segoe UI", 10),
        )
        self.summary_text.pack(fill="x")

    def _load_demo_state(self) -> None:
        depot_point = KNOWN_LOCATIONS["mumbai hub"]
        self.depot = Node("depot", "Depot", depot_point, kind="depot")
        self.location_hint = "Mumbai, Maharashtra, India"
        self.selected_node_id = None
        self._update_selection_text()
        demo_orders = ["bandra boutique", "andheri medical", "powai electronics", "lower parel studio"]
        for index, name in enumerate(demo_orders, start=1):
            point = KNOWN_LOCATIONS[name]
            self.orders.append(Node(f"order-{index}", name.title(), point, kind="order"))
        self._refresh_orders()
        self._refresh_canvas()

    def _set_depot_from_address(self) -> None:
        query = self.depot_entry.get().strip()
        if not query:
            return
        self._run_background(
            f"Geocoding depot '{query}'",
            lambda: self.road_service.geocode(query, locality_hint=self.location_hint),
            self._on_depot_geocoded,
        )

    def _add_order_from_address(self) -> None:
        query = self.order_entry.get().strip()
        if not query:
            return
        self._run_background(
            f"Geocoding order '{query}'",
            lambda: self.road_service.geocode(query, locality_hint=self.location_hint),
            self._on_order_geocoded,
        )

    def _on_depot_geocoded(self, payload) -> None:
        label, point = payload
        self.depot = Node("depot", "Depot", point, kind="depot")
        self._update_location_hint(label)
        self.selected_node_id = "depot"
        self._update_selection_text()
        self.status_text.set(f"Depot set to {label}.")
        self._refresh_canvas()

    def _on_order_geocoded(self, payload) -> None:
        label, point = payload
        order = Node(self._next_order_id(), label.split(",")[0], point, kind="order")
        self.orders.append(order)
        self.selected_node_id = order.node_id
        self._update_selection_text()
        self.status_text.set(f"Added order {order.label}.")
        self._refresh_orders()
        self._refresh_canvas()

    def _handle_canvas_click(self, point: GeoPoint, node_id: str | None) -> None:
        if not self.pin_mode:
            self._select_node(node_id)
            return
        if self.pin_mode == "depot":
            self.depot = Node("depot", "Depot", point, kind="depot")
            self.selected_node_id = "depot"
            self._update_selection_text()
            self.status_text.set("Depot pinned on canvas.")
            self.pin_mode = ""
            self._refresh_canvas()
            self._run_background(
                "Reverse geocoding depot pin",
                lambda: self.road_service.reverse_geocode(point),
                self._on_depot_pin_reverse_geocoded,
                show_busy=False,
            )
            return
        label = f"Order {len(self.orders) + 1}"
        order = Node(self._next_order_id(), label, point, kind="order")
        self.orders.append(order)
        self.selected_node_id = order.node_id
        self._update_selection_text()
        self.status_text.set(f"Added {label} from canvas pin.")
        self.pin_mode = ""
        self._refresh_orders()
        self._refresh_canvas()
        self._run_background(
            "Reverse geocoding pin",
            lambda: self.road_service.reverse_geocode(point),
            lambda value, order_id=self.orders[-1].node_id: self._apply_reverse_label(order_id, value),
            show_busy=False,
        )

    def _apply_reverse_label(self, order_id: str, label: str) -> None:
        for order in self.orders:
            if order.node_id == order_id:
                order.label = label.split(",")[0]
                break
        self._refresh_orders()
        self._refresh_canvas()

    def _on_depot_pin_reverse_geocoded(self, label: str) -> None:
        self._update_location_hint(label)

    def _set_pin_mode(self, mode: str) -> None:
        self.pin_mode = mode
        self.status_text.set(f"Click the canvas to place a {mode}.")

    def _reset_orders(self) -> None:
        self.orders.clear()
        self.solution = None
        self.current_step_index = 0
        self.selected_node_id = None
        self._stop_animation()
        self._refresh_orders()
        self._refresh_step_panel()
        self._update_selection_text()
        self._refresh_canvas()
        self.status_text.set("Orders cleared.")

    def _remove_selected_order(self) -> None:
        selection = self.order_list.curselection()
        if not selection:
            return
        removed = self.orders.pop(selection[0])
        if self.selected_node_id == removed.node_id:
            self.selected_node_id = None
        self.solution = None
        self.current_step_index = 0
        self._stop_animation()
        self._refresh_orders()
        self._refresh_step_panel()
        self._update_selection_text()
        self._refresh_canvas()
        self.status_text.set(f"Removed order {removed.label}.")

    def _remove_selected_node(self) -> None:
        if self.selected_node_id is None:
            return
        if self.selected_node_id == "depot":
            self._remove_depot()
            return
        for index, order in enumerate(self.orders):
            if order.node_id == self.selected_node_id:
                self.orders.pop(index)
                self.solution = None
                self.current_step_index = 0
                self.selected_node_id = None
                self._stop_animation()
                self._refresh_orders()
                self._refresh_step_panel()
                self._update_selection_text()
                self._refresh_canvas()
                self.status_text.set(f"Removed order {order.label}.")
                return

    def _remove_depot(self) -> None:
        if self.depot is None:
            return
        self.depot = None
        self.solution = None
        self.current_step_index = 0
        self.selected_node_id = None
        self._stop_animation()
        self._refresh_step_panel()
        self._update_selection_text()
        self._refresh_canvas()
        self.status_text.set("Depot removed.")

    def _select_node(self, node_id: str | None) -> None:
        self.selected_node_id = node_id
        self._update_selection_text()
        self._sync_order_selection()
        self._refresh_canvas()

    def _select_order_from_list(self, _event) -> None:
        selection = self.order_list.curselection()
        if not selection:
            return
        self.selected_node_id = self.orders[selection[0]].node_id
        self._update_selection_text()
        self._refresh_canvas()

    def _stop_animation(self) -> None:
        for canvas in self._all_canvases():
            canvas.stop_animation()

    def _zoom_in_view(self) -> None:
        canvas = self._active_canvas()
        if canvas is not None:
            canvas.zoom_in()

    def _zoom_out_view(self) -> None:
        canvas = self._active_canvas()
        if canvas is not None:
            canvas.zoom_out()

    def _fit_view(self) -> None:
        canvas = self._active_canvas()
        if canvas is not None:
            canvas.fit_scene()

    def _solve(self) -> None:
        if self.depot is None:
            messagebox.showerror("Missing depot", "Set a depot before solving.")
            return
        if not self.orders:
            messagebox.showerror("Missing orders", "Add at least one order location.")
            return
        depot = Node(self.depot.node_id, self.depot.label, self.depot.point, kind="depot")
        orders = [Node(order.node_id, order.label, order.point, kind="order") for order in self.orders]
        vehicle_count = max(1, int(self.vehicle_count.get()))
        self._run_background(
            "Solving VRP and fetching road segments",
            lambda: self._solve_payload(depot, orders, vehicle_count),
            self._apply_solution,
        )

    def _solve_payload(self, depot: Node, orders: list[Node], vehicle_count: int):
        solver = ExplainableVRPSolver(depot, orders, vehicle_count)
        result = solver.solve()
        self.road_service.prefetch_pairs([depot] + orders)
        return result

    def _apply_solution(self, solution: SolveResult) -> None:
        self.solution = solution
        self.current_step_index = max(0, len(solution.steps) - 1)
        self.view_mode.set("step")
        self._stop_animation()
        self._refresh_step_panel()
        self._refresh_canvas()
        self.status_text.set(
            f"Final distance {solution.final_distance_km:.2f} km across {len(solution.final_routes)} vehicle route(s)."
        )

    def _refresh_orders(self) -> None:
        self.order_list.delete(0, "end")
        for order in self.orders:
            self.order_list.insert("end", order.label)
        self._sync_order_selection()

    def _refresh_step_panel(self) -> None:
        self.step_list.delete(0, "end")
        self.step_detail.delete("1.0", "end")
        self.alternative_list.delete(0, "end")
        self.summary_text.delete("1.0", "end")
        if self.solution is None:
            self.summary_text.insert("1.0", "Construction and final routes will appear after solving.")
            return
        for step in self.solution.steps:
            self.step_list.insert("end", f"{step.index}. {step.title}")
        if self.solution.steps:
            self.step_list.selection_clear(0, "end")
            self.step_list.selection_set(self.current_step_index)
            self.step_list.activate(self.current_step_index)
            self._show_step(self.solution.steps[self.current_step_index])
        self.summary_text.insert(
            "1.0",
            (
                f"Construction: {self.solution.baseline_distance_km:.2f} km\n"
                f"Final: {self.solution.final_distance_km:.2f} km\n\n"
                "Final Routes\n"
            ),
        )
        for route in self.solution.final_routes:
            self.summary_text.insert(
                "end",
                f"{route.name}: {' -> '.join(self._labels_for_ids(route.node_ids))} ({route.distance_km:.2f} km)\n",
            )

    def _show_step(self, step: SolveStep) -> None:
        self.step_detail.delete("1.0", "end")
        self.step_detail.insert("1.0", step.detail)
        self.alternative_list.delete(0, "end")
        if step.chosen is not None:
            self.alternative_list.insert("end", f"Chosen: {step.chosen.reason}")
        for alternative in step.alternatives:
            self.alternative_list.insert("end", f"Alternative: {alternative.reason}")

    def _refresh_canvas(self) -> None:
        nodes = ([self.depot] if self.depot is not None else []) + self.orders
        step = None
        baseline = []
        final = []
        if self.solution is not None:
            baseline = self.solution.baseline_routes
            final = self.solution.final_routes
            if self.solution.steps:
                step = self.solution.steps[self.current_step_index]
        for canvas in self._all_canvases():
            canvas.set_scene(
                nodes=nodes,
                show_map=bool(self.show_map.get()),
                view_mode=self.view_mode.get(),
                step=step,
                baseline_routes=baseline,
                final_routes=final,
                selected_node_id=self.selected_node_id,
            )

    def _next_step(self) -> None:
        if self.solution is None or not self.solution.steps:
            return
        self.current_step_index = min(len(self.solution.steps) - 1, self.current_step_index + 1)
        self.view_mode.set("step")
        self._refresh_step_panel()
        self._refresh_canvas()

    def _previous_step(self) -> None:
        if self.solution is None or not self.solution.steps:
            return
        self.current_step_index = max(0, self.current_step_index - 1)
        self.view_mode.set("step")
        self._refresh_step_panel()
        self._refresh_canvas()

    def _play_steps(self) -> None:
        if self.solution is None or not self.solution.steps:
            return
        self._stop_animation()
        self.view_mode.set("step")
        self.current_step_index = 0

        def advance() -> None:
            if self.solution is None:
                return
            self._refresh_step_panel()
            self._refresh_canvas()
            if self.current_step_index < len(self.solution.steps) - 1:
                self.current_step_index += 1
                self.root.after(1100, advance)

        advance()

    def _animate_final(self) -> None:
        if self.solution is None or not self.solution.final_routes:
            return
        self.view_mode.set("final")
        self._refresh_canvas()
        routes = [
            AnimationRoute(
                name=route.name,
                color=OPTIMAL_COLOR,
                node_ids=route.node_ids,
                distance_km=route.distance_km,
            )
            for route in self.solution.final_routes
        ]
        for canvas in self._all_canvases():
            canvas.start_animation(routes)

    def _select_step(self, _event) -> None:
        if self.solution is None:
            return
        selection = self.step_list.curselection()
        if not selection:
            return
        self.current_step_index = selection[0]
        self.view_mode.set("step")
        self._show_step(self.solution.steps[self.current_step_index])
        self._refresh_canvas()

    def _run_background(self, label: str, func, on_success, show_busy: bool = True) -> None:
        if show_busy:
            self.status_text.set(label)

        def runner() -> None:
            try:
                result = func()
                self.background_queue.put(("success", on_success, result))
            except Exception as exc:  # pragma: no cover - UI path
                self.background_queue.put(("error", None, str(exc)))

        threading.Thread(target=runner, daemon=True).start()

    def _drain_queue(self) -> None:
        while True:
            try:
                kind, callback, payload = self.background_queue.get_nowait()
            except queue.Empty:
                break
            if kind == "error":
                self.status_text.set(payload)
                messagebox.showerror("Operation failed", payload)
                continue
            callback(payload)
        self.root.after(120, self._drain_queue)

    def _labels_for_ids(self, node_ids: list[str]) -> list[str]:
        lookup = {"depot": "Depot"}
        lookup.update({order.node_id: order.label for order in self.orders})
        return [lookup.get(node_id, node_id) for node_id in node_ids]

    def _next_order_id(self) -> str:
        return next_order_id([order.node_id for order in self.orders])

    def _update_location_hint(self, label: str) -> None:
        parts = [part.strip() for part in label.split(",") if part.strip()]
        filtered = [part for part in parts if not any(character.isdigit() for character in part)]
        base = filtered or parts
        if not base:
            return
        if len(base) >= 4:
            self.location_hint = ", ".join(base[-4:])
            return
        if len(base) >= 3:
            self.location_hint = ", ".join(base[-3:])
            return
        self.location_hint = base[-1]

    def _update_selection_text(self) -> None:
        if self.selected_node_id is None:
            self.selection_text.set("No node selected")
            return
        if self.selected_node_id == "depot":
            self.selection_text.set("Selected: Depot")
            return
        for order in self.orders:
            if order.node_id == self.selected_node_id:
                self.selection_text.set(f"Selected: {order.label}")
                return
        self.selection_text.set("No node selected")

    def _sync_order_selection(self) -> None:
        self.order_list.selection_clear(0, "end")
        if self.selected_node_id is None:
            return
        for index, order in enumerate(self.orders):
            if order.node_id == self.selected_node_id:
                self.order_list.selection_set(index)
                self.order_list.activate(index)
                break

    def _all_canvases(self) -> list[RouteCanvas]:
        return [canvas for canvas in (self.route_canvas, self.polyline_canvas) if canvas is not None]

    def _active_canvas(self) -> RouteCanvas | None:
        if self.canvas_tabs is None:
            return self.route_canvas
        selected = self.canvas_tabs.select()
        for canvas in self._all_canvases():
            if str(canvas) == selected:
                return canvas
        return self.route_canvas


def run() -> None:
    root = tk.Tk()
    MiniVRPApp(root)
    root.mainloop()


if __name__ == "__main__":
    run()
