"""Order repository."""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from vrp_platform.domain.entities import Order
from vrp_platform.domain.enums import OrderStatus
from vrp_platform.repos.models import OrderRecord


class OrderRepository:
    """CRUD access for orders."""

    _SORT_COLUMNS = {
        "external_ref": OrderRecord.external_ref,
        "customer_name": OrderRecord.customer_name,
        "priority": OrderRecord.priority,
        "demand_kg": OrderRecord.demand_kg,
        "window_start": OrderRecord.time_window_start_min,
        "status": OrderRecord.status,
    }

    def __init__(self, session: Session):
        self.session = session

    def list_orders(
        self,
        statuses: Iterable[OrderStatus] | None = None,
        search_term: str = "",
        sort_by: str = "external_ref",
        descending: bool = False,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Order]:
        stmt = self._base_query(statuses, search_term)
        order_column = self._SORT_COLUMNS.get(sort_by, OrderRecord.external_ref)
        stmt = stmt.order_by(
            order_column.desc() if descending else order_column.asc(),
            OrderRecord.external_ref.asc(),
        )
        if offset > 0:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        rows = self.session.scalars(stmt).all()
        return [self._to_domain(row) for row in rows]

    def count_orders(
        self,
        statuses: Iterable[OrderStatus] | None = None,
        search_term: str = "",
    ) -> int:
        stmt = self._base_query(statuses, search_term).with_only_columns(func.count(OrderRecord.id))
        return int(self.session.scalar(stmt) or 0)

    def _base_query(
        self,
        statuses: Iterable[OrderStatus] | None,
        search_term: str,
    ):
        stmt = select(OrderRecord)
        if statuses is not None:
            stmt = stmt.where(OrderRecord.status.in_(list(statuses)))
        normalized = search_term.strip()
        if normalized:
            like_term = f"%{normalized.lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(OrderRecord.external_ref).like(like_term),
                    func.lower(OrderRecord.customer_name).like(like_term),
                    func.lower(OrderRecord.address).like(like_term),
                )
            )
        return stmt

    def get_orders(self, order_ids: list[str]) -> list[Order]:
        if not order_ids:
            return []
        rows = self.session.scalars(select(OrderRecord).where(OrderRecord.id.in_(order_ids))).all()
        return [self._to_domain(row) for row in rows]

    def get_order_by_external_ref(self, external_ref: str) -> Order | None:
        stmt = select(OrderRecord).where(OrderRecord.external_ref == external_ref)
        row = self.session.scalars(stmt).first()
        return self._to_domain(row) if row is not None else None

    def upsert_orders(self, orders: list[Order]) -> list[Order]:
        for order in orders:
            row = self.session.get(OrderRecord, order.id)
            if row is None:
                row = self.session.scalars(
                    select(OrderRecord).where(OrderRecord.external_ref == order.external_ref)
                ).first()
            payload = {
                "external_ref": order.external_ref,
                "customer_name": order.customer_name,
                "latitude": order.latitude,
                "longitude": order.longitude,
                "demand_kg": order.demand_kg,
                "volume_m3": order.volume_m3,
                "service_time_min": order.service_time_min,
                "time_window_start_min": order.time_window_start_min,
                "time_window_end_min": order.time_window_end_min,
                "address": order.address,
                "priority": order.priority,
                "fragile": order.fragile,
                "orientation_locked": order.orientation_locked,
                "package_dimensions": {
                    "length_m": order.package_dimensions_m[0],
                    "width_m": order.package_dimensions_m[1],
                    "height_m": order.package_dimensions_m[2],
                },
                "status": order.status,
            }
            if row is None:
                row = OrderRecord(id=order.id, **payload)
                self.session.add(row)
            else:
                order.id = row.id
                for key, value in payload.items():
                    setattr(row, key, value)
        self.session.flush()
        return orders

    def update_status(self, order_id: str, status: OrderStatus, route_plan_id: str | None = None) -> None:
        row = self.session.get(OrderRecord, order_id)
        if row is None:
            return
        row.status = status
        row.route_plan_id = route_plan_id
        self.session.flush()

    def _to_domain(self, row: OrderRecord) -> Order:
        dimensions = row.package_dimensions or {}
        return Order(
            id=row.id,
            external_ref=row.external_ref,
            customer_name=row.customer_name,
            latitude=row.latitude,
            longitude=row.longitude,
            demand_kg=row.demand_kg,
            volume_m3=row.volume_m3,
            service_time_min=row.service_time_min,
            time_window_start_min=row.time_window_start_min,
            time_window_end_min=row.time_window_end_min,
            address=row.address,
            priority=row.priority,
            fragile=row.fragile,
            orientation_locked=row.orientation_locked,
            package_dimensions_m=(
                dimensions.get("length_m", 0.4),
                dimensions.get("width_m", 0.3),
                dimensions.get("height_m", 0.3),
            ),
            status=row.status,
        )
