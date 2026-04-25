from unittest import TestCase

try:
    from ..models import GeoPoint, Node
    from ..solver import ExplainableVRPSolver
except ImportError:  # pragma: no cover - direct discovery from repo root or parent
    try:
        from VRP.models import GeoPoint, Node
        from VRP.solver import ExplainableVRPSolver
    except ImportError:
        from models import GeoPoint, Node
        from solver import ExplainableVRPSolver


class SolverTests(TestCase):
    def test_solver_produces_cvrp_routes_and_preserves_capacity(self) -> None:
        depots = [
            Node("depot-1", "West Hub", GeoPoint(19.0760, 72.8777), kind="depot"),
            Node("depot-2", "East Hub", GeoPoint(19.0450, 73.0200), kind="depot"),
        ]
        orders = [
            Node("o1", "Bandra", GeoPoint(19.0596, 72.8295), kind="order", demand=2.0),
            Node("o2", "Andheri", GeoPoint(19.1136, 72.8697), kind="order", demand=3.0),
            Node("o3", "Powai", GeoPoint(19.1176, 72.9060), kind="order", demand=2.0),
            Node("o4", "Vashi", GeoPoint(19.0771, 72.9987), kind="order", demand=3.0),
        ]

        result = ExplainableVRPSolver(depots, orders, vehicle_count=3, vehicle_capacity=5.0).solve()

        self.assertGreaterEqual(len(result.steps), 3)
        self.assertLessEqual(len(result.final_routes), 3)
        self.assertEqual(
            sorted(node_id for route in result.final_routes for node_id in route.node_ids if not node_id.startswith("depot-")),
            ["o1", "o2", "o3", "o4"],
        )
        for route in result.final_routes:
            self.assertLessEqual(route.load, route.capacity)
        self.assertLessEqual(result.final_distance_km, result.baseline_distance_km)

    def test_solver_keeps_single_vehicle_solution_valid(self) -> None:
        depots = [Node("depot-1", "Depot", GeoPoint(0.0, 0.0), kind="depot")]
        orders = [
            Node("o1", "A", GeoPoint(0.02, 0.01), kind="order", demand=1.0),
            Node("o2", "B", GeoPoint(0.04, 0.03), kind="order", demand=1.0),
            Node("o3", "C", GeoPoint(0.03, 0.04), kind="order", demand=1.0),
        ]

        result = ExplainableVRPSolver(depots, orders, vehicle_count=1, vehicle_capacity=5.0).solve()

        self.assertEqual(len(result.final_routes), 1)
        self.assertEqual(result.final_routes[0].node_ids[0], "depot-1")
        self.assertEqual(result.final_routes[0].node_ids[-1], "depot-1")

    def test_solver_builds_examiner_friendly_connection_steps(self) -> None:
        depots = [Node("depot-1", "Depot", GeoPoint(19.0760, 72.8777), kind="depot")]
        orders = [
            Node("o1", "Bandra", GeoPoint(19.0596, 72.8295), kind="order", demand=1.0),
            Node("o2", "Andheri", GeoPoint(19.1136, 72.8697), kind="order", demand=1.0),
            Node("o3", "Powai", GeoPoint(19.1176, 72.9060), kind="order", demand=1.0),
        ]

        result = ExplainableVRPSolver(depots, orders, vehicle_count=1, vehicle_capacity=5.0).solve()

        first_step = result.steps[0]
        self.assertEqual(first_step.title, "Start Layout")
        self.assertIsNone(first_step.chosen)
        self.assertEqual(first_step.context_routes, [])

        first_connection = result.steps[1]
        self.assertTrue(first_connection.title.startswith("Connect Depot to "))
        self.assertIsNotNone(first_connection.chosen)
        self.assertEqual(first_connection.chosen.node_ids[0], "depot-1")
        self.assertGreaterEqual(len(first_connection.alternatives), 1)
        self.assertIn("Nearest-neighbour score = direct depot-to-order distance", first_connection.detail)

        final_step = result.steps[-1]
        self.assertEqual(final_step.title, "Final Answer")
        self.assertEqual(len(final_step.context_routes), len(result.final_routes))

    def test_solver_can_use_multiple_depots(self) -> None:
        depots = [
            Node("depot-1", "West Hub", GeoPoint(19.0500, 72.8200), kind="depot"),
            Node("depot-2", "East Hub", GeoPoint(19.0700, 73.0100), kind="depot"),
        ]
        orders = [
            Node("o1", "West A", GeoPoint(19.0550, 72.8250), kind="order", demand=1.0),
            Node("o2", "West B", GeoPoint(19.0600, 72.8300), kind="order", demand=1.0),
            Node("o3", "East A", GeoPoint(19.0750, 73.0000), kind="order", demand=1.0),
            Node("o4", "East B", GeoPoint(19.0800, 73.0050), kind="order", demand=1.0),
        ]

        result = ExplainableVRPSolver(depots, orders, vehicle_count=2, vehicle_capacity=4.0).solve()

        used_depots = {route.node_ids[0] for route in result.final_routes}
        self.assertEqual(used_depots, {"depot-1", "depot-2"})

    def test_solver_does_not_seed_all_routes_from_one_depot_when_clusters_split(self) -> None:
        depots = [
            Node("depot-1", "West Hub", GeoPoint(0.0, 0.0), kind="depot"),
            Node("depot-2", "East Hub", GeoPoint(0.0, 10.0), kind="depot"),
        ]
        orders = [
            Node("o1", "West A", GeoPoint(0.0, 0.05), kind="order", demand=1.0),
            Node("o2", "West B", GeoPoint(0.0, 0.10), kind="order", demand=1.0),
            Node("o3", "East A", GeoPoint(0.0, 9.5), kind="order", demand=1.0),
            Node("o4", "East B", GeoPoint(0.0, 9.6), kind="order", demand=1.0),
        ]

        result = ExplainableVRPSolver(depots, orders, vehicle_count=2, vehicle_capacity=10.0).solve()

        self.assertEqual(len(result.final_routes), 2)
        used_depots = {route.node_ids[0] for route in result.final_routes}
        self.assertEqual(used_depots, {"depot-1", "depot-2"})
        west_route = next(route for route in result.final_routes if route.node_ids[0] == "depot-1")
        east_route = next(route for route in result.final_routes if route.node_ids[0] == "depot-2")
        self.assertEqual(sorted(node_id for node_id in west_route.node_ids if node_id.startswith("o")), ["o1", "o2"])
        self.assertEqual(sorted(node_id for node_id in east_route.node_ids if node_id.startswith("o")), ["o3", "o4"])

    def test_solver_uses_extra_vehicle_when_capacity_requires_it(self) -> None:
        depots = [Node("depot-1", "Depot", GeoPoint(19.0, 72.8), kind="depot")]
        orders = [
            Node("o1", "A", GeoPoint(19.01, 72.81), kind="order", demand=4.0),
            Node("o2", "B", GeoPoint(19.02, 72.82), kind="order", demand=4.0),
            Node("o3", "C", GeoPoint(19.03, 72.83), kind="order", demand=4.0),
        ]

        result = ExplainableVRPSolver(depots, orders, vehicle_count=3, vehicle_capacity=5.0).solve()

        self.assertEqual(len(result.final_routes), 3)

    def test_solver_can_use_fewer_than_max_vehicles_when_capacity_allows(self) -> None:
        depots = [Node("depot-1", "Depot", GeoPoint(0.0, 0.0), kind="depot")]
        orders = [
            Node("o1", "Near A", GeoPoint(0.0, 0.05), kind="order", demand=1.0),
            Node("o2", "Near B", GeoPoint(0.0, 0.1), kind="order", demand=1.0),
            Node("o3", "Far", GeoPoint(0.0, 1.0), kind="order", demand=1.0),
        ]

        result = ExplainableVRPSolver(depots, orders, vehicle_count=3, vehicle_capacity=10.0).solve()

        self.assertLess(len(result.final_routes), 3)
        self.assertEqual(
            sorted(node_id for route in result.final_routes for node_id in route.node_ids if node_id != "depot-1"),
            ["o1", "o2", "o3"],
        )

    def test_solver_rejects_demand_above_capacity(self) -> None:
        depots = [Node("depot-1", "Depot", GeoPoint(19.0, 72.8), kind="depot")]
        orders = [Node("o1", "Heavy", GeoPoint(19.01, 72.81), kind="order", demand=12.0)]

        with self.assertRaises(ValueError):
            ExplainableVRPSolver(depots, orders, vehicle_count=2, vehicle_capacity=10.0)

    def test_solver_resets_step_log_on_repeated_solve(self) -> None:
        depots = [Node("depot-1", "Depot", GeoPoint(19.0, 72.8), kind="depot")]
        orders = [
            Node("o1", "A", GeoPoint(19.02, 72.81), kind="order", demand=1.0),
            Node("o2", "B", GeoPoint(19.04, 72.83), kind="order", demand=1.0),
            Node("o3", "C", GeoPoint(19.03, 72.84), kind="order", demand=1.0),
        ]

        solver = ExplainableVRPSolver(depots, orders, vehicle_count=2, vehicle_capacity=5.0)
        first = solver.solve()
        second = solver.solve()

        self.assertEqual(len(first.steps), len(second.steps))
