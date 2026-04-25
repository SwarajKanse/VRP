"""Tkinter entrypoint for the VRP solver."""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk

from canvas_view import OPTIMAL_COLOR, RouteCanvas
from geo import KNOWN_LOCATIONS, RoadService
from models import AnimationRoute, GeoPoint, Node, SolveResult, SolveStep
from solver import ExplainableVRPSolver

ACCENT = "#c96a2d"
INK = "#0f172a"
SURFACE = "#f7f8fa"
PANEL = "#fbfcfd"
BLUE = "#1f4f6f"
GREEN = "#2f7f5f"
TRUCK_COLOR = "#2563eb"


def next_order_id(existing_ids: list[str]) -> str:
    next_index = 1
    for node_id in existing_ids:
        if not node_id.startswith("order-"):
            continue
        suffix = node_id.split("-", 1)[1]
        if suffix.isdigit():
            next_index = max(next_index, int(suffix) + 1)
    return f"order-{next_index}"


def next_depot_id(existing_ids: list[str]) -> str:
    next_index = 1
    for node_id in existing_ids:
        if not node_id.startswith("depot-"):
            continue
        suffix = node_id.split("-", 1)[1]
        if suffix.isdigit():
            next_index = max(next_index, int(suffix) + 1)
    return f"depot-{next_index}"


class MiniVRPApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("VRP Solver")
        self.root.geometry("1480x920")
        self.root.minsize(1280, 760)
        self.root.configure(bg=SURFACE)

        self.app_dir = Path(__file__).resolve().parent
        self.road_service = RoadService(self.app_dir / "cache")
        self.depots: list[Node] = []
        self.orders: list[Node] = []
        self.solution: SolveResult | None = None
        self.route_canvas: RouteCanvas | None = None
        self.polyline_canvas: RouteCanvas | None = None
        self.canvas_mode = tk.StringVar(value="road")
        self.current_step_index = 0
        self.selected_node_id: str | None = None
        self.pin_mode = ""
        self.location_hint = "Mumbai, Maharashtra, India"
        self.show_map = tk.BooleanVar(value=False)
        self.view_mode = tk.StringVar(value="step")
        self.vehicle_count = tk.IntVar(value=2)
        self.vehicle_capacity = tk.DoubleVar(value=10.0)
        self.order_demand = tk.DoubleVar(value=1.0)
        self.status_text = tk.StringVar(value="Add depots, orders, set capacity, and solve.")
        self.background_queue: queue.Queue = queue.Queue()

        self._build_styles()
        self._load_assets()
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
        style.configure("Tab.TButton", background=PANEL, foreground=INK, font=("Segoe UI", 10), padding=(14, 8))
        style.map("Tab.TButton", background=[("active", "#eef2f7")])
        style.configure("TabActive.TButton", background="#e8eef4", foreground=BLUE, font=("Segoe UI", 10, "bold"), padding=(14, 8))
        style.configure("Pin.TButton", background=PANEL, foreground=INK, padding=4)
        style.map("Pin.TButton", background=[("active", "#eef2f7")])
        style.configure("PinActive.TButton", background="#f4dccb", foreground=ACCENT, padding=4)

    def _load_assets(self) -> None:
        self._pin_source = tk.PhotoImage(file=str(self.app_dir / "assets" / "location.png"))
        self.pin_button_icon = self._pin_source.subsample(20, 20)
        self.pin_cursor_icon = self._pin_source.subsample(14, 14)

    def _build_ui(self) -> None:
        shell = ttk.Frame(self.root, style="App.TFrame", padding=12)
        shell.pack(fill="both", expand=True)

        header = ttk.Frame(shell, style="Panel.TFrame", padding=(14, 10))
        header.pack(fill="x", pady=(0, 10))
        ttk.Label(header, text="VRP Solver", style="Title.TLabel").pack(side="left")
        ttk.Label(header, textvariable=self.status_text, style="Body.TLabel").pack(side="right")

        body = ttk.Panedwindow(shell, orient="horizontal")
        body.pack(fill="both", expand=True)

        left_shell = ttk.Frame(body, style="Panel.TFrame")
        center = ttk.Frame(body, style="Panel.TFrame", padding=0)
        right = ttk.Frame(body, style="Panel.TFrame", padding=12)
        body.add(left_shell, weight=1)
        body.add(center, weight=4)
        body.add(right, weight=2)

        left = ttk.Frame(left_shell, style="Panel.TFrame", padding=12)
        left.pack(fill="both", expand=True)
        self._build_left_panel(left)
        canvas_header = ttk.Frame(center, style="Panel.TFrame", padding=(10, 8, 10, 0))
        canvas_header.pack(fill="x")
        tab_bar = ttk.Frame(canvas_header, style="Panel.TFrame")
        tab_bar.pack(fill="x")
        self.road_tab_button = ttk.Button(tab_bar, text="Road Route", style="TabActive.TButton", command=lambda: self._show_canvas("road"))
        self.road_tab_button.pack(side="left")
        self.polyline_tab_button = ttk.Button(tab_bar, text="Polyline Route", style="Tab.TButton", command=lambda: self._show_canvas("polyline"))
        self.polyline_tab_button.pack(side="left", padx=(4, 0))
        ttk.Checkbutton(
            tab_bar,
            text="Show Map Background",
            variable=self.show_map,
            command=self._refresh_canvas,
        ).pack(side="right")

        canvas_host = ttk.Frame(center, style="Panel.TFrame")
        canvas_host.pack(fill="both", expand=True)
        canvas_host.columnconfigure(0, weight=1)
        canvas_host.rowconfigure(0, weight=1)
        self.route_canvas = RouteCanvas(canvas_host, self.road_service, path_mode="road")
        self.route_canvas.set_click_callback(self._handle_canvas_click)
        self.route_canvas.set_pin_cursor(None, enabled=False)
        self.route_canvas.grid(row=0, column=0, sticky="nsew")
        self.polyline_canvas = RouteCanvas(canvas_host, self.road_service, path_mode="polyline")
        self.polyline_canvas.set_click_callback(self._handle_canvas_click)
        self.polyline_canvas.set_pin_cursor(None, enabled=False)
        self.polyline_canvas.grid(row=0, column=0, sticky="nsew")
        self._show_canvas("road")
        self._build_right_panel(right)

    def _build_left_panel(self, parent) -> None:
        config_box = ttk.LabelFrame(parent, text="Configuration", style="Panel.TLabelframe", padding=12)
        config_box.pack(fill="x", pady=(0, 12))

        ttk.Label(config_box, text="Depot Address", style="Body.TLabel").pack(anchor="w")
        self.depot_entry = ttk.Entry(config_box)
        self.depot_entry.pack(fill="x", pady=(4, 6))
        depot_actions = ttk.Frame(config_box, style="Panel.TFrame")
        depot_actions.pack(fill="x")
        self.add_depot_button = ttk.Button(depot_actions, text="Add Depot", style="Accent.TButton", command=self._add_depot_from_address)
        self.add_depot_button.pack(side="left", fill="x", expand=True)
        self.depot_pin_button = ttk.Button(
            depot_actions,
            image=self.pin_button_icon,
            style="Pin.TButton",
            command=lambda: self._set_pin_mode("depot"),
        )
        self.depot_pin_button.pack(side="left", padx=(6, 0))

        ttk.Separator(config_box).pack(fill="x", pady=10)

        ttk.Label(config_box, text="Order Address", style="Body.TLabel").pack(anchor="w")
        self.order_entry = ttk.Entry(config_box)
        self.order_entry.pack(fill="x", pady=(4, 6))
        order_actions = ttk.Frame(config_box, style="Panel.TFrame")
        order_actions.pack(fill="x")
        self.add_order_button = ttk.Button(order_actions, text="Add Order", style="Accent.TButton", command=self._add_order_from_address)
        self.add_order_button.pack(side="left", fill="x", expand=True)
        self.order_pin_button = ttk.Button(
            order_actions,
            image=self.pin_button_icon,
            style="Pin.TButton",
            command=lambda: self._set_pin_mode("order"),
        )
        self.order_pin_button.pack(side="left", padx=(6, 0))

        ttk.Separator(config_box).pack(fill="x", pady=10)
        vehicle_row = ttk.Frame(config_box, style="Panel.TFrame")
        vehicle_row.pack(fill="x", pady=(2, 6))
        ttk.Label(vehicle_row, text="Vehicles", style="Body.TLabel").pack(side="left")
        ttk.Spinbox(vehicle_row, from_=1, to=8, textvariable=self.vehicle_count, width=6).pack(side="left", padx=(8, 16))
        ttk.Label(vehicle_row, text="Capacity", style="Body.TLabel").pack(side="left")
        ttk.Spinbox(vehicle_row, from_=1.0, to=999.0, increment=1.0, textvariable=self.vehicle_capacity, width=8).pack(side="left", padx=(8, 0))
        ttk.Button(config_box, text="Solve", style="Accent.TButton", command=self._solve).pack(fill="x", pady=(6, 0))
        ttk.Button(config_box, text="Clear Orders", style="Tool.TButton", command=self._reset_orders).pack(fill="x", pady=(6, 0))

        playback_box = ttk.LabelFrame(parent, text="Playback", style="Panel.TLabelframe", padding=12)
        playback_box.pack(fill="x")
        ttk.Button(playback_box, text="Play Steps", style="Tool.TButton", command=self._play_steps).pack(fill="x", pady=(6, 0))
        ttk.Button(playback_box, text="Animate Trucks", style="Tool.TButton", command=self._animate_final).pack(fill="x", pady=(6, 0))

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
        self.depots = [
            Node("depot-1", "Mumbai Hub", depot_point, kind="depot"),
            Node("depot-2", "Navi Mumbai Hub", GeoPoint(19.0330, 73.0297), kind="depot"),
        ]
        self.location_hint = "Mumbai, Maharashtra, India"
        self.selected_node_id = None
        demo_orders = ["bandra boutique", "andheri medical", "powai electronics", "lower parel studio"]
        for index, name in enumerate(demo_orders, start=1):
            point = KNOWN_LOCATIONS[name]
            self.orders.append(Node(f"order-{index}", name.title(), point, kind="order", demand=2.0))
        self.order_demand.set(2.0)
        self._refresh_step_panel()
        self._refresh_canvas()

    def _add_depot_from_address(self) -> None:
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
        demand = self._prompt_order_demand()
        if demand is None:
            return
        self._run_background(
            f"Geocoding order '{query}'",
            lambda: self.road_service.geocode(query, locality_hint=self.location_hint),
            lambda payload, order_demand=demand: self._on_order_geocoded(payload, order_demand),
        )

    def _on_depot_geocoded(self, payload) -> None:
        label, point = payload
        depot = Node(self._next_depot_id(), label.split(",")[0], point, kind="depot")
        self.depots.append(depot)
        self.depot_entry.delete(0, "end")
        self._update_location_hint(label)
        self._invalidate_solution(depot.node_id, f"Added depot {depot.label}.")

    def _on_order_geocoded(self, payload, demand: float) -> None:
        label, point = payload
        order = Node(
            self._next_order_id(),
            label.split(",")[0],
            point,
            kind="order",
            demand=demand,
        )
        self.orders.append(order)
        self.order_entry.delete(0, "end")
        self.order_demand.set(demand)
        self._invalidate_solution(order.node_id, f"Added order {order.label} with demand {order.demand:.2f}.")

    def _handle_canvas_click(self, point: GeoPoint, node_id: str | None) -> None:
        if not self.pin_mode:
            self._select_node(node_id)
            return
        if self.pin_mode == "depot":
            depot = Node(self._next_depot_id(), f"Depot {len(self.depots) + 1}", point, kind="depot")
            self.depots.append(depot)
            self._set_pin_mode("")
            self._invalidate_solution(depot.node_id, f"Added depot {depot.label} from canvas pin.")
            self._run_background(
                "Reverse geocoding depot pin",
                lambda: self.road_service.reverse_geocode(point),
                lambda value, depot_id=depot.node_id: self._apply_reverse_label(depot_id, value),
                show_busy=False,
            )
            return
        demand = self._prompt_order_demand()
        if demand is None:
            self._set_pin_mode("")
            self.status_text.set("Order placement cancelled.")
            return
        label = f"Order {len(self.orders) + 1}"
        order = Node(self._next_order_id(), label, point, kind="order", demand=demand)
        self.orders.append(order)
        self.order_demand.set(demand)
        self._set_pin_mode("")
        self._invalidate_solution(order.node_id, f"Added {label} from canvas pin with demand {order.demand:.2f}.")
        self._run_background(
            "Reverse geocoding pin",
            lambda: self.road_service.reverse_geocode(point),
            lambda value, order_id=self.orders[-1].node_id: self._apply_reverse_label(order_id, value),
            show_busy=False,
        )

    def _apply_reverse_label(self, order_id: str, label: str) -> None:
        short_label = label.split(",")[0]
        for depot in self.depots:
            if depot.node_id == order_id:
                depot.label = short_label
                self._refresh_canvas()
                return
        for order in self.orders:
            if order.node_id == order_id:
                order.label = short_label
                break
        self._refresh_canvas()
        self._update_location_hint(label)

    def _set_pin_mode(self, mode: str) -> None:
        self.pin_mode = "" if mode == "" or self.pin_mode == mode else mode
        self._update_pin_controls()
        self.status_text.set(
            f"Click the canvas to place a {self.pin_mode}."
            if self.pin_mode
            else "Pin placement cancelled."
        )

    def _prompt_order_demand(self) -> float | None:
        demand = simpledialog.askfloat(
            "Order Demand",
            "Enter required capacity / demand for this order:",
            parent=self.root,
            initialvalue=float(self.order_demand.get()),
            minvalue=0.1,
        )
        if demand is None:
            return None
        return float(demand)

    def _reset_orders(self) -> None:
        self.orders.clear()
        self._invalidate_solution(status="Orders cleared.")

    def _remove_selected_node(self) -> None:
        if self.selected_node_id is None:
            return
        for index, depot in enumerate(self.depots):
            if depot.node_id == self.selected_node_id:
                self.depots.pop(index)
                self._invalidate_solution(status=f"Removed depot {depot.label}.")
                return
        for index, order in enumerate(self.orders):
            if order.node_id == self.selected_node_id:
                self.orders.pop(index)
                self._invalidate_solution(status=f"Removed order {order.label}.")
                return

    def _select_node(self, node_id: str | None) -> None:
        self.selected_node_id = node_id
        self._refresh_canvas()

    def _stop_animation(self) -> None:
        for canvas in self._all_canvases():
            canvas.stop_animation()

    def _invalidate_solution(self, selected_node_id: str | None = None, status: str | None = None) -> None:
        self.solution = None
        self.current_step_index = 0
        self.selected_node_id = selected_node_id
        self._stop_animation()
        self._refresh_step_panel()
        self._refresh_canvas()
        if status:
            self.status_text.set(status)

    def _solve(self) -> None:
        if not self.depots:
            messagebox.showerror("Missing depot", "Add at least one depot before solving.")
            return
        if not self.orders:
            messagebox.showerror("Missing orders", "Add at least one order location.")
            return
        depots = [Node(depot.node_id, depot.label, depot.point, kind="depot") for depot in self.depots]
        orders = [Node(order.node_id, order.label, order.point, kind="order", demand=order.demand) for order in self.orders]
        vehicle_count = max(1, int(self.vehicle_count.get()))
        vehicle_capacity = max(0.1, float(self.vehicle_capacity.get()))
        self._run_background(
            "Solving VRP and fetching road segments",
            lambda: self._solve_payload(depots, orders, vehicle_count, vehicle_capacity),
            self._apply_solution,
        )

    def _solve_payload(self, depots: list[Node], orders: list[Node], vehicle_count: int, vehicle_capacity: float):
        solver = ExplainableVRPSolver(depots, orders, vehicle_count, vehicle_capacity)
        result = solver.solve()
        self.road_service.prefetch_pairs(depots + orders)
        return result

    def _apply_solution(self, solution: SolveResult) -> None:
        self.solution = solution
        self.current_step_index = 0
        self.view_mode.set("step")
        self._stop_animation()
        self._refresh_step_panel()
        self._refresh_canvas()
        self.status_text.set(
            f"Solution ready. Playing {len(solution.steps)} connection steps. Final distance {solution.final_distance_km:.2f} km."
        )
        self.root.after(150, self._play_steps)

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
                (
                    f"{route.name}: {' -> '.join(self._labels_for_ids(route.node_ids))} "
                    f"({route.distance_km:.2f} km, load {route.load:.2f}/{route.capacity:.2f})\n"
                ),
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
        nodes = self.depots + self.orders
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
                name=f"Truck {index}",
                color=TRUCK_COLOR,
                node_ids=route.node_ids,
                distance_km=route.distance_km,
            )
            for index, route in enumerate(self.solution.final_routes, start=1)
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
        lookup = {}
        lookup.update({depot.node_id: depot.label for depot in self.depots})
        lookup.update({order.node_id: order.label for order in self.orders})
        return [lookup.get(node_id, node_id) for node_id in node_ids]

    def _next_order_id(self) -> str:
        return next_order_id([order.node_id for order in self.orders])

    def _next_depot_id(self) -> str:
        return next_depot_id([depot.node_id for depot in self.depots])

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

    def _show_canvas(self, mode: str) -> None:
        self.canvas_mode.set(mode)
        if mode == "road":
            self.route_canvas.tkraise()
        else:
            self.polyline_canvas.tkraise()
        self.road_tab_button.configure(style="TabActive.TButton" if mode == "road" else "Tab.TButton")
        self.polyline_tab_button.configure(style="TabActive.TButton" if mode == "polyline" else "Tab.TButton")

    def _all_canvases(self) -> list[RouteCanvas]:
        return [canvas for canvas in (self.route_canvas, self.polyline_canvas) if canvas is not None]

    def _update_pin_controls(self) -> None:
        depot_active = self.pin_mode == "depot"
        order_active = self.pin_mode == "order"
        self.depot_pin_button.configure(style="PinActive.TButton" if depot_active else "Pin.TButton")
        self.order_pin_button.configure(style="PinActive.TButton" if order_active else "Pin.TButton")
        for canvas in self._all_canvases():
            canvas.set_pin_cursor(self.pin_cursor_icon if self.pin_mode else None, enabled=bool(self.pin_mode))


def run() -> None:
    root = tk.Tk()
    MiniVRPApp(root)
    root.mainloop()


if __name__ == "__main__":
    run()
