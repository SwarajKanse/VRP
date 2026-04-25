from unittest import TestCase

from mini_vrp_tkinter.models import GeoPoint, Node
from mini_vrp_tkinter.solver import ExplainableVRPSolver


class SolverTests(TestCase):
    def test_solver_produces_steps_and_final_routes(self) -> None:
        depot = Node("depot", "Depot", GeoPoint(19.0760, 72.8777), kind="depot")
        orders = [
            Node("o1", "Bandra", GeoPoint(19.0596, 72.8295)),
            Node("o2", "Andheri", GeoPoint(19.1136, 72.8697)),
            Node("o3", "Powai", GeoPoint(19.1176, 72.9060)),
            Node("o4", "Lower Parel", GeoPoint(19.0038, 72.8295)),
        ]

        result = ExplainableVRPSolver(depot, orders, vehicle_count=2).solve()

        self.assertGreaterEqual(len(result.steps), 3)
        self.assertLessEqual(len(result.final_routes), 2)
        self.assertEqual(
            sorted(node_id for route in result.final_routes for node_id in route.node_ids if node_id != "depot"),
            ["o1", "o2", "o3", "o4"],
        )
        self.assertLessEqual(result.final_distance_km, result.baseline_distance_km)

    def test_solver_keeps_single_vehicle_solution_valid(self) -> None:
        depot = Node("depot", "Depot", GeoPoint(0.0, 0.0), kind="depot")
        orders = [
            Node("o1", "A", GeoPoint(0.02, 0.01)),
            Node("o2", "B", GeoPoint(0.04, 0.03)),
            Node("o3", "C", GeoPoint(0.03, 0.04)),
        ]

        result = ExplainableVRPSolver(depot, orders, vehicle_count=1).solve()

        self.assertEqual(len(result.final_routes), 1)
        self.assertEqual(result.final_routes[0].node_ids[0], "depot")
        self.assertEqual(result.final_routes[0].node_ids[-1], "depot")

    def test_solver_builds_examiner_friendly_connection_steps(self) -> None:
        depot = Node("depot", "Depot", GeoPoint(19.0760, 72.8777), kind="depot")
        orders = [
            Node("o1", "Bandra", GeoPoint(19.0596, 72.8295)),
            Node("o2", "Andheri", GeoPoint(19.1136, 72.8697)),
            Node("o3", "Powai", GeoPoint(19.1176, 72.9060)),
        ]

        result = ExplainableVRPSolver(depot, orders, vehicle_count=1).solve()

        expected_edge_steps = sum(len(route.node_ids) - 1 for route in result.final_routes)
        self.assertEqual(len(result.steps), expected_edge_steps + 2)

        first_step = result.steps[0]
        self.assertEqual(first_step.title, "Start Layout")
        self.assertIsNone(first_step.chosen)
        self.assertEqual(first_step.context_routes, [])

        first_connection = result.steps[1]
        self.assertTrue(first_connection.title.startswith("Connect Depot to "))
        self.assertIsNotNone(first_connection.chosen)
        self.assertEqual(first_connection.chosen.node_ids[0], "depot")
        self.assertEqual(len(first_connection.chosen.node_ids), 2)
        self.assertGreaterEqual(len(first_connection.alternatives), 1)
        self.assertIn("Nearest-neighbour score = direct edge distance", first_connection.detail)
        self.assertIn("direct edge", first_connection.alternatives[0].reason)

        final_step = result.steps[-1]
        self.assertEqual(final_step.title, "Final Answer")
        self.assertEqual(len(final_step.context_routes), len(result.final_routes))

    def test_solver_uses_extra_vehicle_when_it_reduces_completion_time(self) -> None:
        depot = Node("depot", "Depot", GeoPoint(19.0, 72.8), kind="depot")
        orders = [
            Node("o1", "West", GeoPoint(19.0, 72.7)),
            Node("o2", "East", GeoPoint(19.0, 72.9)),
            Node("o3", "North", GeoPoint(19.1, 72.8)),
            Node("o4", "South", GeoPoint(18.9, 72.8)),
        ]

        result = ExplainableVRPSolver(depot, orders, vehicle_count=2).solve()

        self.assertEqual(len(result.final_routes), 2)

    def test_solver_can_use_fewer_than_max_vehicles_when_time_does_not_improve(self) -> None:
        depot = Node("depot", "Depot", GeoPoint(0.0, 0.0), kind="depot")
        orders = [
            Node("o1", "Near A", GeoPoint(0.0, 0.05)),
            Node("o2", "Near B", GeoPoint(0.0, 0.1)),
            Node("o3", "Far", GeoPoint(0.0, 1.0)),
        ]

        result = ExplainableVRPSolver(depot, orders, vehicle_count=3).solve()

        self.assertLess(len(result.final_routes), 3)
        self.assertEqual(
            sorted(node_id for route in result.final_routes for node_id in route.node_ids if node_id != "depot"),
            ["o1", "o2", "o3"],
        )

    def test_two_opt_never_worsens_construction_distance(self) -> None:
        depot = Node("depot", "Depot", GeoPoint(19.0, 72.8), kind="depot")
        orders = [
            Node("o0", "A", GeoPoint(19.094428543090544, 72.82014024161367)),
            Node("o1", "B", GeoPoint(19.086834367090756, 72.92217739468876)),
            Node("o2", "C", GeoPoint(19.18260221064758, 72.99332127355414)),
            Node("o3", "D", GeoPoint(19.095401955310543, 72.97306198555432)),
        ]

        result = ExplainableVRPSolver(depot, orders, vehicle_count=1).solve()

        self.assertLessEqual(result.final_distance_km, result.baseline_distance_km)

    def test_solver_rejects_duplicate_order_ids(self) -> None:
        depot = Node("depot", "Depot", GeoPoint(19.0, 72.8), kind="depot")
        orders = [
            Node("dup", "A", GeoPoint(19.01, 72.81)),
            Node("dup", "B", GeoPoint(19.02, 72.82)),
        ]

        with self.assertRaises(ValueError):
            ExplainableVRPSolver(depot, orders, vehicle_count=1)

    def test_solver_resets_step_log_on_repeated_solve(self) -> None:
        depot = Node("depot", "Depot", GeoPoint(19.0, 72.8), kind="depot")
        orders = [
            Node("o1", "A", GeoPoint(19.02, 72.81)),
            Node("o2", "B", GeoPoint(19.04, 72.83)),
            Node("o3", "C", GeoPoint(19.03, 72.84)),
        ]

        solver = ExplainableVRPSolver(depot, orders, vehicle_count=1)
        first = solver.solve()
        second = solver.solve()

        self.assertEqual(len(first.steps), len(second.steps))
