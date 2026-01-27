"""
Financial Engine Module for VRP Solver

This module calculates route costs including fuel consumption and labor costs
based on vehicle-specific fuel efficiency.
"""

from dataclasses import dataclass
from typing import List, Dict, Any
from dashboard.fleet_composer import VehicleType


@dataclass
class RouteCost:
    """Represents comprehensive cost breakdown for a route."""
    route_id: int
    vehicle_name: str
    distance_km: float
    time_hours: float
    fuel_efficiency_km_per_L: float
    fuel_consumed_L: float
    fuel_cost: float
    labor_cost: float
    total_cost: float


class FinancialEngine:
    """Calculates and reports route costs with vehicle-specific fuel efficiency."""
    
    def __init__(self, fuel_price_per_L: float, driver_hourly_wage: float):
        """
        Initialize the financial engine.
        
        Args:
            fuel_price_per_L: Price per liter of fuel
            driver_hourly_wage: Hourly wage for drivers
        """
        self.fuel_price_per_L = fuel_price_per_L
        self.driver_hourly_wage = driver_hourly_wage

    def calculate_route_cost(self, route_id: int, route_distance_km: float, 
                            route_time_hours: float, vehicle: VehicleType) -> RouteCost:
        """
        Calculate comprehensive route cost.
        
        Formula:
        - fuel_consumed_L = route_distance_km / vehicle.fuel_efficiency_km_per_L
        - fuel_cost = fuel_consumed_L * fuel_price_per_L
        - labor_cost = route_time_hours * driver_hourly_wage
        - total_cost = fuel_cost + labor_cost
        
        Args:
            route_id: Identifier for the route
            route_distance_km: Total distance of the route in kilometers
            route_time_hours: Total time for the route in hours
            vehicle: VehicleType object with fuel efficiency
            
        Returns:
            RouteCost object with complete cost breakdown
        """
        # Calculate fuel consumption
        fuel_consumed_L = route_distance_km / vehicle.fuel_efficiency_km_per_L
        
        # Calculate fuel cost
        fuel_cost = fuel_consumed_L * self.fuel_price_per_L
        
        # Calculate labor cost
        labor_cost = route_time_hours * self.driver_hourly_wage
        
        # Calculate total cost
        total_cost = fuel_cost + labor_cost
        
        return RouteCost(
            route_id=route_id,
            vehicle_name=vehicle.name,
            distance_km=route_distance_km,
            time_hours=route_time_hours,
            fuel_efficiency_km_per_L=vehicle.fuel_efficiency_km_per_L,
            fuel_consumed_L=fuel_consumed_L,
            fuel_cost=fuel_cost,
            labor_cost=labor_cost,
            total_cost=total_cost
        )

    def generate_cost_summary(self, route_costs: List[RouteCost]) -> Dict[str, Any]:
        """
        Generate summary statistics across all routes.
        
        Args:
            route_costs: List of RouteCost objects
            
        Returns:
            Dictionary containing:
            - total_fuel_consumed_L: Total fuel consumed across all routes
            - total_fuel_cost: Total fuel cost across all routes
            - total_labor_cost: Total labor cost across all routes
            - total_cost: Total cost across all routes
            - vehicle_efficiency_breakdown: Dict mapping vehicle names to their efficiency stats
        """
        if not route_costs:
            return {
                "total_fuel_consumed_L": 0.0,
                "total_fuel_cost": 0.0,
                "total_labor_cost": 0.0,
                "total_cost": 0.0,
                "vehicle_efficiency_breakdown": {}
            }
        
        # Calculate totals
        total_fuel_consumed_L = sum(rc.fuel_consumed_L for rc in route_costs)
        total_fuel_cost = sum(rc.fuel_cost for rc in route_costs)
        total_labor_cost = sum(rc.labor_cost for rc in route_costs)
        total_cost = sum(rc.total_cost for rc in route_costs)
        
        # Build vehicle efficiency breakdown
        vehicle_efficiency_breakdown = {}
        for route_cost in route_costs:
            vehicle_name = route_cost.vehicle_name
            if vehicle_name not in vehicle_efficiency_breakdown:
                vehicle_efficiency_breakdown[vehicle_name] = {
                    "fuel_efficiency_km_per_L": route_cost.fuel_efficiency_km_per_L,
                    "total_distance_km": 0.0,
                    "total_fuel_consumed_L": 0.0,
                    "route_count": 0
                }
            
            vehicle_efficiency_breakdown[vehicle_name]["total_distance_km"] += route_cost.distance_km
            vehicle_efficiency_breakdown[vehicle_name]["total_fuel_consumed_L"] += route_cost.fuel_consumed_L
            vehicle_efficiency_breakdown[vehicle_name]["route_count"] += 1
        
        return {
            "total_fuel_consumed_L": total_fuel_consumed_L,
            "total_fuel_cost": total_fuel_cost,
            "total_labor_cost": total_labor_cost,
            "total_cost": total_cost,
            "vehicle_efficiency_breakdown": vehicle_efficiency_breakdown
        }
