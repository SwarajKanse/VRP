"""Domain enumerations."""

from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    DISPATCHER = "dispatcher"
    CUSTOMER = "customer"
    DRIVER = "driver"
    ADMIN = "admin"


class OrderStatus(str, Enum):
    PENDING = "pending"
    PLANNED = "planned"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    FAILED = "failed"


class PlanStatus(str, Enum):
    DRAFT = "draft"
    OPTIMIZED = "optimized"
    DISPATCHED = "dispatched"
    COMPLETED = "completed"


class DeliveryEventType(str, Enum):
    CHECK_IN = "check_in"
    ARRIVED = "arrived"
    DELIVERED = "delivered"
    FAILED_ATTEMPT = "failed_attempt"
    PHOTO_CAPTURED = "photo_captured"
    SIGNATURE_CAPTURED = "signature_captured"


class ObjectiveMode(str, Enum):
    DISTANCE = "distance"
    COST = "cost"
    ON_TIME = "on_time"
    EMISSIONS = "emissions"
    BALANCE = "balance"


class VehicleEnergyType(str, Enum):
    DIESEL = "diesel"
    PETROL = "petrol"
    EV = "ev"


class VehicleCategory(str, Enum):
    TWO_WHEELER = "two_wheeler"
    MINI_TEMPO = "mini_tempo"
    PICKUP_TRUCK = "pickup_truck"
    SMALL_TRUCK = "small_truck"
    LARGE_TRUCK = "large_truck"
    VAN = "van"
