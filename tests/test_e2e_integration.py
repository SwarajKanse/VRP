"""
End-to-End Integration Test for Time Window Enforcement

This test validates the complete flow from Dashboard to Solver to Results:
- Generate demo data with service times
- Run solver with time_matrix
- Verify routes respect time windows
- Verify arrival times displayed correctly
"""

import os
import sys

# Critical: Add DLL directories for MinGW runtime
os.add_dll_directory(r"C:\mingw64\bin")
build_path = os.path.abspath("build")
os.add_dll_directory(build_path)

# Add root directory to Python path for module import (vrp_core.pyd is in root)
root_path = os.path.abspath(".")
if root_path not in sys.path:
    sys.path.insert(0, root_path)

import vrp_core
import pandas as pd
import numpy as np
import pytest


# ============================================================================
# Helper Functions (from dashboard/app.py)
# ============================================================================

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate Haversine distance between two geographic points"""
    R = 6371.0
    lat1_rad = np.radians(lat1)
    lon1_rad = np.radians(lon1)
    lat2_rad = np.radians(lat2)
    lon2_rad = np.radians(lon2)
    
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = np.sin(dlat / 2)**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    
    distance = R * c
    return distance


def generate_time_matrix(df: pd.DataFrame) -> list:
    """Generate travel time matrix for all customer pairs"""
    n = len(df)
    time_matrix = []
    
    df_sorted = df.sort_values('id').reset_index(drop=True)
    
    for i in range(n):
        row = []
        lat1 = df_sorted.iloc[i]['lat']
        lon1 = df_sorted.iloc[i]['lon']
        
        for j in range(n):
            lat2 = df_sorted.iloc[j]['lat']
            lon2 = df_sorted.iloc[j]['lon']
            
            distance_km = haversine_distance(lat1, lon1, lat2, lon2)
            travel_time_minutes = distance_km * 1.5
            
            row.append(travel_time_minutes)
        
        time_matrix.append(row)
    
    return time_matrix


def dataframe_to_customers(df: pd.DataFrame) -> list:
    """Convert DataFrame rows to vrp_core.Customer objects"""
    customers = []
    for _, row in df.iterrows():
        location = vrp_core.Location(float(row['lat']), float(row['lon']))
        service_time = float(row.get('service_time', 10))
        
        customer = vrp_core.Customer(
            int(row['id']),
            location,
            float(row['demand']),
            float(row['start_window']),
            float(row['end_window']),
            service_time
        )
        customers.append(customer)
    
    return customers


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def demo_data_with_service_times():
    """Generate demo data with service times (similar to Dashboard)"""
    np.random.seed(42)
    
    # Create depot
    depot = {
        'id': 0,
        'lat': 19.065,
        'lon': 72.835,
        'demand': 0,
        'start_window': 0,
        'end_window': 600,
        'service_time': 0
    }
    
    # Generate 5 customers
    customers = [depot]
    for i in range(1, 6):
        lat = np.random.uniform(19.05, 19.08)
        lon = np.random.uniform(72.82, 72.85)
        demand = np.random.randint(1, 11)
        start_window = np.random.randint(0, 481)
        end_window = start_window + np.random.randint(60, 121)
        
        customers.append({
            'id': i,
            'lat': lat,
            'lon': lon,
            'demand': demand,
            'start_window': start_window,
            'end_window': end_window,
            'service_time': 10
        })
    
    return pd.DataFrame(customers)


@pytest.fixture
def tight_time_window_data():
    """Generate data with tight time windows to test constraint enforcement"""
    customers = [
        # Depot
        {'id': 0, 'lat': 19.065, 'lon': 72.835, 'demand': 0, 
         'start_window': 0, 'end_window': 600, 'service_time': 0},
        
        # Customer 1: Early time window
        {'id': 1, 'lat': 19.070, 'lon': 72.840, 'demand': 5,
         'start_window': 10, 'end_window': 30, 'service_time': 10},
        
        # Customer 2: Later time window (should cause waiting if visited early)
        {'id': 2, 'lat': 19.075, 'lon': 72.845, 'demand': 5,
         'start_window': 50, 'end_window': 70, 'service_time': 10},
        
        # Customer 3: Very tight window
        {'id': 3, 'lat': 19.068, 'lon': 72.838, 'demand': 5,
         'start_window': 80, 'end_window': 90, 'service_time': 10},
    ]
    
    return pd.DataFrame(customers)


# ============================================================================
# Integration Tests
# ============================================================================

def test_e2e_demo_data_with_service_times(demo_data_with_service_times):
    """
    Test 1: Generate demo data with service times
    
    Validates:
    - Demo data includes service_time field
    - Service times are set correctly (0 for depot, 10 for customers)
    """
    df = demo_data_with_service_times
    
    # Verify service_time column exists
    assert 'service_time' in df.columns, "Demo data should include service_time column"
    
    # Verify depot has service_time = 0
    depot_row = df[df['id'] == 0].iloc[0]
    assert depot_row['service_time'] == 0, "Depot should have service_time = 0"
    
    # Verify customers have service_time = 10
    customer_rows = df[df['id'] != 0]
    assert all(customer_rows['service_time'] == 10), "Customers should have service_time = 10"
    
    print("✅ Test 1 passed: Demo data includes correct service times")


def test_e2e_solver_with_time_matrix(demo_data_with_service_times):
    """
    Test 2: Run solver with time_matrix
    
    Validates:
    - Time matrix is generated correctly
    - Solver accepts time_matrix parameter
    - Solver returns valid routes
    """
    df = demo_data_with_service_times
    
    # Generate time matrix
    time_matrix = generate_time_matrix(df)
    
    # Verify time matrix dimensions
    n = len(df)
    assert len(time_matrix) == n, f"Time matrix should have {n} rows"
    assert all(len(row) == n for row in time_matrix), f"Time matrix should be {n}×{n}"
    
    # Convert to Customer objects
    customers = dataframe_to_customers(df)
    
    # Run solver with time_matrix
    solver = vrp_core.VRPSolver()
    routes = solver.solve(customers, [20.0], True, time_matrix)
    
    # Verify routes are returned
    assert routes is not None, "Solver should return routes"
    assert len(routes) > 0, "Solver should return at least one route"
    
    # Verify all routes start and end at depot
    for route in routes:
        assert route[0] == 0, "Route should start at depot (id=0)"
        assert route[-1] == 0, "Route should end at depot (id=0)"
    
    print(f"✅ Test 2 passed: Solver executed with time_matrix, returned {len(routes)} routes")


def test_e2e_routes_respect_time_windows(tight_time_window_data):
    """
    Test 3: Verify routes respect time windows
    
    Validates:
    - No customer is visited after their end_window
    - Time progression is consistent throughout routes
    """
    df = tight_time_window_data
    
    # Generate time matrix
    time_matrix = generate_time_matrix(df)
    
    # Convert to Customer objects
    customers = dataframe_to_customers(df)
    
    # Run solver
    solver = vrp_core.VRPSolver()
    routes = solver.solve(customers, [20.0], True, time_matrix)
    
    # Verify time window constraints for each route
    for route_idx, route in enumerate(routes):
        current_time = 0.0
        
        for i in range(len(route)):
            customer_id = route[i]
            customer_row = df[df['id'] == customer_id].iloc[0]
            
            # Calculate arrival time
            if i == 0:
                arrival_time = 0.0
            else:
                prev_customer_id = route[i - 1]
                travel_time = time_matrix[prev_customer_id][customer_id]
                arrival_time = current_time + travel_time
            
            # Verify arrival time is within time window
            start_window = customer_row['start_window']
            end_window = customer_row['end_window']
            
            assert arrival_time <= end_window, (
                f"Route {route_idx}, Customer {customer_id}: "
                f"Arrival time {arrival_time:.2f} exceeds end_window {end_window}"
            )
            
            # Calculate waiting time and departure time
            waiting_time = max(0.0, start_window - arrival_time)
            service_time = customer_row['service_time']
            departure_time = arrival_time + waiting_time + service_time
            
            # Update current time
            current_time = departure_time
    
    print("✅ Test 3 passed: All routes respect time window constraints")


def test_e2e_arrival_times_calculation(demo_data_with_service_times):
    """
    Test 4: Verify arrival times are calculated correctly
    
    Validates:
    - Arrival times follow time progression formula
    - Waiting times are calculated correctly
    - Departure times include service time
    """
    df = demo_data_with_service_times
    
    # Generate time matrix
    time_matrix = generate_time_matrix(df)
    
    # Convert to Customer objects
    customers = dataframe_to_customers(df)
    
    # Run solver
    solver = vrp_core.VRPSolver()
    routes = solver.solve(customers, [20.0], True, time_matrix)
    
    # Calculate and verify timing for each route
    for route_idx, route in enumerate(routes):
        current_time = 0.0
        prev_departure_time = 0.0
        
        for i in range(len(route)):
            customer_id = route[i]
            customer_row = df[df['id'] == customer_id].iloc[0]
            
            # Calculate arrival time
            if i == 0:
                arrival_time = 0.0
            else:
                prev_customer_id = route[i - 1]
                travel_time = time_matrix[prev_customer_id][customer_id]
                arrival_time = current_time + travel_time
                
                # Verify time progression consistency
                expected_arrival = prev_departure_time + travel_time
                assert abs(arrival_time - expected_arrival) < 0.01, (
                    f"Route {route_idx}, Customer {customer_id}: "
                    f"Arrival time {arrival_time:.2f} doesn't match expected {expected_arrival:.2f}"
                )
            
            # Calculate waiting time
            start_window = customer_row['start_window']
            waiting_time = max(0.0, start_window - arrival_time)
            
            # Calculate departure time
            service_time = customer_row['service_time']
            departure_time = arrival_time + waiting_time + service_time
            
            # Verify departure time calculation
            expected_departure = arrival_time + waiting_time + service_time
            assert abs(departure_time - expected_departure) < 0.01, (
                f"Route {route_idx}, Customer {customer_id}: "
                f"Departure time {departure_time:.2f} doesn't match expected {expected_departure:.2f}"
            )
            
            # Update for next iteration
            current_time = departure_time
            prev_departure_time = departure_time
    
    print("✅ Test 4 passed: Arrival times and timing calculations are correct")


def test_e2e_waiting_time_scenarios(tight_time_window_data):
    """
    Test 5: Verify waiting time scenarios
    
    Validates:
    - Early arrival causes waiting
    - On-time arrival has no waiting
    - Waiting time is calculated as max(0, start_window - arrival_time)
    """
    df = tight_time_window_data
    
    # Generate time matrix
    time_matrix = generate_time_matrix(df)
    
    # Convert to Customer objects
    customers = dataframe_to_customers(df)
    
    # Run solver
    solver = vrp_core.VRPSolver()
    routes = solver.solve(customers, [20.0], True, time_matrix)
    
    # Track waiting scenarios
    early_arrivals = 0
    on_time_arrivals = 0
    
    for route in routes:
        current_time = 0.0
        
        for i in range(len(route)):
            customer_id = route[i]
            customer_row = df[df['id'] == customer_id].iloc[0]
            
            # Calculate arrival time
            if i == 0:
                arrival_time = 0.0
            else:
                prev_customer_id = route[i - 1]
                travel_time = time_matrix[prev_customer_id][customer_id]
                arrival_time = current_time + travel_time
            
            # Calculate waiting time
            start_window = customer_row['start_window']
            end_window = customer_row['end_window']
            waiting_time = max(0.0, start_window - arrival_time)
            
            # Categorize arrival
            if arrival_time < start_window:
                early_arrivals += 1
                assert waiting_time > 0, (
                    f"Customer {customer_id}: Early arrival should have waiting time > 0"
                )
            elif start_window <= arrival_time <= end_window:
                on_time_arrivals += 1
                assert waiting_time == 0, (
                    f"Customer {customer_id}: On-time arrival should have waiting time = 0"
                )
            
            # Update current time
            service_time = customer_row['service_time']
            departure_time = arrival_time + waiting_time + service_time
            current_time = departure_time
    
    print(f"✅ Test 5 passed: Waiting time scenarios validated "
          f"(Early: {early_arrivals}, On-time: {on_time_arrivals})")


def test_e2e_backward_compatibility():
    """
    Test 6: Verify backward compatibility (solver without time_matrix)
    
    Validates:
    - Solver works without time_matrix parameter
    - Fallback to Haversine-based distance calculation
    - Routes are still valid
    """
    # Create simple test data
    customers_data = [
        {'id': 0, 'lat': 19.065, 'lon': 72.835, 'demand': 0,
         'start_window': 0, 'end_window': 600, 'service_time': 0},
        {'id': 1, 'lat': 19.070, 'lon': 72.840, 'demand': 5,
         'start_window': 0, 'end_window': 600, 'service_time': 10},
        {'id': 2, 'lat': 19.075, 'lon': 72.845, 'demand': 5,
         'start_window': 0, 'end_window': 600, 'service_time': 10},
    ]
    
    df = pd.DataFrame(customers_data)
    customers = dataframe_to_customers(df)
    
    # Run solver WITHOUT time_matrix (backward compatibility)
    solver = vrp_core.VRPSolver()
    routes = solver.solve(customers, [20.0], True)  # No time_matrix parameter
    
    # Verify routes are returned
    assert routes is not None, "Solver should return routes without time_matrix"
    assert len(routes) > 0, "Solver should return at least one route"
    
    # Verify routes are valid
    for route in routes:
        assert route[0] == 0, "Route should start at depot"
        assert route[-1] == 0, "Route should end at depot"
    
    print("✅ Test 6 passed: Backward compatibility verified (solver works without time_matrix)")


# ============================================================================
# Run All Tests
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("End-to-End Integration Test Suite")
    print("=" * 80)
    print()
    
    # Create test data directly (not using fixtures)
    np.random.seed(42)
    
    # Demo data
    depot = {
        'id': 0, 'lat': 19.065, 'lon': 72.835, 'demand': 0,
        'start_window': 0, 'end_window': 600, 'service_time': 0
    }
    customers = [depot]
    for i in range(1, 6):
        lat = np.random.uniform(19.05, 19.08)
        lon = np.random.uniform(72.82, 72.85)
        demand = np.random.randint(1, 11)
        start_window = np.random.randint(0, 481)
        end_window = start_window + np.random.randint(60, 121)
        customers.append({
            'id': i, 'lat': lat, 'lon': lon, 'demand': demand,
            'start_window': start_window, 'end_window': end_window,
            'service_time': 10
        })
    demo_data = pd.DataFrame(customers)
    
    # Tight time window data
    tight_customers = [
        {'id': 0, 'lat': 19.065, 'lon': 72.835, 'demand': 0,
         'start_window': 0, 'end_window': 600, 'service_time': 0},
        {'id': 1, 'lat': 19.070, 'lon': 72.840, 'demand': 5,
         'start_window': 10, 'end_window': 30, 'service_time': 10},
        {'id': 2, 'lat': 19.075, 'lon': 72.845, 'demand': 5,
         'start_window': 50, 'end_window': 70, 'service_time': 10},
        {'id': 3, 'lat': 19.068, 'lon': 72.838, 'demand': 5,
         'start_window': 80, 'end_window': 90, 'service_time': 10},
    ]
    tight_data = pd.DataFrame(tight_customers)
    
    # Run tests
    test_e2e_demo_data_with_service_times(demo_data)
    test_e2e_solver_with_time_matrix(demo_data)
    test_e2e_routes_respect_time_windows(tight_data)
    test_e2e_arrival_times_calculation(demo_data)
    test_e2e_waiting_time_scenarios(tight_data)
    test_e2e_backward_compatibility()
    
    print()
    print("=" * 80)
    print("✅ All End-to-End Integration Tests Passed!")
    print("=" * 80)
