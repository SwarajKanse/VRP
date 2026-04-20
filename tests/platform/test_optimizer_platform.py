from vrp_platform.domain.entities import ConstraintSet, Depot, Order, SolveRequest, Vehicle
from vrp_platform.domain.enums import ObjectiveMode
from vrp_platform.integrations.travel import TravelMatrixResult
from vrp_platform.optimizer.engine import RouteOptimizer


class StubTravelProvider:
    def build(
        self,
        depot,
        orders,
        vehicles,
        departure_minute,
        traffic_incidents=None,
        consider_traffic=True,
        avoid_incidents=True,
    ):
        return TravelMatrixResult(
            matrix_minutes=[
                [0.0, 50.0, 5.0],
                [50.0, 0.0, 10.0],
                [5.0, 10.0, 0.0],
            ],
            distance_km=[
                [0.0, 1.0, 5.0],
                [1.0, 0.0, 2.0],
                [5.0, 2.0, 0.0],
            ],
            metadata={"provider": "stub", "fallback_used": False},
        )


def _request() -> SolveRequest:
    depot = Depot(id="depot", name="Depot", latitude=0.0, longitude=0.0)
    vehicle = Vehicle(
        id="veh-1",
        name="Van 1",
        capacity_kg=200.0,
        capacity_volume_m3=10.0,
        depot_id="depot",
        average_speed_kmh=40.0,
    )
    orders = [
        Order(
            id="ord-1",
            external_ref="ORD-1",
            customer_name="Customer 1",
            latitude=0.1,
            longitude=0.1,
            demand_kg=20.0,
            volume_m3=1.0,
            service_time_min=10.0,
            time_window_start_min=0.0,
            time_window_end_min=200.0,
        ),
        Order(
            id="ord-2",
            external_ref="ORD-2",
            customer_name="Customer 2",
            latitude=0.2,
            longitude=0.2,
            demand_kg=25.0,
            volume_m3=1.5,
            service_time_min=10.0,
            time_window_start_min=0.0,
            time_window_end_min=30.0,
        ),
    ]
    return SolveRequest(
        depots=[depot],
        vehicles=[vehicle],
        orders=orders,
        constraints=ConstraintSet(departure_minute=0.0),
        objective=ObjectiveMode.ON_TIME,
    )


def test_optimizer_uses_travel_time_priority():
    response = RouteOptimizer(StubTravelProvider()).solve(_request())

    assert len(response.routes) == 1
    assert [stop.order_id for stop in response.routes[0].stops] == ["ord-2", "ord-1"]
    assert response.metadata["travel_provider"]["provider"] == "stub"
    assert response.routes[0].fuel_used > 0
    assert response.routes[0].total_energy_cost > 0


def test_optimizer_reports_unassigned_orders():
    request = _request()
    request.vehicles[0].capacity_kg = 10.0

    response = RouteOptimizer(StubTravelProvider()).solve(request)

    assert response.routes == []
    assert len(response.unassigned_orders) == 2
    assert {item.code for item in response.unassigned_orders} == {"CAPACITY_EXCEEDED"}


def test_optimizer_reports_dimension_mismatch():
    request = _request()
    request.orders[0].package_dimensions_m = (5.0, 2.0, 2.0)
    request.orders[0].orientation_locked = True

    response = RouteOptimizer(StubTravelProvider()).solve(request)

    assert any(issue.code == "DIMENSION_EXCEEDED" for issue in response.unassigned_orders)
