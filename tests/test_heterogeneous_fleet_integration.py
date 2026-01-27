"""
Integration tests for heterogeneous fleet feature
Tests the complete workflow: Dashboard → Bindings → Solver → Dashboard
Requirements: 5.4
"""

import os
import sys
import pytest
import pandas as pd
import numpy as np

# Windows-specific DLL path fix
if os.name == 'nt':
    test_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(test_dir, '..'))
    build_path = os.path.join(project_root, 'build')
    
    # Critical: Add DLL directories for MinGW runtime
    os.add_dll_directory(r"C:\mingw64\bin")
    os.add_dll_directory(os.path.abspath(build_path))
    
    if os.path.exists(build_path):
        sys.path.insert(0, build_path)

try:
    import vrp_core
except ImportError as e:
    pytest.skip(f"vrp_core module not available: {e}", allow_module_level=True)

# Import dashboard functions
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'dashboard'))
from app import (
    flatten_and_sort_fleet,
    validate_vehicle_profiles,
    dataframe_to_customers,
    detect_unassigned_customers
)


class TestHeterogeneousFleetIntegration:
    """Integration tests for complete heterogeneous fleet workflow"""
    
    def test_homogeneous_fleet_workflow(self):
        """Test complete workflow with homogeneous fleet (all vehicles identical)"""
        # Step 1: Define fleet configuration (homogeneous)
        vehicle_profiles = [
            {"name": "Van", "capacity": 50.0, "quantity": 3}
        ]
        
        # Step 2: Validate fleet configuration
        errors = validate_vehicle_profiles(vehicle_profiles)
        assert len(errors) == 0, f"Validation errors: {errors}"
        
        # Step 3: Flatten and sort fleet
        vehicle_capacities, vehicle_map = flatten_and_sort_fleet(vehicle_profiles)
        
        # Verify fleet flattening
        assert vehicle_capacities == [50.0, 50.0, 50.0], "Capacities should be flattened"
        assert len(vehicle_map) == 3, "Should have 3 vehicles"
        assert all(v["name"] == "Van" for v in vehicle_map), "All should be Vans"
        assert all(v["capacity"] == 50.0 for v in vehicle_map), "All should have capacity 50"
        
        # Step 4: Create customer data
        df = pd.DataFrame([
            {'id': 0, 'lat': 19.065, 'lon': 72.835, 'demand': 0, 'start_window': 0, 'end_window': 600, 'service_time': 0},
            {'id': 1, 'lat': 19.070, 'lon': 72.840, 'demand': 30, 'start_window': 0, 'end_window': 600, 'service_time': 10},
            {'id': 2, 'lat': 19.075, 'lon': 72.845, 'demand': 30, 'start_window': 0, 'end_window': 600, 'service_time': 10},
            {'id': 3, 'lat': 19.080, 'lon': 72.850, 'demand': 30, 'start_window': 0, 'end_window': 600, 'service_time': 10},
        ])
        
        # Step 5: Convert to Customer objects
        customers = dataframe_to_customers(df)
        assert len(customers) == 4, "Should have 4 customers including depot"
        
        # Step 6: Solve with heterogeneous fleet API
        solver = vrp_core.VRPSolver()
        routes = solver.solve(customers, vehicle_capacities)
        
        # Step 7: Verify solution
        assert isinstance(routes, list), "Should return list of routes"
        assert len(routes) <= 3, "Should use at most 3 vehicles"
        
        # Verify capacity constraints
        for route_idx, route in enumerate(routes):
            route_demand = sum(df[df['id'] == cid]['demand'].values[0] for cid in route if cid != 0)
            assert route_demand <= vehicle_capacities[route_idx], \
                f"Route {route_idx} exceeds capacity"
        
        # Step 8: Check for unassigned customers
        unassigned = detect_unassigned_customers(routes, df)
        assert len(unassigned) == 0, "All customers should be assigned"
    
    def test_heterogeneous_fleet_workflow_two_types(self):
        """Test complete workflow with two vehicle types (Requirements 5.4)"""
        # Step 1: Define fleet configuration (heterogeneous)
        vehicle_profiles = [
            {"name": "Truck", "capacity": 50.0, "quantity": 2},
            {"name": "Van", "capacity": 20.0, "quantity": 2}
        ]
        
        # Step 2: Validate fleet configuration
        errors = validate_vehicle_profiles(vehicle_profiles)
        assert len(errors) == 0, f"Validation errors: {errors}"
        
        # Step 3: Flatten and sort fleet
        vehicle_capacities, vehicle_map = flatten_and_sort_fleet(vehicle_profiles)
        
        # Verify fleet flattening and sorting (descending order)
        assert vehicle_capacities == [50.0, 50.0, 20.0, 20.0], "Should be sorted descending"
        assert len(vehicle_map) == 4, "Should have 4 vehicles total"
        
        # Verify vehicle map structure
        assert vehicle_map[0]["name"] == "Truck" and vehicle_map[0]["instance"] == 1
        assert vehicle_map[1]["name"] == "Truck" and vehicle_map[1]["instance"] == 2
        assert vehicle_map[2]["name"] == "Van" and vehicle_map[2]["instance"] == 1
        assert vehicle_map[3]["name"] == "Van" and vehicle_map[3]["instance"] == 2
        
        # Step 4: Create customer data
        df = pd.DataFrame([
            {'id': 0, 'lat': 19.065, 'lon': 72.835, 'demand': 0, 'start_window': 0, 'end_window': 600, 'service_time': 0},
            {'id': 1, 'lat': 19.070, 'lon': 72.840, 'demand': 40, 'start_window': 0, 'end_window': 600, 'service_time': 10},
            {'id': 2, 'lat': 19.075, 'lon': 72.845, 'demand': 15, 'start_window': 0, 'end_window': 600, 'service_time': 10},
            {'id': 3, 'lat': 19.080, 'lon': 72.850, 'demand': 15, 'start_window': 0, 'end_window': 600, 'service_time': 10},
        ])
        
        # Step 5: Convert to Customer objects
        customers = dataframe_to_customers(df)
        
        # Step 6: Solve with heterogeneous fleet API
        solver = vrp_core.VRPSolver()
        routes = solver.solve(customers, vehicle_capacities)
        
        # Step 7: Verify solution
        assert len(routes) <= 4, "Should use at most 4 vehicles"
        
        # Verify each route respects its vehicle's capacity
        for route_idx, route in enumerate(routes):
            route_demand = sum(df[df['id'] == cid]['demand'].values[0] for cid in route if cid != 0)
            assert route_demand <= vehicle_capacities[route_idx], \
                f"Route {route_idx} demand {route_demand} exceeds capacity {vehicle_capacities[route_idx]}"
        
        # Step 8: Verify vehicle assignment mapping
        for route_idx, route in enumerate(routes):
            vehicle_info = vehicle_map[route_idx]
            assert "name" in vehicle_info, "Vehicle map should have name"
            assert "capacity" in vehicle_info, "Vehicle map should have capacity"
            assert "instance" in vehicle_info, "Vehicle map should have instance"
        
        # Step 9: Check for unassigned customers
        unassigned = detect_unassigned_customers(routes, df)
        assert len(unassigned) == 0, "All customers should be assigned"
    
    def test_heterogeneous_fleet_workflow_three_types(self):
        """Test complete workflow with three vehicle types (Requirements 5.4)"""
        # Step 1: Define fleet configuration (3 types)
        vehicle_profiles = [
            {"name": "Truck", "capacity": 50.0, "quantity": 1},
            {"name": "Van", "capacity": 20.0, "quantity": 2},
            {"name": "Bike", "capacity": 10.0, "quantity": 1}
        ]
        
        # Step 2: Validate and flatten
        errors = validate_vehicle_profiles(vehicle_profiles)
        assert len(errors) == 0
        
        vehicle_capacities, vehicle_map = flatten_and_sort_fleet(vehicle_profiles)
        
        # Verify sorting: [50, 20, 20, 10]
        assert vehicle_capacities == [50.0, 20.0, 20.0, 10.0], "Should be sorted descending"
        
        # Step 3: Create customer data
        df = pd.DataFrame([
            {'id': 0, 'lat': 19.065, 'lon': 72.835, 'demand': 0, 'start_window': 0, 'end_window': 600, 'service_time': 0},
            {'id': 1, 'lat': 19.070, 'lon': 72.840, 'demand': 45, 'start_window': 0, 'end_window': 600, 'service_time': 10},
            {'id': 2, 'lat': 19.075, 'lon': 72.845, 'demand': 18, 'start_window': 0, 'end_window': 600, 'service_time': 10},
            {'id': 3, 'lat': 19.080, 'lon': 72.850, 'demand': 18, 'start_window': 0, 'end_window': 600, 'service_time': 10},
            {'id': 4, 'lat': 19.085, 'lon': 72.855, 'demand': 8, 'start_window': 0, 'end_window': 600, 'service_time': 10},
        ])
        
        # Step 4: Solve
        customers = dataframe_to_customers(df)
        solver = vrp_core.VRPSolver()
        routes = solver.solve(customers, vehicle_capacities)
        
        # Step 5: Verify solution
        assert len(routes) <= 4, "Should use at most 4 vehicles"
        
        # Verify capacity constraints
        for route_idx, route in enumerate(routes):
            route_demand = sum(df[df['id'] == cid]['demand'].values[0] for cid in route if cid != 0)
            assert route_demand <= vehicle_capacities[route_idx]
        
        # Step 6: Check unassigned
        unassigned = detect_unassigned_customers(routes, df)
        assert len(unassigned) == 0, "All customers should be assigned"
    
    def test_heterogeneous_fleet_insufficient_capacity(self):
        """Test workflow when fleet capacity is insufficient (Requirements 2.5, 5.4)"""
        # Step 1: Define fleet with insufficient capacity
        vehicle_profiles = [
            {"name": "Van", "capacity": 30.0, "quantity": 2}
        ]
        
        # Step 2: Flatten and sort
        vehicle_capacities, vehicle_map = flatten_and_sort_fleet(vehicle_profiles)
        assert vehicle_capacities == [30.0, 30.0]
        
        # Step 3: Create customer data with total demand > total capacity
        df = pd.DataFrame([
            {'id': 0, 'lat': 19.065, 'lon': 72.835, 'demand': 0, 'start_window': 0, 'end_window': 600, 'service_time': 0},
            {'id': 1, 'lat': 19.070, 'lon': 72.840, 'demand': 25, 'start_window': 0, 'end_window': 600, 'service_time': 10},
            {'id': 2, 'lat': 19.075, 'lon': 72.845, 'demand': 25, 'start_window': 0, 'end_window': 600, 'service_time': 10},
            {'id': 3, 'lat': 19.080, 'lon': 72.850, 'demand': 25, 'start_window': 0, 'end_window': 600, 'service_time': 10},
        ])
        # Total demand: 75, Total capacity: 60
        
        # Step 4: Solve
        customers = dataframe_to_customers(df)
        solver = vrp_core.VRPSolver()
        routes = solver.solve(customers, vehicle_capacities)
        
        # Step 5: Verify solution
        assert len(routes) <= 2, "Should use at most 2 vehicles"
        
        # Step 6: Detect unassigned customers
        unassigned = detect_unassigned_customers(routes, df)
        
        # Should have at least one unassigned customer
        assert len(unassigned) > 0, "Should have unassigned customers due to insufficient capacity"
        
        # Verify unassigned customers are valid IDs
        all_customer_ids = set(df[df['id'] != 0]['id'].tolist())
        assert set(unassigned).issubset(all_customer_ids), "Unassigned IDs should be valid customer IDs"
    
    def test_heterogeneous_fleet_edge_case_empty_fleet(self):
        """Test edge case with empty fleet configuration"""
        # Empty fleet
        vehicle_profiles = []
        
        # Should handle gracefully
        vehicle_capacities, vehicle_map = flatten_and_sort_fleet(vehicle_profiles)
        
        assert vehicle_capacities == [], "Empty fleet should produce empty capacity list"
        assert vehicle_map == [], "Empty fleet should produce empty vehicle map"
    
    def test_heterogeneous_fleet_edge_case_single_vehicle(self):
        """Test edge case with single vehicle"""
        vehicle_profiles = [
            {"name": "Truck", "capacity": 100.0, "quantity": 1}
        ]
        
        vehicle_capacities, vehicle_map = flatten_and_sort_fleet(vehicle_profiles)
        
        assert vehicle_capacities == [100.0]
        assert len(vehicle_map) == 1
        assert vehicle_map[0]["name"] == "Truck"
        assert vehicle_map[0]["instance"] == 1
        
        # Test with customers
        df = pd.DataFrame([
            {'id': 0, 'lat': 19.065, 'lon': 72.835, 'demand': 0, 'start_window': 0, 'end_window': 600, 'service_time': 0},
            {'id': 1, 'lat': 19.070, 'lon': 72.840, 'demand': 20, 'start_window': 0, 'end_window': 600, 'service_time': 10},
            {'id': 2, 'lat': 19.075, 'lon': 72.845, 'demand': 20, 'start_window': 0, 'end_window': 600, 'service_time': 10},
        ])
        
        customers = dataframe_to_customers(df)
        solver = vrp_core.VRPSolver()
        routes = solver.solve(customers, vehicle_capacities)
        
        assert len(routes) <= 1, "Should use at most 1 vehicle"
        
        # All customers should fit in one vehicle
        if len(routes) == 1:
            visited = set(routes[0]) - {0}
            assert len(visited) == 2, "Both customers should be served"
    
    def test_heterogeneous_fleet_validation_errors(self):
        """Test validation of invalid fleet configurations"""
        # Test negative capacity
        vehicle_profiles = [
            {"name": "Van", "capacity": -10.0, "quantity": 1}
        ]
        errors = validate_vehicle_profiles(vehicle_profiles)
        assert len(errors) > 0, "Should detect negative capacity"
        assert any("positive" in err.lower() for err in errors)
        
        # Test zero capacity
        vehicle_profiles = [
            {"name": "Van", "capacity": 0.0, "quantity": 1}
        ]
        errors = validate_vehicle_profiles(vehicle_profiles)
        assert len(errors) > 0, "Should detect zero capacity"
        
        # Test negative quantity
        vehicle_profiles = [
            {"name": "Van", "capacity": 50.0, "quantity": -1}
        ]
        errors = validate_vehicle_profiles(vehicle_profiles)
        assert len(errors) > 0, "Should detect negative quantity"
        
        # Test zero quantity
        vehicle_profiles = [
            {"name": "Van", "capacity": 50.0, "quantity": 0}
        ]
        errors = validate_vehicle_profiles(vehicle_profiles)
        assert len(errors) > 0, "Should detect zero quantity"
    
    def test_heterogeneous_fleet_max_routes_constraint(self):
        """Test that solver respects maximum routes constraint (Requirements 2.4)"""
        # Define fleet with 3 vehicles
        vehicle_profiles = [
            {"name": "Van", "capacity": 20.0, "quantity": 3}
        ]
        
        vehicle_capacities, vehicle_map = flatten_and_sort_fleet(vehicle_profiles)
        
        # Create many customers
        customers_data = [
            {'id': 0, 'lat': 19.065, 'lon': 72.835, 'demand': 0, 'start_window': 0, 'end_window': 600, 'service_time': 0}
        ]
        for i in range(1, 11):  # 10 customers
            customers_data.append({
                'id': i,
                'lat': 19.065 + i * 0.005,
                'lon': 72.835 + i * 0.005,
                'demand': 5,
                'start_window': 0,
                'end_window': 600,
                'service_time': 10
            })
        
        df = pd.DataFrame(customers_data)
        customers = dataframe_to_customers(df)
        
        # Solve
        solver = vrp_core.VRPSolver()
        routes = solver.solve(customers, vehicle_capacities)
        
        # Should generate at most 3 routes (number of vehicles)
        assert len(routes) <= 3, f"Generated {len(routes)} routes but only 3 vehicles available"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
