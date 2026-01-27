"""
Test chaos mode integration with financial analytics

This test verifies that financial metrics recalculate correctly when
emergency orders are injected via chaos mode.

Requirements: 6.4
"""

import os
import sys

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Critical: Add DLL directories for MinGW runtime
os.add_dll_directory(r"C:\mingw64\bin")
os.add_dll_directory(os.path.join(project_root, "build"))

import vrp_core
import pandas as pd
import numpy as np
from typing import List


# Import functions from dashboard
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'dashboard'))
from app import (
    calculate_fleet_metrics,
    generate_demo_data,
    generate_emergency_order,
    dataframe_to_customers,
    generate_time_matrix
)


def test_chaos_mode_financial_recalculation():
    """
    Test that financial metrics recalculate when emergency orders are injected
    
    This test:
    1. Creates initial customer dataset
    2. Calculates initial financial metrics
    3. Injects emergency order
    4. Recalculates financial metrics
    5. Verifies that metrics have changed
    
    Requirements: 6.4
    """
    # Generate initial demo data
    initial_df = generate_demo_data()
    
    # Generate time matrix for initial customers
    initial_time_matrix = generate_time_matrix(initial_df)
    
    # Create simple routes for testing (2 routes)
    # Route 1: depot -> customer 1 -> customer 2 -> depot
    # Route 2: depot -> customer 3 -> customer 4 -> depot
    initial_routes = [
        [0, 1, 2, 0],
        [0, 3, 4, 0]
    ]
    
    # Cost parameters
    fuel_price = 100.0
    vehicle_mileage = 10.0
    driver_wage = 500.0
    
    # Calculate initial financial metrics
    initial_fleet_metrics, initial_route_metrics = calculate_fleet_metrics(
        routes=initial_routes,
        df=initial_df,
        time_matrix=initial_time_matrix,
        fuel_price=fuel_price,
        vehicle_mileage=vehicle_mileage,
        driver_wage=driver_wage
    )
    
    # Store initial values
    initial_total_cost = initial_fleet_metrics.total_cost
    initial_num_customers = initial_fleet_metrics.num_customers
    initial_num_routes = initial_fleet_metrics.num_routes
    
    print(f"Initial metrics:")
    print(f"  Total cost: ₹{initial_total_cost:.2f}")
    print(f"  Customers: {initial_num_customers}")
    print(f"  Routes: {initial_num_routes}")
    
    # Inject emergency order
    emergency_order = generate_emergency_order(initial_df, current_time=0.0)
    
    # Combine customers
    combined_df = pd.concat([initial_df, emergency_order], ignore_index=True)
    
    # Ensure all IDs are integers
    combined_df['id'] = combined_df['id'].astype(int)
    
    # Generate new time matrix with emergency order included
    new_time_matrix = generate_time_matrix(combined_df)
    
    # Create new routes that include the emergency order
    # For simplicity, add emergency customer to first route
    emergency_customer_id = int(emergency_order.iloc[0]['id'])
    new_routes = [
        [0, 1, 2, emergency_customer_id, 0],  # Added emergency customer
        [0, 3, 4, 0]
    ]
    
    # Calculate new financial metrics
    new_fleet_metrics, new_route_metrics = calculate_fleet_metrics(
        routes=new_routes,
        df=combined_df,
        time_matrix=new_time_matrix,
        fuel_price=fuel_price,
        vehicle_mileage=vehicle_mileage,
        driver_wage=driver_wage
    )
    
    # Store new values
    new_total_cost = new_fleet_metrics.total_cost
    new_num_customers = new_fleet_metrics.num_customers
    new_num_routes = new_fleet_metrics.num_routes
    
    print(f"\nNew metrics after emergency order:")
    print(f"  Total cost: ₹{new_total_cost:.2f}")
    print(f"  Customers: {new_num_customers}")
    print(f"  Routes: {new_num_routes}")
    print(f"  Cost increase: ₹{new_total_cost - initial_total_cost:.2f}")
    
    # Verify that metrics have changed
    assert new_num_customers == initial_num_customers + 1, \
        "Number of customers should increase by 1"
    
    assert new_total_cost > initial_total_cost, \
        "Total cost should increase when emergency order is added"
    
    assert new_num_routes == initial_num_routes, \
        "Number of routes should remain the same (emergency order added to existing route)"
    
    # Verify that the route with emergency order has higher cost
    route_0_initial_cost = initial_route_metrics[0].total_cost
    route_0_new_cost = new_route_metrics[0].total_cost
    
    assert route_0_new_cost > route_0_initial_cost, \
        "Route 0 cost should increase after adding emergency customer"
    
    print("\n✅ All assertions passed!")


def test_chaos_mode_cost_reflects_route_structure():
    """
    Test that costs reflect the new route structure after re-optimization
    
    This test verifies that when routes change structure (e.g., customer
    moved from one route to another), the financial metrics accurately
    reflect the new route assignments.
    
    Requirements: 6.4
    """
    # Create test dataset with 6 customers
    test_df = pd.DataFrame([
        {'id': 0, 'lat': 19.065, 'lon': 72.835, 'demand': 0, 'start_window': 0, 'end_window': 600, 'service_time': 0},
        {'id': 1, 'lat': 19.070, 'lon': 72.840, 'demand': 5, 'start_window': 0, 'end_window': 600, 'service_time': 10},
        {'id': 2, 'lat': 19.072, 'lon': 72.842, 'demand': 3, 'start_window': 0, 'end_window': 600, 'service_time': 10},
        {'id': 3, 'lat': 19.060, 'lon': 72.830, 'demand': 4, 'start_window': 0, 'end_window': 600, 'service_time': 10},
        {'id': 4, 'lat': 19.058, 'lon': 72.828, 'demand': 2, 'start_window': 0, 'end_window': 600, 'service_time': 10},
        {'id': 5, 'lat': 19.075, 'lon': 72.845, 'demand': 6, 'start_window': 0, 'end_window': 600, 'service_time': 10},
    ])
    
    # Generate time matrix
    time_matrix = generate_time_matrix(test_df)
    
    # Cost parameters
    fuel_price = 100.0
    vehicle_mileage = 10.0
    driver_wage = 500.0
    
    # Scenario 1: Original route structure
    routes_scenario_1 = [
        [0, 1, 2, 5, 0],  # Route 1: 3 customers
        [0, 3, 4, 0]      # Route 2: 2 customers
    ]
    
    fleet_metrics_1, route_metrics_1 = calculate_fleet_metrics(
        routes=routes_scenario_1,
        df=test_df,
        time_matrix=time_matrix,
        fuel_price=fuel_price,
        vehicle_mileage=vehicle_mileage,
        driver_wage=driver_wage
    )
    
    # Scenario 2: Re-optimized route structure (customer 5 moved to route 2)
    routes_scenario_2 = [
        [0, 1, 2, 0],     # Route 1: 2 customers
        [0, 3, 4, 5, 0]   # Route 2: 3 customers
    ]
    
    fleet_metrics_2, route_metrics_2 = calculate_fleet_metrics(
        routes=routes_scenario_2,
        df=test_df,
        time_matrix=time_matrix,
        fuel_price=fuel_price,
        vehicle_mileage=vehicle_mileage,
        driver_wage=driver_wage
    )
    
    print(f"Scenario 1 (original):")
    print(f"  Route 1 cost: ₹{route_metrics_1[0].total_cost:.2f} (3 customers)")
    print(f"  Route 2 cost: ₹{route_metrics_1[1].total_cost:.2f} (2 customers)")
    print(f"  Total cost: ₹{fleet_metrics_1.total_cost:.2f}")
    
    print(f"\nScenario 2 (re-optimized):")
    print(f"  Route 1 cost: ₹{route_metrics_2[0].total_cost:.2f} (2 customers)")
    print(f"  Route 2 cost: ₹{route_metrics_2[1].total_cost:.2f} (3 customers)")
    print(f"  Total cost: ₹{fleet_metrics_2.total_cost:.2f}")
    
    # Verify that route costs reflect the new structure
    assert route_metrics_1[0].num_customers == 3, "Scenario 1 Route 1 should have 3 customers"
    assert route_metrics_1[1].num_customers == 2, "Scenario 1 Route 2 should have 2 customers"
    
    assert route_metrics_2[0].num_customers == 2, "Scenario 2 Route 1 should have 2 customers"
    assert route_metrics_2[1].num_customers == 3, "Scenario 2 Route 2 should have 3 customers"
    
    # Verify that route 1 cost decreased (lost a customer)
    assert route_metrics_2[0].total_cost < route_metrics_1[0].total_cost, \
        "Route 1 cost should decrease when customer is removed"
    
    # Verify that route 2 cost increased (gained a customer)
    assert route_metrics_2[1].total_cost > route_metrics_1[1].total_cost, \
        "Route 2 cost should increase when customer is added"
    
    # Verify that total customers remain the same
    assert fleet_metrics_1.num_customers == fleet_metrics_2.num_customers, \
        "Total customers should remain the same across scenarios"
    
    print("\n✅ All assertions passed!")


def test_chaos_mode_uses_updated_routes():
    """
    Test that financial calculations use updated routes from chaos mode
    
    This test verifies that when chaos mode updates routes, the financial
    calculations use the new routes rather than cached old routes.
    
    Requirements: 6.4
    """
    # Create test dataset
    test_df = pd.DataFrame([
        {'id': 0, 'lat': 19.065, 'lon': 72.835, 'demand': 0, 'start_window': 0, 'end_window': 600, 'service_time': 0},
        {'id': 1, 'lat': 19.070, 'lon': 72.840, 'demand': 5, 'start_window': 0, 'end_window': 600, 'service_time': 10},
        {'id': 2, 'lat': 19.072, 'lon': 72.842, 'demand': 3, 'start_window': 0, 'end_window': 600, 'service_time': 10},
        {'id': 3, 'lat': 19.060, 'lon': 72.830, 'demand': 4, 'start_window': 0, 'end_window': 600, 'service_time': 10},
    ])
    
    # Generate time matrix
    time_matrix = generate_time_matrix(test_df)
    
    # Cost parameters
    fuel_price = 100.0
    vehicle_mileage = 10.0
    driver_wage = 500.0
    
    # Old routes (before chaos mode)
    old_routes = [
        [0, 1, 2, 0],
        [0, 3, 0]
    ]
    
    # Calculate metrics with old routes
    old_fleet_metrics, old_route_metrics = calculate_fleet_metrics(
        routes=old_routes,
        df=test_df,
        time_matrix=time_matrix,
        fuel_price=fuel_price,
        vehicle_mileage=vehicle_mileage,
        driver_wage=driver_wage
    )
    
    # New routes (after chaos mode re-optimization)
    new_routes = [
        [0, 1, 3, 0],  # Customer 3 moved to route 1
        [0, 2, 0]      # Customer 2 moved to route 2
    ]
    
    # Calculate metrics with new routes
    new_fleet_metrics, new_route_metrics = calculate_fleet_metrics(
        routes=new_routes,
        df=test_df,
        time_matrix=time_matrix,
        fuel_price=fuel_price,
        vehicle_mileage=vehicle_mileage,
        driver_wage=driver_wage
    )
    
    print(f"Old routes metrics:")
    print(f"  Route 1: {old_routes[0]} - Cost: ₹{old_route_metrics[0].total_cost:.2f}")
    print(f"  Route 2: {old_routes[1]} - Cost: ₹{old_route_metrics[1].total_cost:.2f}")
    print(f"  Total: ₹{old_fleet_metrics.total_cost:.2f}")
    
    print(f"\nNew routes metrics:")
    print(f"  Route 1: {new_routes[0]} - Cost: ₹{new_route_metrics[0].total_cost:.2f}")
    print(f"  Route 2: {new_routes[1]} - Cost: ₹{new_route_metrics[1].total_cost:.2f}")
    print(f"  Total: ₹{new_fleet_metrics.total_cost:.2f}")
    
    # Verify that metrics are different (routes changed)
    assert old_route_metrics[0].total_cost != new_route_metrics[0].total_cost, \
        "Route 1 cost should change when route structure changes"
    
    assert old_route_metrics[1].total_cost != new_route_metrics[1].total_cost, \
        "Route 2 cost should change when route structure changes"
    
    # Verify that total customers remain the same
    assert old_fleet_metrics.num_customers == new_fleet_metrics.num_customers, \
        "Total customers should remain the same"
    
    # Verify that the calculation correctly reflects the new route structure
    # Route 1 in new scenario has customers [1, 3] instead of [1, 2]
    assert new_route_metrics[0].num_customers == 2, "New route 1 should have 2 customers"
    assert new_route_metrics[1].num_customers == 1, "New route 2 should have 1 customer"
    
    print("\n✅ All assertions passed!")


if __name__ == "__main__":
    print("=" * 70)
    print("Test 1: Chaos mode financial recalculation")
    print("=" * 70)
    test_chaos_mode_financial_recalculation()
    
    print("\n" + "=" * 70)
    print("Test 2: Costs reflect route structure")
    print("=" * 70)
    test_chaos_mode_cost_reflects_route_structure()
    
    print("\n" + "=" * 70)
    print("Test 3: Uses updated routes")
    print("=" * 70)
    test_chaos_mode_uses_updated_routes()
    
    print("\n" + "=" * 70)
    print("✅ ALL TESTS PASSED!")
    print("=" * 70)
