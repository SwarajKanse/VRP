from pathlib import Path

from vrp_platform.bootstrap import bootstrap_platform
from vrp_platform.config import PlatformSettings
from vrp_platform.domain.entities import DeliveryEvent
from vrp_platform.domain.enums import DeliveryEventType, ObjectiveMode


MANIFEST = b"""order_id,customer_name,lat,lon,weight_kg,length_m,width_m,height_m,service_time_min,window_start_min,window_end_min,address,priority,fragile,orientation_locked
SO-2001,Bandra Boutique,19.0596,72.8295,150,1.10,0.80,0.50,15,540,660,Hill Road Bandra,2,false,false
SO-2002,Andheri Medical,19.1136,72.8697,220,1.20,0.80,0.60,20,570,720,Veera Desai Road Andheri,2,true,false
"""

HEAVY_MANIFEST = b"""order_id,customer_name,lat,lon,weight_kg,length_m,width_m,height_m,service_time_min,window_start_min,window_end_min,address,priority,fragile,orientation_locked
SO-2999,Heavy Load,19.1136,72.8697,5000,1.20,0.80,0.60,20,570,720,Andheri,2,false,false
"""


def _settings(tmp_path: Path) -> PlatformSettings:
    return PlatformSettings(
        database_url=f"sqlite+pysqlite:///{tmp_path / 'platform.db'}",
        seed_demo_data=True,
    )


def test_platform_app_supports_dispatcher_customer_and_driver_flows(tmp_path: Path):
    app = bootstrap_platform(_settings(tmp_path))

    orders, warnings = app.ingest_manifest(MANIFEST)

    assert len(orders) == 2
    assert warnings == []

    response = app.solve_plan(app.build_solve_request(ObjectiveMode.COST))
    published = app.publish_customer_updates(response)
    snapshot = app.dispatcher_snapshot()

    assert response.routes
    assert published == 2
    assert snapshot.recent_runs[0].run_id == response.run_id
    assert snapshot.routes
    assert snapshot.map_routes
    assert snapshot.warehouse_plans
    assert snapshot.traffic_incidents

    first_route_id = snapshot.routes[0].route_id
    app.assign_driver(first_route_id, app.settings.driver_demo_id, "dispatcher")

    shipment = app.find_shipment("SO-2001")

    assert shipment is not None
    assert shipment.route_id is not None
    assert shipment.customer_events
    assert shipment.path_points
    assert shipment.navigation_url

    driver_route = app.driver_route(app.settings.driver_demo_id)

    assert driver_route is not None
    assert driver_route.route_id == first_route_id
    assert driver_route.stops
    assert driver_route.path_points
    assert driver_route.navigation_url

    app.record_delivery_event(
        DeliveryEvent(
            event_id="evt-test-1",
            order_id=driver_route.stops[0].order_id,
            driver_id=app.settings.driver_demo_id,
            event_type=DeliveryEventType.DELIVERED,
            occurred_at=shipment.customer_events[0].occurred_at,
            notes="Delivered in test",
        )
    )

    updated_shipment = app.find_shipment(driver_route.stops[0].external_ref)

    assert updated_shipment is not None
    assert updated_shipment.order.status.value == "delivered"
    assert updated_shipment.delivery_events


def test_dispatcher_snapshot_persists_solve_issues(tmp_path: Path):
    app = bootstrap_platform(_settings(tmp_path))
    app.ingest_manifest(HEAVY_MANIFEST)

    response = app.solve_plan(app.build_solve_request(ObjectiveMode.COST))
    snapshot = app.dispatcher_snapshot()

    assert response.routes == []
    assert response.unassigned_orders
    assert snapshot.issues
    assert snapshot.issues[0].code == "CAPACITY_EXCEEDED"


def test_dispatcher_snapshot_supports_filters_and_paging(tmp_path: Path):
    app = bootstrap_platform(_settings(tmp_path))
    app.ingest_manifest(MANIFEST)

    snapshot = app.dispatcher_snapshot(
        search_term="SO-2001",
        page=1,
        page_size=1,
    )

    assert snapshot.total_order_count >= 2
    assert snapshot.pending_order_count >= 2
    assert snapshot.filtered_order_count == 1
    assert snapshot.order_page == 1
    assert snapshot.order_page_size == 1
    assert len(snapshot.orders) == 1
    assert snapshot.orders[0].external_ref == "SO-2001"
