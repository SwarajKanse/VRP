"""Manifest ingestion and validation."""

from __future__ import annotations

import csv
import io
import uuid

from vrp_platform.domain.entities import Order
from vrp_platform.repos.orders import OrderRepository


class IngestionService:
    """Parse and validate order manifests."""

    REQUIRED_COLUMNS = {
        "order_id",
        "customer_name",
        "lat",
        "lon",
        "weight_kg",
        "length_m",
        "width_m",
        "height_m",
        "service_time_min",
        "window_start_min",
        "window_end_min",
    }

    def __init__(self, order_repo: OrderRepository):
        self.order_repo = order_repo

    def ingest_manifest(self, manifest_bytes: bytes) -> list[Order]:
        reader = csv.DictReader(io.StringIO(manifest_bytes.decode("utf-8")))
        if reader.fieldnames is None:
            raise ValueError("Manifest is empty")
        missing = sorted(self.REQUIRED_COLUMNS - set(field.strip() for field in reader.fieldnames))
        if missing:
            raise ValueError(f"Manifest missing columns: {', '.join(missing)}")
        orders = [self._row_to_order(row) for row in reader]
        self.order_repo.upsert_orders(orders)
        return orders

    def validate_orders(self, orders: list[Order]) -> list[str]:
        warnings: list[str] = []
        seen_refs: set[str] = set()
        for order in orders:
            if order.external_ref in seen_refs:
                warnings.append(f"Duplicate order reference detected: {order.external_ref}")
            seen_refs.add(order.external_ref)
            if order.time_window_end_min <= order.time_window_start_min:
                warnings.append(f"Order {order.external_ref} has an invalid time window")
            if order.demand_kg <= 0 or order.volume_m3 <= 0:
                warnings.append(f"Order {order.external_ref} has non-positive demand or volume")
        return warnings

    def _row_to_order(self, row: dict[str, str]) -> Order:
        length = float(row["length_m"])
        width = float(row["width_m"])
        height = float(row["height_m"])
        volume = round(length * width * height, 6)
        return Order(
            id=row.get("id") or f"ord-{uuid.uuid4().hex[:10]}",
            external_ref=row["order_id"],
            customer_name=row["customer_name"],
            latitude=float(row["lat"]),
            longitude=float(row["lon"]),
            demand_kg=float(row["weight_kg"]),
            volume_m3=volume,
            service_time_min=float(row["service_time_min"]),
            time_window_start_min=float(row["window_start_min"]),
            time_window_end_min=float(row["window_end_min"]),
            address=row.get("address", ""),
            priority=int(row.get("priority", 1)),
            fragile=row.get("fragile", "false").strip().lower() in {"true", "1", "yes", "y"},
            orientation_locked=row.get("orientation_locked", "false").strip().lower()
            in {"true", "1", "yes", "y"},
            package_dimensions_m=(length, width, height),
        )
