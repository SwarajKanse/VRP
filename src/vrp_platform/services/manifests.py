"""Manifest generation and packing summaries."""

from __future__ import annotations

import csv
import io

from vrp_platform.domain.entities import (
    Order,
    RoutePlan,
    Vehicle,
    WarehouseLoadInstruction,
    WarehouseRoutePlan,
)


class ManifestService:
    """Generate dispatcher/customer/driver manifest exports."""

    def generate_manifests(self, routes: list[RoutePlan], orders: list[Order]) -> dict[str, str]:
        order_lookup = {order.id: order for order in orders}
        exports: dict[str, str] = {}
        for route in routes:
            buffer = io.StringIO()
            writer = csv.writer(buffer)
            writer.writerow(
                [
                    "route_id",
                    "vehicle_id",
                    "stop_id",
                    "sequence",
                    "order_id",
                    "customer_name",
                    "arrival_minute",
                    "departure_minute",
                    "weight_kg",
                    "volume_m3",
                    "fragile",
                    "orientation_locked",
                ]
            )
            for stop in route.stops:
                order = order_lookup[stop.order_id]
                writer.writerow(
                    [
                        route.route_id,
                        route.vehicle_id,
                        stop.stop_id,
                        stop.sequence,
                        order.external_ref,
                        order.customer_name,
                        round(stop.arrival_minute, 2),
                        round(stop.departure_minute, 2),
                        order.demand_kg,
                        order.volume_m3,
                        order.fragile,
                        order.orientation_locked,
                    ]
                )
            exports[route.route_id] = buffer.getvalue()
        return exports

    def generate_warehouse_plans(
        self,
        routes: list[RoutePlan],
        orders: list[Order],
        vehicles: list[Vehicle],
    ) -> list[WarehouseRoutePlan]:
        order_lookup = {order.id: order for order in orders}
        vehicle_lookup = {vehicle.id: vehicle for vehicle in vehicles}
        plans: list[WarehouseRoutePlan] = []
        for route in routes:
            vehicle = vehicle_lookup.get(route.vehicle_id)
            if vehicle is None:
                continue
            route_orders = [order_lookup[stop.order_id] for stop in route.stops if stop.order_id in order_lookup]
            total_weight = sum(order.demand_kg for order in route_orders)
            total_volume = sum(order.volume_m3 for order in route_orders)
            instructions: list[WarehouseLoadInstruction] = []
            for load_sequence, stop in enumerate(reversed(route.stops), start=1):
                order = order_lookup.get(stop.order_id)
                if order is None:
                    continue
                notes = []
                if order.fragile:
                    notes.append("Fragile")
                if order.orientation_locked:
                    notes.append("This side up")
                if order.priority >= 2:
                    notes.append("Priority stop")
                instructions.append(
                    WarehouseLoadInstruction(
                        load_sequence=load_sequence,
                        stop_sequence=stop.sequence,
                        order_id=order.id,
                        external_ref=order.external_ref,
                        customer_name=order.customer_name,
                        slot_label=self._slot_label(load_sequence),
                        notes=", ".join(notes) if notes else "Standard load",
                    )
                )
            plans.append(
                WarehouseRoutePlan(
                    route_id=route.route_id,
                    vehicle_id=route.vehicle_id,
                    vehicle_name=vehicle.name,
                    vehicle_category=vehicle.category,
                    total_weight_kg=total_weight,
                    total_volume_m3=total_volume,
                    utilization_pct=max(
                        total_weight / max(vehicle.capacity_kg, 1.0),
                        total_volume / max(vehicle.capacity_volume_m3, 1.0),
                    )
                    * 100.0,
                    instructions=instructions,
                )
            )
        return plans

    def _slot_label(self, load_sequence: int) -> str:
        zones = ["rear-right", "rear-left", "mid-right", "mid-left", "front-right", "front-left"]
        return zones[(load_sequence - 1) % len(zones)]
