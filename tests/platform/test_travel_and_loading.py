from vrp_platform.config import PlatformSettings
from vrp_platform.domain.entities import Depot, Order, RoutePlan, Stop, TrafficIncident, Vehicle
from vrp_platform.domain.enums import VehicleCategory
from vrp_platform.integrations.travel import HaversineTravelMatrixProvider
from vrp_platform.services.manifests import ManifestService


def test_haversine_provider_applies_incident_delay():
    settings = PlatformSettings()
    provider = HaversineTravelMatrixProvider(settings)
    depot = Depot(id="depot", name="Depot", latitude=19.076, longitude=72.8777)
    vehicle = Vehicle(
        id="veh-1",
        name="Pickup",
        capacity_kg=500.0,
        capacity_volume_m3=4.0,
        depot_id="depot",
        average_speed_kmh=30.0,
        category=VehicleCategory.PICKUP_TRUCK,
    )
    order = Order(
        id="ord-1",
        external_ref="ORD-1",
        customer_name="Customer 1",
        latitude=19.096,
        longitude=72.8977,
        demand_kg=40.0,
        volume_m3=1.0,
        service_time_min=10.0,
        time_window_start_min=0.0,
        time_window_end_min=400.0,
    )
    baseline = provider.build(depot, [order], [vehicle], departure_minute=480.0)
    impacted = provider.build(
        depot,
        [order],
        [vehicle],
        departure_minute=480.0,
        traffic_incidents=[
            TrafficIncident(
                incident_id="incident-1",
                name="Road block",
                latitude=19.086,
                longitude=72.8877,
                radius_km=3.0,
                delay_multiplier=1.4,
            )
        ],
    )

    assert impacted.matrix_minutes[0][1] > baseline.matrix_minutes[0][1]
    assert impacted.metadata["active_incident_count"] == 1


def test_manifest_service_generates_reverse_load_sequence():
    route = RoutePlan(
        route_id="route-1",
        vehicle_id="veh-1",
        depot_id="depot",
        stops=[
            Stop("stop-1", "ord-1", 1, 10.0, 10.0, 20.0, 3.0, 10.0),
            Stop("stop-2", "ord-2", 2, 30.0, 30.0, 40.0, 2.0, 10.0),
        ],
    )
    vehicle = Vehicle(
        id="veh-1",
        name="Small Truck",
        capacity_kg=1000.0,
        capacity_volume_m3=8.0,
        depot_id="depot",
        average_speed_kmh=28.0,
        category=VehicleCategory.SMALL_TRUCK,
    )
    orders = [
        Order(
            id="ord-1",
            external_ref="SO-1",
            customer_name="Customer 1",
            latitude=0.1,
            longitude=0.1,
            demand_kg=100.0,
            volume_m3=1.0,
            service_time_min=10.0,
            time_window_start_min=0.0,
            time_window_end_min=500.0,
        ),
        Order(
            id="ord-2",
            external_ref="SO-2",
            customer_name="Customer 2",
            latitude=0.2,
            longitude=0.2,
            demand_kg=120.0,
            volume_m3=1.5,
            service_time_min=10.0,
            time_window_start_min=0.0,
            time_window_end_min=500.0,
            fragile=True,
        ),
    ]

    plans = ManifestService().generate_warehouse_plans([route], orders, [vehicle])

    assert len(plans) == 1
    assert [item.external_ref for item in plans[0].instructions] == ["SO-2", "SO-1"]
    assert plans[0].utilization_pct > 0
