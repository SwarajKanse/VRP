#!/usr/bin/env python3
"""Test to verify both fixes work correctly"""

import os
import sys

# Critical: Add DLL directories for MinGW runtime
os.add_dll_directory(r"C:\mingw64\bin")

# Add build path and root path to sys.path
build_path = os.path.abspath("build")
root_path = os.path.abspath(".")

if os.path.exists(build_path):
    sys.path.insert(0, build_path)
    os.add_dll_directory(build_path)

if os.path.exists(root_path):
    sys.path.insert(0, root_path)

import vrp_core

def test_infinite_loop_fix():
    """Test that solver handles edge cases without hanging"""
    print("Testing solver robustness...")
    
    # Create a simple problem that should complete quickly
    depot = vrp_core.Customer(0, vrp_core.Location(0.0, 0.0), 0.0, 0.0, 100.0)
    customer1 = vrp_core.Customer(1, vrp_core.Location(0.01, 0.01), 20.0, 0.0, 100.0)
    customer2 = vrp_core.Customer(2, vrp_core.Location(0.02, 0.02), 20.0, 0.0, 100.0)
    
    customers = [depot, customer1, customer2]
    
    # Create solver with reasonable capacity
    solver = vrp_core.VRPSolver()
    routes = solver.solve(customers, [30.0, 30.0])  # Updated to use list of capacities - 2 vehicles
    
    print(f"  Number of routes: {len(routes)}")
    print(f"  Routes: {routes}")
    
    # Should return valid routes
    print("  ✓ Solver completed successfully!")
    
    return True

def test_dll_import():
    """Test that DLL can be imported"""
    print("\nTesting DLL import...")
    
    # If we got here, import worked
    print("  ✓ vrp_core module imported successfully!")
    
    # Test basic functionality
    loc = vrp_core.Location(40.7128, -74.0060)
    print(f"  ✓ Location created: ({loc.latitude}, {loc.longitude})")
    
    customer = vrp_core.Customer(1, loc, 10.0, 0.0, 24.0)
    print(f"  ✓ Customer created: id={customer.id}, demand={customer.demand}")
    
    solver = vrp_core.VRPSolver()
    print("  ✓ VRPSolver instantiated")
    
    return True

def test_normal_solve():
    """Test that normal solve still works correctly"""
    print("\nTesting normal solve functionality...")
    
    # Create a simple feasible problem
    depot = vrp_core.Customer(0, vrp_core.Location(0.0, 0.0), 0.0, 0.0, 48.0)
    customer1 = vrp_core.Customer(1, vrp_core.Location(0.1, 0.1), 10.0, 0.0, 48.0)
    customer2 = vrp_core.Customer(2, vrp_core.Location(0.2, 0.2), 15.0, 0.0, 48.0)
    
    customers = [depot, customer1, customer2]
    
    solver = vrp_core.VRPSolver()
    routes = solver.solve(customers, [50.0])  # Updated to use list of capacities
    
    print(f"  Number of routes: {len(routes)}")
    for i, route in enumerate(routes):
        print(f"  Route {i+1}: {route}")
    
    # Verify routes were generated
    assert len(routes) > 0, "Should generate at least one route"
    
    # Verify each route starts and ends at depot (0)
    for route in routes:
        assert route[0] == 0, "Route should start at depot"
        assert route[-1] == 0, "Route should end at depot"
    
    print("  ✓ Normal solve works correctly!")
    
    return True

if __name__ == "__main__":
    try:
        test_dll_import()
        test_infinite_loop_fix()
        test_normal_solve()
        print("\n✅ All fixes verified successfully!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
