"""Event and audit repositories."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from vrp_platform.domain.entities import DeliveryEvent, TimelineEvent
from vrp_platform.repos.models import AuditLogRecord, CustomerEventRecord, DeliveryEventRecord


class EventRepository:
    """Persist customer, delivery, and audit events."""

    def __init__(self, session: Session):
        self.session = session

    def add_customer_event(self, order_id: str, message: str, metadata: dict | None = None) -> None:
        self.session.add(
            CustomerEventRecord(
                id=f"cust-{uuid.uuid4().hex[:10]}",
                order_id=order_id,
                message=message,
                metadata_json=metadata or {},
            )
        )
        self.session.flush()

    def add_delivery_event(self, event: DeliveryEvent) -> None:
        self.session.add(
            DeliveryEventRecord(
                id=event.event_id,
                order_id=event.order_id,
                driver_id=event.driver_id,
                event_type=event.event_type,
                occurred_at=event.occurred_at,
                notes=event.notes,
                metadata_json=event.metadata,
            )
        )
        self.session.flush()

    def add_audit_log(
        self, actor: str, action: str, entity_type: str, entity_id: str, payload: dict | None = None
    ) -> None:
        self.session.add(
            AuditLogRecord(
                id=f"audit-{uuid.uuid4().hex[:10]}",
                actor=actor,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                payload=payload or {},
            )
        )
        self.session.flush()

    def list_customer_events(self, order_id: str) -> list[TimelineEvent]:
        stmt = (
            select(CustomerEventRecord)
            .where(CustomerEventRecord.order_id == order_id)
            .order_by(CustomerEventRecord.created_at.desc())
        )
        rows = self.session.scalars(stmt).all()
        return [
            TimelineEvent(
                event_id=row.id,
                source="customer_event",
                occurred_at=row.created_at,
                label="Customer update",
                details=row.message,
            )
            for row in rows
        ]

    def list_delivery_events(self, order_id: str) -> list[TimelineEvent]:
        stmt = (
            select(DeliveryEventRecord)
            .where(DeliveryEventRecord.order_id == order_id)
            .order_by(DeliveryEventRecord.occurred_at.desc())
        )
        rows = self.session.scalars(stmt).all()
        return [
            TimelineEvent(
                event_id=row.id,
                source="delivery_event",
                occurred_at=row.occurred_at,
                label=row.event_type.value.replace("_", " ").title(),
                details=row.notes or f"Driver {row.driver_id} recorded {row.event_type.value}.",
            )
            for row in rows
        ]
