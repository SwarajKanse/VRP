"""Execution and customer update services."""

from __future__ import annotations

from vrp_platform.domain.entities import DeliveryEvent, SolveResponse
from vrp_platform.domain.enums import DeliveryEventType, OrderStatus
from vrp_platform.repos.events import EventRepository
from vrp_platform.repos.orders import OrderRepository


class ExecutionService:
    """Persist execution events and publish customer updates."""

    def __init__(self, order_repo: OrderRepository, event_repo: EventRepository):
        self.order_repo = order_repo
        self.event_repo = event_repo

    def publish_customer_updates(self, response: SolveResponse) -> int:
        count = 0
        for route in response.routes:
            for stop in route.stops:
                message = (
                    f"Order {stop.order_id} is planned on {route.route_id} "
                    f"with ETA {stop.arrival_minute:.0f} minutes."
                )
                self.event_repo.add_customer_event(stop.order_id, message, {"route_id": route.route_id})
                count += 1
        return count

    def record_delivery_event(self, event: DeliveryEvent) -> None:
        self.event_repo.add_delivery_event(event)
        if event.event_type == DeliveryEventType.DELIVERED:
            self.order_repo.update_status(event.order_id, OrderStatus.DELIVERED)
        elif event.event_type == DeliveryEventType.FAILED_ATTEMPT:
            self.order_repo.update_status(event.order_id, OrderStatus.FAILED)
        else:
            self.order_repo.update_status(event.order_id, OrderStatus.IN_TRANSIT)

