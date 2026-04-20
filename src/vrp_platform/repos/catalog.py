"""Catalog repository for depots, vehicles, and shifts."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from vrp_platform.domain.entities import Depot, Shift, Vehicle
from vrp_platform.repos.models import DepotRecord, ShiftRecord, VehicleRecord


class CatalogRepository:
    """Read catalog entities required for planning."""

    def __init__(self, session: Session):
        self.session = session

    def list_depots(self) -> list[Depot]:
        rows = self.session.scalars(select(DepotRecord).order_by(DepotRecord.name)).all()
        return [
            Depot(
                id=row.id,
                name=row.name,
                latitude=row.latitude,
                longitude=row.longitude,
                address=row.address,
            )
            for row in rows
        ]

    def list_vehicles(self) -> list[Vehicle]:
        rows = self.session.scalars(select(VehicleRecord).order_by(VehicleRecord.name)).all()
        return [
            Vehicle(
                id=row.id,
                name=row.name,
                capacity_kg=row.capacity_kg,
                capacity_volume_m3=row.capacity_volume_m3,
                depot_id=row.depot_id,
                average_speed_kmh=row.average_speed_kmh,
                category=row.category,
                max_shift_minutes=row.max_shift_minutes,
                cost_per_km=row.cost_per_km,
                labor_cost_per_hour=row.labor_cost_per_hour,
                emissions_kg_per_km=row.emissions_kg_per_km,
                energy_type=row.energy_type,
                fuel_consumption_per_km=row.fuel_consumption_per_km,
                energy_unit_cost=row.energy_unit_cost,
                max_continuous_drive_min=row.max_continuous_drive_min,
                required_break_min=row.required_break_min,
                cargo_length_m=row.cargo_length_m,
                cargo_width_m=row.cargo_width_m,
                cargo_height_m=row.cargo_height_m,
            )
            for row in rows
        ]

    def list_shifts(self) -> list[Shift]:
        rows = self.session.scalars(select(ShiftRecord).order_by(ShiftRecord.start_minute)).all()
        return [
            Shift(
                id=row.id,
                vehicle_id=row.vehicle_id,
                start_minute=row.start_minute,
                end_minute=row.end_minute,
            )
            for row in rows
        ]
