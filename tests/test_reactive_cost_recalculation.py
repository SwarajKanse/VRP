"""
Test reactive cost recalculation functionality

This test verifies that:
1. calculate_fleet_metrics() is called with current cost parameters
2. Calculations update when cost parameters change
3. Changing parameters does not trigger solver re-run

Requirements: 2.5
"""

import os
import sys

# Critical: Add DLL directories for MinGW runtime
os.add_dll_directory(r"C:\mingw64\bin")
os.add_dll_directory(os.path.abspath("build"))

import pytest
import pandas as pd
from typing import List


# Import functions from dashboard
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'dashboard'))
from app import (
    calculate_fleet_metrics,
    calculate_route_metrics,
    RouteMetrics,
    FleetMetrics
)


def test_cost_parameter_independence():
    """
    Test that changing cost parameters produces different costs
    but identical distance and duration values
    
    This verifies that cost calculations are independent of the solver
    and can be recalculated without re-running the solver.
    
    Requirements: 2.5
    """
    # Create sample data
    df = pd.DataFrame([
        {'id': 0, 'lat': 19.065, 'lon': 72.835, 'demand': 0, 'start_window': 0, 'end_window': 600, 'service_time': 0},
        {'id': 1, 'lat': 19.070, 'lon': 72.840, 'demand': 5, 'start_window': 60, 'end_window': 180, 'service_time': 10},
        {'id': 2, 'lat': 19.075, 'lon': 72.845, 'demand': 3, 'start_window': 120, 'end_window': 240, 'service_time': 10},
    ])
    
    # Create sample routes (depot -> customer 1 -> customer 2 -> depot)
    routes = [[0, 1, 2, 0]]
    
    # Create sample time matrix (in minutes)
    time_matrix = [
        [0, 10, 20, 0],
        [10, 0, 10, 10],
        [20, 10, 0, 20],
        [0, 10, 20, 0]
    ]
    
    # First set of cost parameters
    fuel_price_1 = 100.0
    vehicle_mileage_1 = 10.0
    driver_wage_1 = 500.0
    
    # Calculate metrics with first set of parameters
    fleet_metrics_1, route_metrics_1 = calculate_fleet_metrics(
        routes=routes,
        df=df,
        time_matrix=time_matrix,
        fuel_price=fuel_price_1,
        vehicle_mileage=vehicle_mileage_1,
        driver_wage=driver_wage_1
    )
    
    # Second set of cost parameters (different values)
    fuel_price_2 = 150.0  # 50% increase
    vehicle_mileage_2 = 12.0  # 20% increase
    driver_wage_2 = 600.0  # 20% increase
    
    # Calculate metrics with second set of parameters
    fleet_metrics_2, route_metrics_2 = calculate_fleet_metrics(
        routes=routes,
        df=df,
        time_matrix=time_matrix,
        fuel_price=fuel_price_2,
        vehicle_mileage=vehicle_mileage_2,
        driver_wage=driver_wage_2
    )
    
    # Verify that distance and duration are IDENTICAL (independent of cost parameters)
    assert fleet_metrics_1.total_distance_km == fleet_metrics_2.total_distance_km, \
        "Distance should be identical regardless of cost parameters"
    
    assert fleet_metrics_1.total_duration_hours == fleet_metrics_2.total_duration_hours, \
        "Duration should be identical regardless of cost parameters"
    
    # Verify that costs are DIFFERENT (dependent on cost parameters)
    assert fleet_metrics_1.total_fuel_cost != fleet_metrics_2.total_fuel_cost, \
        "Fuel cost should change when fuel price or mileage changes"
    
    assert fleet_metrics_1.total_labor_cost != fleet_metrics_2.total_labor_cost, \
        "Labor cost should change when driver wage changes"
    
    assert fleet_metrics_1.total_cost != fleet_metrics_2.total_cost, \
        "Total cost should change when cost parameters change"
    
    # Verify that costs increased as expected (higher fuel price and wage)
    assert fleet_metrics_2.total_cost > fleet_metrics_1.total_cost, \
        "Total cost should increase with higher cost parameters"
    
    print("✅ Cost parameter independence verified:")
    print(f"   Distance (both): {fleet_metrics_1.total_distance_km:.2f} km")
    print(f"   Duration (both): {fleet_metrics_1.total_duration_hours:.2f} hrs")
    print(f"   Cost (params 1): ₹{fleet_metrics_1.total_cost:.2f}")
    print(f"   Cost (params 2): ₹{fleet_metrics_2.total_cost:.2f}")


def test_cost_recalculation_without_solver():
    """
    Test that cost calculations can be performed multiple times
    with different parameters without calling the solver
    
    This simulates the Streamlit reactive behavior where changing
    a cost parameter input triggers recalculation but not solver re-run.
    
    Requirements: 2.5
    """
    # Create sample data
    df = pd.DataFrame([
        {'id': 0, 'lat': 19.065, 'lon': 72.835, 'demand': 0, 'start_window': 0, 'end_window': 600, 'service_time': 0},
        {'id': 1, 'lat': 19.070, 'lon': 72.840, 'demand': 5, 'start_window': 60, 'end_window': 180, 'service_time': 10},
    ])
    
    # Create sample routes (simulating solver output)
    routes = [[0, 1, 0]]
    
    # Create sample time matrix (simulating solver output)
    time_matrix = [
        [0, 10, 0],
        [10, 0, 10],
        [0, 10, 0]
    ]
    
    # Simulate multiple cost parameter changes (like user adjusting sliders)
    cost_scenarios = [
        {'fuel_price': 80.0, 'vehicle_mileage': 12.0, 'driver_wage': 400.0},
        {'fuel_price': 100.0, 'vehicle_mileage': 10.0, 'driver_wage': 500.0},
        {'fuel_price': 120.0, 'vehicle_mileage': 8.0, 'driver_wage': 600.0},
    ]
    
    results = []
    
    # Calculate metrics for each scenario WITHOUT calling solver
    for scenario in cost_scenarios:
        fleet_metrics, route_metrics = calculate_fleet_metrics(
            routes=routes,  # Same routes (no solver re-run)
            df=df,
            time_matrix=time_matrix,  # Same time matrix (no solver re-run)
            fuel_price=scenario['fuel_price'],
            vehicle_mileage=scenario['vehicle_mileage'],
            driver_wage=scenario['driver_wage']
        )
        results.append(fleet_metrics)
    
    # Verify that all scenarios have identical distance and duration
    for i in range(1, len(results)):
        assert results[i].total_distance_km == results[0].total_distance_km, \
            "Distance should be identical across all scenarios"
        assert results[i].total_duration_hours == results[0].total_duration_hours, \
            "Duration should be identical across all scenarios"
    
    # Verify that costs are different across scenarios
    costs = [r.total_cost for r in results]
    assert len(set(costs)) == len(costs), \
        "Each scenario should produce different total cost"
    
    # Verify that costs increase with higher fuel price and lower mileage
    assert costs[2] > costs[1] > costs[0], \
        "Cost should increase with higher fuel price, lower mileage, and higher wage"
    
    print("✅ Cost recalculation without solver verified:")
    print(f"   Scenario 1 cost: ₹{costs[0]:.2f}")
    print(f"   Scenario 2 cost: ₹{costs[1]:.2f}")
    print(f"   Scenario 3 cost: ₹{costs[2]:.2f}")


def test_calculate_fleet_metrics_uses_current_parameters():
    """
    Test that calculate_fleet_metrics() correctly uses the provided
    cost parameters for all calculations
    
    Requirements: 2.5
    """
    # Create sample data
    df = pd.DataFrame([
        {'id': 0, 'lat': 19.065, 'lon': 72.835, 'demand': 0, 'start_window': 0, 'end_window': 600, 'service_time': 0},
        {'id': 1, 'lat': 19.070, 'lon': 72.840, 'demand': 5, 'start_window': 60, 'end_window': 180, 'service_time': 10},
    ])
    
    routes = [[0, 1, 0]]
    
    # Simple time matrix: 10 minutes each way
    time_matrix = [
        [0, 10, 0],
        [10, 0, 10],
        [0, 10, 0]
    ]
    
    # Known cost parameters
    fuel_price = 100.0  # ₹100 per liter
    vehicle_mileage = 10.0  # 10 km per liter
    driver_wage = 500.0  # ₹500 per hour
    
    # Calculate metrics
    fleet_metrics, route_metrics = calculate_fleet_metrics(
        routes=routes,
        df=df,
        time_matrix=time_matrix,
        fuel_price=fuel_price,
        vehicle_mileage=vehicle_mileage,
        driver_wage=driver_wage
    )
    
    # Manually calculate expected values
    # Distance: (10 min / 60) * 40 km/h = 6.67 km (one way), total = 13.33 km
    expected_distance = (10 / 60) * 40 * 2  # Round trip
    
    # Duration calculation:
    # - Depot (customer 0): arrival=0, waiting=0, service=0, departure=0
    # - Customer 1: arrival=10 (travel from depot), waiting=50 (start_window=60), service=10, departure=70
    # - Depot return: arrival=80 (travel from customer 1), waiting=0, service=0
    # Total duration: 80 minutes = 1.33 hours
    expected_duration = 80 / 60  # 1.33 hours
    
    # Fuel cost: (13.33 km / 10 km/L) * 100 ₹/L = 133.3 ₹
    expected_fuel_cost = (expected_distance / vehicle_mileage) * fuel_price
    
    # Labor cost: 1.33 hours * 500 ₹/hour = 666.67 ₹
    expected_labor_cost = expected_duration * driver_wage
    
    # Total cost: 133.3 + 666.67 = 800 ₹
    expected_total_cost = expected_fuel_cost + expected_labor_cost
    
    # Verify calculations (with small tolerance for floating point)
    assert abs(fleet_metrics.total_distance_km - expected_distance) < 0.01, \
        f"Distance mismatch: expected {expected_distance:.2f}, got {fleet_metrics.total_distance_km:.2f}"
    
    assert abs(fleet_metrics.total_duration_hours - expected_duration) < 0.01, \
        f"Duration mismatch: expected {expected_duration:.2f}, got {fleet_metrics.total_duration_hours:.2f}"
    
    assert abs(fleet_metrics.total_fuel_cost - expected_fuel_cost) < 0.01, \
        f"Fuel cost mismatch: expected {expected_fuel_cost:.2f}, got {fleet_metrics.total_fuel_cost:.2f}"
    
    assert abs(fleet_metrics.total_labor_cost - expected_labor_cost) < 0.01, \
        f"Labor cost mismatch: expected {expected_labor_cost:.2f}, got {fleet_metrics.total_labor_cost:.2f}"
    
    assert abs(fleet_metrics.total_cost - expected_total_cost) < 0.01, \
        f"Total cost mismatch: expected {expected_total_cost:.2f}, got {fleet_metrics.total_cost:.2f}"
    
    print("✅ calculate_fleet_metrics() uses current parameters correctly:")
    print(f"   Distance: {fleet_metrics.total_distance_km:.2f} km (expected: {expected_distance:.2f})")
    print(f"   Duration: {fleet_metrics.total_duration_hours:.2f} hrs (expected: {expected_duration:.2f})")
    print(f"   Fuel cost: ₹{fleet_metrics.total_fuel_cost:.2f} (expected: ₹{expected_fuel_cost:.2f})")
    print(f"   Labor cost: ₹{fleet_metrics.total_labor_cost:.2f} (expected: ₹{expected_labor_cost:.2f})")
    print(f"   Total cost: ₹{fleet_metrics.total_cost:.2f} (expected: ₹{expected_total_cost:.2f})")


if __name__ == "__main__":
    # Run tests
    test_cost_parameter_independence()
    print()
    test_cost_recalculation_without_solver()
    print()
    test_calculate_fleet_metrics_uses_current_parameters()
    print()
    print("✅ All reactive cost recalculation tests passed!")
