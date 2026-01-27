"""
Tests for Financial Engine Module

This module tests the financial calculations including fuel costs
and labor costs for vehicle routes.
"""

import os
import sys
import pytest

# Critical: Add DLL directories for MinGW runtime
if os.name == 'nt':
    os.add_dll_directory(r"C:\mingw64\bin")
    os.add_dll_directory(os.path.abspath("build"))

from dashboard.financial_engine import FinancialEngine, RouteCost
from dashboard.fleet_composer import VehicleType


class TestFinancialEngine:
    """Test suite for financial engine functionality."""
    
    def test_financial_engine_instantiation(self):
        """Test that FinancialEngine can be instantiated."""
        engine = FinancialEngine(fuel_price_per_L=1.5, driver_hourly_wage=25.0)
        assert engine is not None
        assert engine.fuel_price_per_L == 1.5
        assert engine.driver_hourly_wage == 25.0
    
    def test_route_cost_dataclass(self):
        """Test RouteCost dataclass creation."""
        route_cost = RouteCost(
            route_id=1,
            vehicle_name="Truck A",
            distance_km=100.0,
            time_hours=2.5,
            fuel_efficiency_km_per_L=10.0,
            fuel_consumed_L=10.0,
            fuel_cost=15.0,
            labor_cost=62.5,
            total_cost=77.5
        )
        
        assert route_cost.route_id == 1
        assert route_cost.vehicle_name == "Truck A"
        assert route_cost.total_cost == 77.5
    
    def test_calculate_route_cost_basic(self):
        """Test basic route cost calculation."""
        engine = FinancialEngine(fuel_price_per_L=1.5, driver_hourly_wage=25.0)
        
        vehicle = VehicleType(
            name="Truck A",
            capacity_kg=1000.0,
            length_m=6.0,
            width_m=2.5,
            height_m=2.5,
            fuel_efficiency_km_per_L=10.0,
            count=1
        )
        
        route_cost = engine.calculate_route_cost(
            route_id=1,
            route_distance_km=100.0,
            route_time_hours=2.5,
            vehicle=vehicle
        )
        
        assert route_cost is not None
        assert route_cost.vehicle_name == "Truck A"
    
    def test_fuel_cost_formula(self):
        """Test fuel cost calculation formula: (distance / efficiency) * price."""
        engine = FinancialEngine(fuel_price_per_L=2.0, driver_hourly_wage=20.0)
        
        vehicle = VehicleType(
            name="Van",
            capacity_kg=500.0,
            length_m=4.0,
            width_m=2.0,
            height_m=2.0,
            fuel_efficiency_km_per_L=12.0,
            count=1
        )
        
        route_cost = engine.calculate_route_cost(
            route_id=1,
            route_distance_km=120.0,
            route_time_hours=3.0,
            vehicle=vehicle
        )
        
        # Expected: (120 / 12) * 2.0 = 10 * 2.0 = 20.0
        assert route_cost.fuel_consumed_L == 10.0
        assert route_cost.fuel_cost == 20.0
    
    def test_labor_cost_formula(self):
        """Test labor cost calculation formula: time * wage."""
        engine = FinancialEngine(fuel_price_per_L=1.5, driver_hourly_wage=30.0)
        
        vehicle = VehicleType(
            name="Truck B",
            capacity_kg=1500.0,
            length_m=7.0,
            width_m=2.5,
            height_m=3.0,
            fuel_efficiency_km_per_L=8.0,
            count=1
        )
        
        route_cost = engine.calculate_route_cost(
            route_id=2,
            route_distance_km=80.0,
            route_time_hours=4.0,
            vehicle=vehicle
        )
        
        # Expected: 4.0 * 30.0 = 120.0
        assert route_cost.labor_cost == 120.0
    
    def test_total_cost_composition(self):
        """Test total cost equals fuel_cost + labor_cost."""
        engine = FinancialEngine(fuel_price_per_L=1.8, driver_hourly_wage=28.0)
        
        vehicle = VehicleType(
            name="Truck C",
            capacity_kg=2000.0,
            length_m=8.0,
            width_m=2.5,
            height_m=3.0,
            fuel_efficiency_km_per_L=9.0,
            count=1
        )
        
        route_cost = engine.calculate_route_cost(
            route_id=3,
            route_distance_km=90.0,
            route_time_hours=2.0,
            vehicle=vehicle
        )
        
        # Fuel cost: (90 / 9) * 1.8 = 10 * 1.8 = 18.0
        # Labor cost: 2.0 * 28.0 = 56.0
        # Total: 18.0 + 56.0 = 74.0
        assert route_cost.fuel_cost == 18.0
        assert route_cost.labor_cost == 56.0
        assert route_cost.total_cost == 74.0
    
    def test_generate_cost_summary_empty(self):
        """Test cost summary with empty route list."""
        engine = FinancialEngine(fuel_price_per_L=1.5, driver_hourly_wage=25.0)
        
        summary = engine.generate_cost_summary([])
        
        assert summary["total_fuel_consumed_L"] == 0.0
        assert summary["total_fuel_cost"] == 0.0
        assert summary["total_labor_cost"] == 0.0
        assert summary["total_cost"] == 0.0
        assert summary["vehicle_efficiency_breakdown"] == {}
    
    def test_generate_cost_summary_single_route(self):
        """Test cost summary with single route."""
        engine = FinancialEngine(fuel_price_per_L=2.0, driver_hourly_wage=25.0)
        
        vehicle = VehicleType(
            name="Van A",
            capacity_kg=800.0,
            length_m=5.0,
            width_m=2.0,
            height_m=2.5,
            fuel_efficiency_km_per_L=15.0,
            count=1
        )
        
        route_cost = engine.calculate_route_cost(
            route_id=1,
            route_distance_km=150.0,
            route_time_hours=3.0,
            vehicle=vehicle
        )
        
        summary = engine.generate_cost_summary([route_cost])
        
        assert summary["total_fuel_consumed_L"] == 10.0
        assert summary["total_fuel_cost"] == 20.0
        assert summary["total_labor_cost"] == 75.0
        assert summary["total_cost"] == 95.0
        assert "Van A" in summary["vehicle_efficiency_breakdown"]
        assert summary["vehicle_efficiency_breakdown"]["Van A"]["fuel_efficiency_km_per_L"] == 15.0
        assert summary["vehicle_efficiency_breakdown"]["Van A"]["total_distance_km"] == 150.0
        assert summary["vehicle_efficiency_breakdown"]["Van A"]["route_count"] == 1
    
    def test_generate_cost_summary_multiple_routes(self):
        """Test cost summary with multiple routes and different vehicles."""
        engine = FinancialEngine(fuel_price_per_L=1.5, driver_hourly_wage=20.0)
        
        vehicle1 = VehicleType(
            name="Truck A",
            capacity_kg=1000.0,
            length_m=6.0,
            width_m=2.5,
            height_m=2.5,
            fuel_efficiency_km_per_L=10.0,
            count=1
        )
        
        vehicle2 = VehicleType(
            name="Van B",
            capacity_kg=600.0,
            length_m=4.5,
            width_m=2.0,
            height_m=2.0,
            fuel_efficiency_km_per_L=12.0,
            count=1
        )
        
        route_cost1 = engine.calculate_route_cost(
            route_id=1,
            route_distance_km=100.0,
            route_time_hours=2.0,
            vehicle=vehicle1
        )
        
        route_cost2 = engine.calculate_route_cost(
            route_id=2,
            route_distance_km=60.0,
            route_time_hours=1.5,
            vehicle=vehicle2
        )
        
        summary = engine.generate_cost_summary([route_cost1, route_cost2])
        
        # Route 1: fuel = 100/10 = 10L, fuel_cost = 10*1.5 = 15, labor = 2*20 = 40
        # Route 2: fuel = 60/12 = 5L, fuel_cost = 5*1.5 = 7.5, labor = 1.5*20 = 30
        # Total: fuel = 15L, fuel_cost = 22.5, labor = 70, total = 92.5
        assert summary["total_fuel_consumed_L"] == 15.0
        assert summary["total_fuel_cost"] == 22.5
        assert summary["total_labor_cost"] == 70.0
        assert summary["total_cost"] == 92.5
        
        # Check vehicle breakdown
        assert "Truck A" in summary["vehicle_efficiency_breakdown"]
        assert "Van B" in summary["vehicle_efficiency_breakdown"]
        assert summary["vehicle_efficiency_breakdown"]["Truck A"]["fuel_efficiency_km_per_L"] == 10.0
        assert summary["vehicle_efficiency_breakdown"]["Van B"]["fuel_efficiency_km_per_L"] == 12.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
