"""
Unit tests for financial calculation functions
Tests calculate_route_metrics() and calculate_fleet_metrics()
"""

import os
import sys

# Critical: Add DLL directories for MinGW runtime
os.add_dll_directory(r"C:\mingw64\bin")
os.add_dll_directory(os.path.abspath("build"))

import pytest
import pandas as pd
from dashboard.app import (
    calculate_route_distance,
    calculate_route_duration,
    calculate_route_metrics,
    calculate_fleet_metrics,
    RouteMetrics,
    FleetMetrics
)


def test_calculate_route_metrics_normal_route():
    """Test calculate_route_metrics with a normal route"""
    # Create test data
    df = pd.DataFrame([
        {'id': 0, 'lat': 19.065, 'lon': 72.835, 'demand': 0, 'start_window': 0, 'end_window': 600, 'service_time': 0},
        {'id': 1, 'lat': 19.070, 'lon': 72.840, 'demand': 5, 'start_window': 0, 'end_window': 600, 'service_time': 10},
        {'id': 2, 'lat': 19.075, 'lon': 72.845, 'demand': 3, 'start_window': 0, 'end_window': 600, 'service_time': 10},
    ])
    
    # Create simple time matrix (in minutes)
    time_matrix = [
        [0, 10, 20],
        [10, 0, 10],
        [20, 10, 0]
    ]
    
    route = [0, 1, 2, 0]
    
    # Calculate metrics
    metrics = calculate_route_metrics(
        route=route,
        route_id=0,
        df=df,
        time_matrix=time_matrix,
        fuel_price=100.0,
        vehicle_mileage=10.0,
        driver_wage=500.0
    )
    
    # Verify metrics object
    assert isinstance(metrics, RouteMetrics)
    assert metrics.route_id == 0
    assert metrics.distance_km > 0
    assert metrics.duration_hours > 0
    assert metrics.fuel_cost > 0
    assert metrics.labor_cost > 0
    assert metrics.total_cost == metrics.fuel_cost + metrics.labor_cost
    assert metrics.num_customers == 2  # Exclude depot


def test_calculate_route_metrics_empty_route():
    """Test calculate_route_metrics with empty route (only depot)"""
    df = pd.DataFrame([
        {'id': 0, 'lat': 19.065, 'lon': 72.835, 'demand': 0, 'start_window': 0, 'end_window': 600, 'service_time': 0},
    ])
    
    time_matrix = [[0]]
    route = [0]
    
    metrics = calculate_route_metrics(
        route=route,
        route_id=0,
        df=df,
        time_matrix=time_matrix,
        fuel_price=100.0,
        vehicle_mileage=10.0,
        driver_wage=500.0
    )
    
    # Verify all metrics are zero for empty route
    assert metrics.distance_km == 0.0
    assert metrics.duration_hours == 0.0
    assert metrics.fuel_cost == 0.0
    assert metrics.labor_cost == 0.0
    assert metrics.total_cost == 0.0
    assert metrics.num_customers == 0


def test_calculate_fleet_metrics_multiple_routes():
    """Test calculate_fleet_metrics with multiple routes"""
    df = pd.DataFrame([
        {'id': 0, 'lat': 19.065, 'lon': 72.835, 'demand': 0, 'start_window': 0, 'end_window': 600, 'service_time': 0},
        {'id': 1, 'lat': 19.070, 'lon': 72.840, 'demand': 5, 'start_window': 0, 'end_window': 600, 'service_time': 10},
        {'id': 2, 'lat': 19.075, 'lon': 72.845, 'demand': 3, 'start_window': 0, 'end_window': 600, 'service_time': 10},
        {'id': 3, 'lat': 19.080, 'lon': 72.850, 'demand': 4, 'start_window': 0, 'end_window': 600, 'service_time': 10},
    ])
    
    time_matrix = [
        [0, 10, 20, 30],
        [10, 0, 10, 20],
        [20, 10, 0, 10],
        [30, 20, 10, 0]
    ]
    
    routes = [
        [0, 1, 0],
        [0, 2, 3, 0]
    ]
    
    fleet_metrics, route_metrics_list = calculate_fleet_metrics(
        routes=routes,
        df=df,
        time_matrix=time_matrix,
        fuel_price=100.0,
        vehicle_mileage=10.0,
        driver_wage=500.0
    )
    
    # Verify fleet metrics
    assert isinstance(fleet_metrics, FleetMetrics)
    assert fleet_metrics.num_routes == 2
    assert fleet_metrics.num_customers == 3  # 1 + 2 customers
    assert fleet_metrics.total_distance_km > 0
    assert fleet_metrics.total_duration_hours > 0
    assert fleet_metrics.total_cost > 0
    assert fleet_metrics.cost_per_km > 0
    assert fleet_metrics.cost_per_delivery > 0
    
    # Verify route metrics list
    assert len(route_metrics_list) == 2
    assert all(isinstance(m, RouteMetrics) for m in route_metrics_list)
    
    # Verify aggregation: fleet totals should equal sum of route metrics
    assert fleet_metrics.total_distance_km == sum(m.distance_km for m in route_metrics_list)
    assert fleet_metrics.total_duration_hours == sum(m.duration_hours for m in route_metrics_list)
    assert fleet_metrics.total_fuel_cost == sum(m.fuel_cost for m in route_metrics_list)
    assert fleet_metrics.total_labor_cost == sum(m.labor_cost for m in route_metrics_list)


def test_calculate_fleet_metrics_empty_routes():
    """Test calculate_fleet_metrics with empty routes list"""
    df = pd.DataFrame([
        {'id': 0, 'lat': 19.065, 'lon': 72.835, 'demand': 0, 'start_window': 0, 'end_window': 600, 'service_time': 0},
    ])
    
    time_matrix = [[0]]
    routes = []
    
    fleet_metrics, route_metrics_list = calculate_fleet_metrics(
        routes=routes,
        df=df,
        time_matrix=time_matrix,
        fuel_price=100.0,
        vehicle_mileage=10.0,
        driver_wage=500.0
    )
    
    # Verify all metrics are zero for empty routes
    assert fleet_metrics.total_distance_km == 0.0
    assert fleet_metrics.total_duration_hours == 0.0
    assert fleet_metrics.total_fuel_cost == 0.0
    assert fleet_metrics.total_labor_cost == 0.0
    assert fleet_metrics.total_cost == 0.0
    assert fleet_metrics.cost_per_km == 0.0
    assert fleet_metrics.cost_per_delivery == 0.0
    assert fleet_metrics.num_routes == 0
    assert fleet_metrics.num_customers == 0
    assert len(route_metrics_list) == 0


def test_cost_calculation_formulas():
    """Test that cost formulas are correct"""
    df = pd.DataFrame([
        {'id': 0, 'lat': 19.065, 'lon': 72.835, 'demand': 0, 'start_window': 0, 'end_window': 600, 'service_time': 0},
        {'id': 1, 'lat': 19.070, 'lon': 72.840, 'demand': 5, 'start_window': 0, 'end_window': 600, 'service_time': 10},
    ])
    
    time_matrix = [
        [0, 10],
        [10, 0]
    ]
    
    route = [0, 1, 0]
    
    # Known parameters
    fuel_price = 100.0
    vehicle_mileage = 10.0
    driver_wage = 500.0
    
    metrics = calculate_route_metrics(
        route=route,
        route_id=0,
        df=df,
        time_matrix=time_matrix,
        fuel_price=fuel_price,
        vehicle_mileage=vehicle_mileage,
        driver_wage=driver_wage
    )
    
    # Verify formula: fuel_cost = (distance / mileage) * price
    expected_fuel_cost = (metrics.distance_km / vehicle_mileage) * fuel_price
    assert abs(metrics.fuel_cost - expected_fuel_cost) < 0.01
    
    # Verify formula: labor_cost = duration * wage
    expected_labor_cost = metrics.duration_hours * driver_wage
    assert abs(metrics.labor_cost - expected_labor_cost) < 0.01
    
    # Verify formula: total_cost = fuel_cost + labor_cost
    assert abs(metrics.total_cost - (metrics.fuel_cost + metrics.labor_cost)) < 0.01


def test_division_by_zero_handling():
    """Test that division by zero is handled correctly"""
    df = pd.DataFrame([
        {'id': 0, 'lat': 19.065, 'lon': 72.835, 'demand': 0, 'start_window': 0, 'end_window': 600, 'service_time': 0},
    ])
    
    time_matrix = [[0]]
    routes = [[0]]  # Route with only depot
    
    fleet_metrics, route_metrics_list = calculate_fleet_metrics(
        routes=routes,
        df=df,
        time_matrix=time_matrix,
        fuel_price=100.0,
        vehicle_mileage=10.0,
        driver_wage=500.0
    )
    
    # Verify cost_per_km is 0 when distance is 0
    assert fleet_metrics.cost_per_km == 0.0
    
    # Verify cost_per_delivery is 0 when num_customers is 0
    assert fleet_metrics.cost_per_delivery == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
