"""
Fleet Composer Module for VRP Solver

This module manages vehicle fleet configuration including fuel efficiency
parameters for cost calculations.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class VehicleType:
    """Represents a vehicle type with capacity and fuel efficiency."""
    name: str
    capacity_kg: float
    length_m: float
    width_m: float
    height_m: float
    fuel_efficiency_km_per_L: float
    count: int


class FleetComposer:
    """Manages vehicle fleet configuration."""
    
    def __init__(self):
        self.vehicle_types: List[VehicleType] = []
    
    def add_vehicle_type(self, name: str, capacity_kg: float, 
                        length_m: float, width_m: float, height_m: float,
                        fuel_efficiency_km_per_L: float, count: int) -> None:
        """Add a vehicle type with fuel efficiency."""
        vehicle = VehicleType(
            name=name,
            capacity_kg=capacity_kg,
            length_m=length_m,
            width_m=width_m,
            height_m=height_m,
            fuel_efficiency_km_per_L=fuel_efficiency_km_per_L,
            count=count
        )
        self.vehicle_types.append(vehicle)
    
    def get_vehicle_by_name(self, name: str) -> Optional[VehicleType]:
        """Retrieve vehicle type by name."""
        for vehicle in self.vehicle_types:
            if vehicle.name == name:
                return vehicle
        return None
