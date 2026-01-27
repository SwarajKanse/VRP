"""
VRP Dashboard - High-Frequency Logistics Dashboard
Main entry point for the Streamlit application
"""

import os
import sys
import streamlit as st

# --- UNIVERSAL WINDOWS DLL FIX ---
if os.name == 'nt':
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, '..'))
    
    # 1. Define ALL critical paths
    paths_to_add = [
        # The project root where the .pyd file lives
        project_root,
        # The build folder (for any additional DLLs)
        os.path.join(project_root, 'build'),
        # CRITICAL: Your MinGW Compiler Runtime
        r"C:\mingw64\bin",
    ]
    
    # 2. Add them to Python's "Authorized DLL List"
    for path in paths_to_add:
        if os.path.exists(path):
            try:
                os.add_dll_directory(path)  # Whitelist this folder for DLLs
                if path not in sys.path:
                    sys.path.insert(0, path)   # Allow Python import finding (insert at front)
            except Exception as e:
                print(f"Warning: Could not add {path}: {e}")

# --- IMPORT SOLVER ---
vrp_core = None
vrp_core_error = None

try:
    import vrp_core
    # Optional: Toast to confirm it finally worked
    st.toast("✅ C++ Engine Loaded Successfully!", icon="🚀")
except ImportError as e:
    vrp_core_error = str(e)
    st.error(f"❌ DLL Load Failed: {e}")
    st.info("Tip: If this fails, restart your terminal to clear old cached paths.")
    # Don't stop - allow demo mode

import pandas as pd
import numpy as np
import pydeck as pdk
import time
import requests
from typing import List, Tuple, Dict
from dataclasses import dataclass


# ============================================================================
# Financial Calculation Module
# ============================================================================

@dataclass
class RouteMetrics:
    """Financial and operational metrics for a single route"""
    route_id: int
    distance_km: float
    duration_hours: float
    fuel_cost: float
    labor_cost: float
    total_cost: float
    num_customers: int


@dataclass
class FleetMetrics:
    """Aggregated financial metrics for entire fleet"""
    total_distance_km: float
    total_duration_hours: float
    total_fuel_cost: float
    total_labor_cost: float
    total_cost: float
    cost_per_km: float
    cost_per_delivery: float
    num_routes: int
    num_customers: int


def calculate_route_distance(
    route: List[int],
    time_matrix: List[List[float]],
    avg_speed_kmh: float = 40.0
) -> float:
    """
    Calculate total distance for a route in kilometers
    
    Args:
        route: List of customer IDs in visit order
        time_matrix: N×N matrix of travel times in minutes
        avg_speed_kmh: Average speed in km/h (default: 40.0)
    
    Returns:
        Total distance in kilometers
    
    Raises:
        ValueError: If route is None, time_matrix is None, or avg_speed_kmh is invalid
        IndexError: If route contains invalid customer IDs
    
    Algorithm:
        For each consecutive pair (i, j) in route:
            travel_time_minutes = time_matrix[i][j]
            distance_km = (travel_time_minutes / 60) * avg_speed_kmh
        Return sum of all distances
    """
    # Input validation
    if route is None:
        raise ValueError("Route cannot be None")
    if time_matrix is None:
        raise ValueError("Time matrix cannot be None")
    if avg_speed_kmh <= 0:
        raise ValueError(f"Average speed must be positive, got {avg_speed_kmh}")
    
    # Handle empty route
    if len(route) <= 1:
        return 0.0
    
    total_distance = 0.0
    
    try:
        for i in range(len(route) - 1):
            current_customer = route[i]
            next_customer = route[i + 1]
            
            # Validate customer IDs are within bounds
            if current_customer < 0 or current_customer >= len(time_matrix):
                raise IndexError(f"Invalid customer ID {current_customer} in route")
            if next_customer < 0 or next_customer >= len(time_matrix):
                raise IndexError(f"Invalid customer ID {next_customer} in route")
            
            # Get travel time from time_matrix (in minutes)
            travel_time_minutes = time_matrix[current_customer][next_customer]
            
            # Validate travel time is non-negative
            if travel_time_minutes < 0:
                raise ValueError(f"Invalid negative travel time: {travel_time_minutes}")
            
            # Convert to distance: (minutes / 60) * speed = hours * speed = km
            distance_km = (travel_time_minutes / 60.0) * avg_speed_kmh
            
            total_distance += distance_km
    except IndexError as e:
        raise IndexError(f"Error accessing time matrix: {str(e)}")
    except Exception as e:
        raise Exception(f"Error calculating route distance: {str(e)}")
    
    return total_distance


def calculate_route_duration(
    route: List[int],
    df: pd.DataFrame,
    time_matrix: List[List[float]]
) -> float:
    """
    Calculate total duration for a route in hours
    
    Args:
        route: List of customer IDs in visit order
        df: DataFrame with customer data (service_time column)
        time_matrix: N×N matrix of travel times in minutes
    
    Returns:
        Total duration in hours (travel + service + waiting)
    
    Raises:
        ValueError: If route, df, or time_matrix is None
        KeyError: If required columns are missing from DataFrame
    
    Algorithm:
        Use existing calculate_route_timing() function to get timing info
        Sum: travel_time + service_time + waiting_time for all stops
        Convert minutes to hours
    """
    # Input validation
    if route is None:
        raise ValueError("Route cannot be None")
    if df is None or df.empty:
        raise ValueError("Customer DataFrame cannot be None or empty")
    if time_matrix is None:
        raise ValueError("Time matrix cannot be None")
    
    # Validate required columns
    required_columns = ['id', 'start_window', 'end_window']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise KeyError(f"DataFrame is missing required columns: {', '.join(missing_columns)}")
    
    # Handle empty route
    if len(route) <= 1:
        return 0.0
    
    try:
        # Use existing calculate_route_timing() function
        timing_info = calculate_route_timing(route, df, time_matrix)
        
        # Calculate total duration in minutes
        total_duration_minutes = 0.0
        
        for i, info in enumerate(timing_info):
            customer_id = info['customer_id']
            
            # Add travel time (except for first customer which is depot)
            if i > 0:
                prev_customer = route[i - 1]
                travel_time = time_matrix[prev_customer][customer_id]
                total_duration_minutes += travel_time
            
            # Add waiting time
            total_duration_minutes += info['waiting_time']
            
            # Add service time
            customer_row = df[df['id'] == customer_id]
            if customer_row.empty:
                raise ValueError(f"Customer ID {customer_id} not found in DataFrame")
            
            service_time = customer_row.iloc[0].get('service_time', 10)
            total_duration_minutes += service_time
        
        # Convert minutes to hours
        total_duration_hours = total_duration_minutes / 60.0
        
        return total_duration_hours
    except Exception as e:
        raise Exception(f"Error calculating route duration: {str(e)}")


def calculate_route_metrics(
    route: List[int],
    route_id: int,
    df: pd.DataFrame,
    time_matrix: List[List[float]],
    fuel_price: float,
    vehicle_mileage: float,
    driver_wage: float
) -> RouteMetrics:
    """
    Calculate comprehensive metrics for a single route
    
    Args:
        route: List of customer IDs in visit order
        route_id: Route identifier (0, 1, 2, ...)
        df: DataFrame with customer data
        time_matrix: N×N matrix of travel times in minutes
        fuel_price: Cost per liter of fuel (₹/L)
        vehicle_mileage: Vehicle efficiency (km/L)
        driver_wage: Hourly wage for driver (₹/hour)
    
    Returns:
        RouteMetrics object with all calculated metrics
    
    Raises:
        ValueError: If cost parameters are invalid or inputs are None
    
    Algorithm:
        1. distance_km = calculate_route_distance(route, time_matrix)
        2. duration_hours = calculate_route_duration(route, df, time_matrix)
        3. fuel_cost = (distance_km / vehicle_mileage) * fuel_price
        4. labor_cost = duration_hours * driver_wage
        5. total_cost = fuel_cost + labor_cost
        6. num_customers = len(route) - 1  # Exclude depot
        7. Return RouteMetrics(...)
    """
    # Input validation
    if route is None:
        raise ValueError("Route cannot be None")
    if df is None or df.empty:
        raise ValueError("Customer DataFrame cannot be None or empty")
    if time_matrix is None:
        raise ValueError("Time matrix cannot be None")
    
    # Validate cost parameters
    if fuel_price <= 0:
        raise ValueError(f"Fuel price must be positive, got {fuel_price}")
    if vehicle_mileage <= 0:
        raise ValueError(f"Vehicle mileage must be positive, got {vehicle_mileage}")
    if driver_wage <= 0:
        raise ValueError(f"Driver wage must be positive, got {driver_wage}")
    
    # Handle edge case: empty route or route with only depot
    if len(route) <= 1:
        return RouteMetrics(
            route_id=route_id,
            distance_km=0.0,
            duration_hours=0.0,
            fuel_cost=0.0,
            labor_cost=0.0,
            total_cost=0.0,
            num_customers=0
        )
    
    try:
        # Calculate distance in kilometers
        distance_km = calculate_route_distance(route, time_matrix)
        
        # Calculate duration in hours
        duration_hours = calculate_route_duration(route, df, time_matrix)
        
        # Calculate fuel cost: (distance / mileage) * price
        fuel_cost = (distance_km / vehicle_mileage) * fuel_price
        
        # Calculate labor cost: duration * wage
        labor_cost = duration_hours * driver_wage
        
        # Calculate total cost
        total_cost = fuel_cost + labor_cost
        
        # Count customers (exclude all depot visits - depot has id=0)
        num_customers = sum(1 for customer_id in route if customer_id != 0)
        
        return RouteMetrics(
            route_id=route_id,
            distance_km=distance_km,
            duration_hours=duration_hours,
            fuel_cost=fuel_cost,
            labor_cost=labor_cost,
            total_cost=total_cost,
            num_customers=num_customers
        )
    except Exception as e:
        raise Exception(f"Error calculating route metrics for route {route_id}: {str(e)}")


def calculate_fleet_metrics(
    routes: List[List[int]],
    df: pd.DataFrame,
    time_matrix: List[List[float]],
    fuel_price: float,
    vehicle_mileage: float,
    driver_wage: float
) -> Tuple[FleetMetrics, List[RouteMetrics]]:
    """
    Calculate aggregated metrics for entire fleet
    
    Args:
        routes: List of routes (each route is list of customer IDs)
        df: DataFrame with customer data
        time_matrix: N×N matrix of travel times in minutes
        fuel_price: Cost per liter of fuel (₹/L)
        vehicle_mileage: Vehicle efficiency (km/L)
        driver_wage: Hourly wage for driver (₹/hour)
    
    Returns:
        Tuple of (FleetMetrics, List[RouteMetrics])
    
    Raises:
        ValueError: If inputs are invalid or cost parameters are non-positive
    
    Algorithm:
        1. route_metrics_list = []
        2. For each route with index i:
            metrics = calculate_route_metrics(route, i, df, time_matrix, ...)
            route_metrics_list.append(metrics)
        3. Aggregate totals:
            total_distance = sum(m.distance_km for m in route_metrics_list)
            total_duration = sum(m.duration_hours for m in route_metrics_list)
            total_fuel_cost = sum(m.fuel_cost for m in route_metrics_list)
            total_labor_cost = sum(m.labor_cost for m in route_metrics_list)
            total_cost = total_fuel_cost + total_labor_cost
        4. Calculate KPIs:
            cost_per_km = total_cost / total_distance if total_distance > 0 else 0
            num_customers = sum(m.num_customers for m in route_metrics_list)
            cost_per_delivery = total_cost / num_customers if num_customers > 0 else 0
        5. Return FleetMetrics(...), route_metrics_list
    """
    # Input validation
    if routes is None:
        raise ValueError("Routes cannot be None")
    if df is None or df.empty:
        raise ValueError("Customer DataFrame cannot be None or empty")
    if time_matrix is None:
        raise ValueError("Time matrix cannot be None")
    
    # Validate cost parameters
    if fuel_price <= 0:
        raise ValueError(f"Fuel price must be positive, got {fuel_price}")
    if vehicle_mileage <= 0:
        raise ValueError(f"Vehicle mileage must be positive, got {vehicle_mileage}")
    if driver_wage <= 0:
        raise ValueError(f"Driver wage must be positive, got {driver_wage}")
    
    # Handle edge case: empty routes list
    if not routes:
        return FleetMetrics(
            total_distance_km=0.0,
            total_duration_hours=0.0,
            total_fuel_cost=0.0,
            total_labor_cost=0.0,
            total_cost=0.0,
            cost_per_km=0.0,
            cost_per_delivery=0.0,
            num_routes=0,
            num_customers=0
        ), []
    
    try:
        # Calculate metrics for each route
        route_metrics_list = []
        for i, route in enumerate(routes):
            metrics = calculate_route_metrics(
                route=route,
                route_id=i,
                df=df,
                time_matrix=time_matrix,
                fuel_price=fuel_price,
                vehicle_mileage=vehicle_mileage,
                driver_wage=driver_wage
            )
            route_metrics_list.append(metrics)
        
        # Aggregate totals
        total_distance = sum(m.distance_km for m in route_metrics_list)
        total_duration = sum(m.duration_hours for m in route_metrics_list)
        total_fuel_cost = sum(m.fuel_cost for m in route_metrics_list)
        total_labor_cost = sum(m.labor_cost for m in route_metrics_list)
        total_cost = total_fuel_cost + total_labor_cost
        
        # Calculate KPIs with division by zero handling
        cost_per_km = total_cost / total_distance if total_distance > 0 else 0.0
        num_customers = sum(m.num_customers for m in route_metrics_list)
        cost_per_delivery = total_cost / num_customers if num_customers > 0 else 0.0
        
        # Create FleetMetrics object
        fleet_metrics = FleetMetrics(
            total_distance_km=total_distance,
            total_duration_hours=total_duration,
            total_fuel_cost=total_fuel_cost,
            total_labor_cost=total_labor_cost,
            total_cost=total_cost,
            cost_per_km=cost_per_km,
            cost_per_delivery=cost_per_delivery,
            num_routes=len(routes),
            num_customers=num_customers
        )
        
        return fleet_metrics, route_metrics_list
    except Exception as e:
        raise Exception(f"Error calculating fleet metrics: {str(e)}")


# ============================================================================
# Export Module
# ============================================================================

def format_time(minutes: float) -> str:
    """
    Convert minutes to HH:MM format
    
    Args:
        minutes: Time in minutes from start of day
    
    Returns:
        Formatted time string "HH:MM"
    
    Algorithm:
        hours = int(minutes // 60)
        mins = int(minutes % 60)
        return f"{hours:02d}:{mins:02d}"
    """
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    return f"{hours:02d}:{mins:02d}"


def generate_driver_manifest(
    routes: List[List[int]],
    df: pd.DataFrame,
    time_matrix: List[List[float]]
) -> pd.DataFrame:
    """
    Generate driver manifest DataFrame for export
    
    Args:
        routes: List of routes
        df: DataFrame with customer data
        time_matrix: N×N matrix of travel times
    
    Returns:
        DataFrame with columns:
            - Route_ID: Vehicle/route number
            - Stop_Number: Sequential stop number (1, 2, 3, ...)
            - Customer_ID: Customer identifier
            - Arrival_Time: Formatted time string (HH:MM)
            - Action: "Deliver" or "Pickup" (default: "Deliver")
    
    Raises:
        ValueError: If inputs are None or invalid
    
    Algorithm:
        1. manifest_rows = []
        2. For each route with route_id:
            timing_info = calculate_route_timing(route, df, time_matrix)
            For each stop with stop_number:
                arrival_minutes = timing_info[stop_number]['arrival_time']
                arrival_time_str = format_time(arrival_minutes)  # "HH:MM"
                manifest_rows.append({
                    'Route_ID': route_id + 1,  # 1-indexed for drivers
                    'Stop_Number': stop_number + 1,
                    'Customer_ID': customer_id,
                    'Arrival_Time': arrival_time_str,
                    'Action': 'Deliver'
                })
        3. Return pd.DataFrame(manifest_rows)
    """
    # Input validation
    if routes is None:
        raise ValueError("Routes cannot be None")
    if df is None or df.empty:
        raise ValueError("Customer DataFrame cannot be None or empty")
    if time_matrix is None:
        raise ValueError("Time matrix cannot be None")
    
    # Handle empty routes list
    if not routes:
        return pd.DataFrame(columns=['Route_ID', 'Stop_Number', 'Customer_ID', 'Arrival_Time', 'Action'])
    
    try:
        manifest_rows = []
        
        # Process each route
        for route_id, route in enumerate(routes):
            # Skip empty routes
            if not route:
                continue
            
            # Get timing information for this route
            timing_info = calculate_route_timing(route, df, time_matrix)
            
            # Process each stop in the route
            for stop_number, info in enumerate(timing_info):
                customer_id = info['customer_id']
                arrival_minutes = info['arrival_time']
                
                # Format arrival time as HH:MM
                arrival_time_str = format_time(arrival_minutes)
                
                # Create manifest row
                manifest_rows.append({
                    'Route_ID': route_id + 1,  # 1-indexed for drivers
                    'Stop_Number': stop_number + 1,  # 1-indexed for drivers
                    'Customer_ID': customer_id,
                    'Arrival_Time': arrival_time_str,
                    'Action': 'Deliver'
                })
        
        # Convert to DataFrame
        manifest_df = pd.DataFrame(manifest_rows)
        
        return manifest_df
    except Exception as e:
        raise Exception(f"Error generating driver manifest: {str(e)}")


# ============================================================================
# Data Management Module
# ============================================================================

def generate_demo_data() -> pd.DataFrame:
    """
    Generate 5-10 random customers in Mumbai/Bandra area
    
    Returns:
        DataFrame with columns: id, lat, lon, demand, start_window, end_window, service_time
    """
    np.random.seed(42)  # For reproducible demo data
    
    # Generate random number of customers (5-10)
    num_customers = np.random.randint(5, 11)
    
    # Create depot as customer 0
    depot = {
        'id': 0,
        'lat': 19.065,
        'lon': 72.835,
        'demand': 0,
        'start_window': 0,
        'end_window': 600,
        'service_time': 0  # Depot has no service time
    }
    
    # Generate random customers
    customers = [depot]
    for i in range(1, num_customers):
        # Random coordinates in Mumbai/Bandra area
        lat = np.random.uniform(19.05, 19.08)
        lon = np.random.uniform(72.82, 72.85)
        
        # Random demand (1-10)
        demand = np.random.randint(1, 11)
        
        # Random time windows
        start_window = np.random.randint(0, 481)  # 0-480
        end_window = start_window + np.random.randint(60, 121)  # start + 60-120
        
        customers.append({
            'id': i,
            'lat': lat,
            'lon': lon,
            'demand': demand,
            'start_window': start_window,
            'end_window': end_window,
            'service_time': 10  # Default 10 minutes service time
        })
    
    return pd.DataFrame(customers)


def load_customer_csv(uploaded_file) -> pd.DataFrame:
    """
    Load and validate CSV file
    
    Args:
        uploaded_file: Streamlit UploadedFile object
        
    Returns:
        DataFrame with validated customer data
        
    Raises:
        ValueError: If required columns are missing
    """
    # Parse CSV to DataFrame
    df = pd.read_csv(uploaded_file)
    
    # Validate required columns
    required_columns = ['id', 'lat', 'lon', 'demand', 'start_window', 'end_window']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        raise ValueError(
            f"CSV file is missing required columns: {', '.join(missing_columns)}. "
            f"Required columns are: {', '.join(required_columns)}"
        )
    
    # Handle service_time column: use from CSV if present, otherwise default to 10
    if 'service_time' not in df.columns:
        df['service_time'] = 10  # Default 10 minutes service time
    
    return df


def dataframe_to_customers(df: pd.DataFrame) -> List:
    """
    Convert DataFrame rows to vrp_core.Customer objects
    
    Args:
        df: DataFrame with columns: id, lat, lon, demand, start_window, end_window, service_time
        
    Returns:
        List of vrp_core.Customer objects
    """
    if vrp_core is None:
        raise RuntimeError("vrp_core module not available")
    
    customers = []
    for _, row in df.iterrows():
        # Create Location object first
        location = vrp_core.Location(float(row['lat']), float(row['lon']))
        
        # Get service_time with default value of 10 if not present
        service_time = float(row.get('service_time', 10))
        
        # Create Customer with correct constructor signature:
        # Customer(int id, Location loc, double demand, double start_w, double end_w, double service_t)
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
# Unassigned Customer Detection Module
# ============================================================================

def detect_unassigned_customers(
    routes: List[List[int]],
    df: pd.DataFrame
) -> List[int]:
    """
    Detect customers that are not assigned to any route
    
    Compares the total customer list with customers present in routes
    to identify any customers that could not be assigned due to capacity
    or time window constraints.
    
    Args:
        routes: List of routes (each route is list of customer IDs)
        df: DataFrame with customer data (must have 'id' column)
    
    Returns:
        List of customer IDs that are not present in any route
        (excludes depot with id=0)
    
    Algorithm:
        1. Extract all customer IDs from DataFrame (exclude depot id=0)
        2. Extract all customer IDs from routes (exclude depot id=0)
        3. Find difference: customers_in_df - customers_in_routes
        4. Return list of unassigned customer IDs
    
    Requirements: 2.5
    """
    # Input validation
    if routes is None:
        routes = []
    if df is None or df.empty:
        return []
    
    # Get all customer IDs from DataFrame (exclude depot with id=0)
    all_customer_ids = set(df[df['id'] != 0]['id'].tolist())
    
    # Get all customer IDs present in routes (exclude depot with id=0)
    customers_in_routes = set()
    for route in routes:
        for customer_id in route:
            if customer_id != 0:  # Exclude depot
                customers_in_routes.add(customer_id)
    
    # Find unassigned customers: customers in DataFrame but not in routes
    unassigned_customer_ids = all_customer_ids - customers_in_routes
    
    # Return as sorted list for consistent ordering
    return sorted(list(unassigned_customer_ids))


# ============================================================================
# Fleet Configuration Module
# ============================================================================

def get_default_cargo_length(vehicle_type: str) -> float:
    """
    Get default cargo bay length based on vehicle type
    
    Args:
        vehicle_type: Name of vehicle type (e.g., "Truck", "Van", "Tempo")
    
    Returns:
        Default length in meters
    
    Requirements: 1.2
    """
    defaults = {
        "Tempo": 2.5,
        "Truck": 4.0,
        "Van": 3.0,
        "Bike": 1.0
    }
    return defaults.get(vehicle_type, 2.5)


def get_default_cargo_width(vehicle_type: str) -> float:
    """
    Get default cargo bay width based on vehicle type
    
    Args:
        vehicle_type: Name of vehicle type (e.g., "Truck", "Van", "Tempo")
    
    Returns:
        Default width in meters
    
    Requirements: 1.2
    """
    defaults = {
        "Tempo": 1.5,
        "Truck": 2.0,
        "Van": 1.8,
        "Bike": 0.8
    }
    return defaults.get(vehicle_type, 1.5)


def get_default_cargo_height(vehicle_type: str) -> float:
    """
    Get default cargo bay height based on vehicle type
    
    Args:
        vehicle_type: Name of vehicle type (e.g., "Truck", "Van", "Tempo")
    
    Returns:
        Default height in meters
    
    Requirements: 1.2
    """
    defaults = {
        "Tempo": 1.5,
        "Truck": 2.5,
        "Van": 1.8,
        "Bike": 1.0
    }
    return defaults.get(vehicle_type, 1.5)


def flatten_and_sort_fleet(vehicle_profiles: List[Dict]) -> Tuple[List[float], List[Dict]]:
    """
    Convert vehicle profiles to sorted capacity list and vehicle map
    
    Args:
        vehicle_profiles: List of dicts with keys: name, capacity, quantity,
                         cargo_length, cargo_width, cargo_height, fuel_efficiency
    
    Returns:
        Tuple of (vehicle_capacities, vehicle_map)
        - vehicle_capacities: List of float capacities sorted in descending order
        - vehicle_map: List of dicts with keys: name, instance, capacity,
                      cargo_length, cargo_width, cargo_height, fuel_efficiency
    
    Algorithm:
        1. Flatten profiles into list of vehicle dicts with instance numbers
        2. Sort by capacity in descending order
        3. Extract capacity list
        4. Return tuple of (vehicle_capacities, vehicle_map)
    
    Requirements: 1.5, 1.6
    """
    # Step 1: Flatten profiles into list of vehicle dicts
    vehicles = []
    for profile in vehicle_profiles:
        for i in range(profile["quantity"]):
            vehicle = {
                "name": profile["name"],
                "capacity": profile["capacity"],
                "instance": i + 1
            }
            
            # Add cargo dimensions if present, otherwise use defaults
            vehicle["cargo_length"] = profile.get("cargo_length", get_default_cargo_length(profile["name"]))
            vehicle["cargo_width"] = profile.get("cargo_width", get_default_cargo_width(profile["name"]))
            vehicle["cargo_height"] = profile.get("cargo_height", get_default_cargo_height(profile["name"]))
            
            # Add fuel efficiency if present, otherwise use default of 10.0 km/L
            vehicle["fuel_efficiency"] = profile.get("fuel_efficiency", 10.0)
            
            vehicles.append(vehicle)
    
    # Step 2: Sort by capacity (descending)
    vehicles.sort(key=lambda v: v["capacity"], reverse=True)
    
    # Step 3: Extract capacity list
    vehicle_capacities = [v["capacity"] for v in vehicles]
    
    # Step 4: Create vehicle map
    vehicle_map = vehicles
    
    return vehicle_capacities, vehicle_map


def validate_vehicle_profiles(vehicle_profiles: List[Dict]) -> List[str]:
    """
    Validate vehicle profiles for correct input
    
    Args:
        vehicle_profiles: List of dicts with keys: name, capacity, quantity,
                         cargo_length, cargo_width, cargo_height
    
    Returns:
        List of validation error messages (empty list if all valid)
    
    Validation Rules:
        - Capacity must be a positive number (> 0)
        - Quantity must be a positive integer (> 0)
        - Cargo dimensions (length, width, height) must be positive numbers (> 0)
    
    Requirements: 1.2, 1.3
    """
    errors = []
    
    for i, profile in enumerate(vehicle_profiles):
        # Validate capacity is positive number
        capacity = profile.get("capacity")
        if capacity is None:
            errors.append(f"Vehicle profile {i+1}: Missing capacity")
        elif not isinstance(capacity, (int, float)):
            errors.append(f"Vehicle profile {i+1}: Capacity must be a number, got {type(capacity).__name__}")
        elif capacity <= 0:
            errors.append(f"Vehicle profile {i+1}: Capacity must be positive, got {capacity}")
        
        # Validate quantity is positive integer
        quantity = profile.get("quantity")
        if quantity is None:
            errors.append(f"Vehicle profile {i+1}: Missing quantity")
        elif not isinstance(quantity, int):
            errors.append(f"Vehicle profile {i+1}: Quantity must be an integer, got {type(quantity).__name__}")
        elif quantity <= 0:
            errors.append(f"Vehicle profile {i+1}: Quantity must be positive, got {quantity}")
        
        # Validate cargo dimensions (if present)
        cargo_length = profile.get("cargo_length")
        if cargo_length is not None:
            if not isinstance(cargo_length, (int, float)):
                errors.append(f"Vehicle profile {i+1}: Cargo length must be a number, got {type(cargo_length).__name__}")
            elif cargo_length <= 0:
                errors.append(f"Vehicle profile {i+1}: Cargo length must be positive, got {cargo_length}")
        
        cargo_width = profile.get("cargo_width")
        if cargo_width is not None:
            if not isinstance(cargo_width, (int, float)):
                errors.append(f"Vehicle profile {i+1}: Cargo width must be a number, got {type(cargo_width).__name__}")
            elif cargo_width <= 0:
                errors.append(f"Vehicle profile {i+1}: Cargo width must be positive, got {cargo_width}")
        
        cargo_height = profile.get("cargo_height")
        if cargo_height is not None:
            if not isinstance(cargo_height, (int, float)):
                errors.append(f"Vehicle profile {i+1}: Cargo height must be a number, got {type(cargo_height).__name__}")
            elif cargo_height <= 0:
                errors.append(f"Vehicle profile {i+1}: Cargo height must be positive, got {cargo_height}")
    
    return errors


# ============================================================================
# Chaos Mode State Management Module
# ============================================================================

def initialize_chaos_state():
    """
    Initialize session state variables for chaos mode
    
    Creates and initializes the following session state variables:
    - original_customers: DataFrame with initial customer data
    - dynamic_customers: List of DataFrames for injected emergency orders
    - chaos_mode_active: Boolean flag indicating if chaos mode is active
    - current_time: Float representing current simulation time in minutes
    - reoptimization_times: List of re-optimization execution times in milliseconds
    """
    if 'original_customers' not in st.session_state:
        st.session_state.original_customers = None
    if 'dynamic_customers' not in st.session_state:
        st.session_state.dynamic_customers = []
    if 'chaos_mode_active' not in st.session_state:
        st.session_state.chaos_mode_active = False
    if 'current_time' not in st.session_state:
        st.session_state.current_time = 0.0
    if 'reoptimization_times' not in st.session_state:
        st.session_state.reoptimization_times = []


def get_current_customers() -> pd.DataFrame:
    """
    Get combined customer list (original + dynamic)
    
    Merges the original customer dataset with all dynamically injected
    emergency orders to create a complete customer list for routing.
    
    Returns:
        DataFrame containing all customers (original + dynamic)
        Returns empty DataFrame if no original customers exist
    """
    if st.session_state.original_customers is None:
        return pd.DataFrame()
    
    # Start with original customers
    combined = st.session_state.original_customers.copy()
    
    # Append all dynamic customers
    for dynamic_customer in st.session_state.dynamic_customers:
        combined = pd.concat([combined, dynamic_customer], ignore_index=True)
    
    return combined


def generate_emergency_order(
    existing_df: pd.DataFrame,
    current_time: float
) -> pd.DataFrame:
    """
    Generate a random emergency order with valid constraints
    
    Creates a new customer with random location within the bounding box of
    existing customers, random demand (1-5), tight time window starting at
    current_time, and priority service time of 5 minutes.
    
    Args:
        existing_df: DataFrame containing current customers (used to determine
                     geographic bounds and assign unique ID)
        current_time: Current simulation time in minutes (used to calculate
                      time windows for immediate service)
    
    Returns:
        Single-row DataFrame with new emergency customer data containing
        columns: id, lat, lon, demand, start_window, end_window, service_time
    
    Edge Cases:
        - If existing_df has only depot (id=0), uses default Mumbai bounds
          (lat: 19.05-19.08, lon: 72.82-72.85)
    """
    import random
    
    # Edge case: If only depot exists, use default Mumbai bounds
    if len(existing_df) <= 1:
        min_lat, max_lat = 19.05, 19.08
        min_lon, max_lon = 72.82, 72.85
    else:
        # Calculate bounding box from existing customer coordinates
        min_lat = existing_df['lat'].min()
        max_lat = existing_df['lat'].max()
        min_lon = existing_df['lon'].min()
        max_lon = existing_df['lon'].max()
    
    # Generate random location within bounds
    lat = random.uniform(min_lat, max_lat)
    lon = random.uniform(min_lon, max_lon)
    
    # Generate random demand (1-5)
    demand = random.randint(1, 5)
    
    # Calculate time window: start = current_time, end = current_time + 30
    start_window = current_time
    end_window = current_time + 30
    
    # Set service time to 5 minutes (priority handling)
    service_time = 5
    
    # Assign unique ID: max(existing_df['id']) + 1
    new_id = int(existing_df['id'].max()) + 1
    
    # Create single-row DataFrame with new customer
    new_customer = pd.DataFrame([{
        'id': new_id,
        'lat': lat,
        'lon': lon,
        'demand': demand,
        'start_window': start_window,
        'end_window': end_window,
        'service_time': service_time
    }])
    
    return new_customer


def handle_reset_button():
    """
    Handle reset simulation button click
    
    Clears all chaos mode state and returns the simulation to its initial
    state with only the original customers. This function resets all
    dynamic customers, routes, and timing information.
    
    Side Effects:
        - Clears st.session_state.dynamic_customers (set to empty list)
        - Sets st.session_state.chaos_mode_active to False
        - Resets st.session_state.current_time to 0.0
        - Clears st.session_state.routes to None
        - Clears st.session_state.execution_time_ms to None
        - Clears st.session_state.time_matrix to None
        - Clears st.session_state.reoptimization_times to empty list
        - Clears st.session_state.packing_results to None
        - Calls st.rerun() to refresh the UI
    
    Requirements: 4.4
    """
    # Clear dynamic customers list
    st.session_state.dynamic_customers = []
    
    # Deactivate chaos mode
    st.session_state.chaos_mode_active = False
    
    # Reset simulation time
    st.session_state.current_time = 0.0
    
    # Clear routes
    st.session_state.routes = None
    
    # Clear execution time
    st.session_state.execution_time_ms = None
    
    # Clear time matrix
    st.session_state.time_matrix = None
    
    # Clear re-optimization times
    st.session_state.reoptimization_times = []
    
    # Clear packing results
    st.session_state.packing_results = None
    
    # Refresh UI to reflect reset state
    st.rerun()


# ============================================================================
# Solver Integration Module
# ============================================================================

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate Haversine distance between two geographic points
    
    Args:
        lat1: Latitude of point 1 (degrees)
        lon1: Longitude of point 1 (degrees)
        lat2: Latitude of point 2 (degrees)
        lon2: Longitude of point 2 (degrees)
        
    Returns:
        Distance in kilometers
    """
    # Earth radius in kilometers
    R = 6371.0
    
    # Convert degrees to radians
    lat1_rad = np.radians(lat1)
    lon1_rad = np.radians(lon1)
    lat2_rad = np.radians(lat2)
    lon2_rad = np.radians(lon2)
    
    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = np.sin(dlat / 2)**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    
    distance = R * c
    return distance


def generate_time_matrix(df: pd.DataFrame) -> List[List[float]]:
    """
    Generate travel time matrix for all customer pairs
    
    Calculates Haversine distance for all customer pairs and converts to
    travel time using distance * 1.5 (equivalent to 40 km/h speed).
    
    Args:
        df: DataFrame with customer data (must have 'id', 'lat', 'lon' columns)
        
    Returns:
        N×N matrix as list of lists, where time_matrix[i][j] is the travel
        time in minutes from customer i to customer j
    """
    n = len(df)
    time_matrix = []
    
    # Sort DataFrame by id to ensure correct indexing
    df_sorted = df.sort_values('id').reset_index(drop=True)
    
    for i in range(n):
        row = []
        lat1 = df_sorted.iloc[i]['lat']
        lon1 = df_sorted.iloc[i]['lon']
        
        for j in range(n):
            lat2 = df_sorted.iloc[j]['lat']
            lon2 = df_sorted.iloc[j]['lon']
            
            # Calculate Haversine distance in kilometers
            distance_km = haversine_distance(lat1, lon1, lat2, lon2)
            
            # Convert to travel time in minutes
            # distance * 1.5 = distance / (40/60) = distance / 0.6667
            # This assumes 40 km/h average speed
            travel_time_minutes = distance_km * 1.5
            
            row.append(travel_time_minutes)
        
        time_matrix.append(row)
    
    return time_matrix


def get_osrm_matrix(locations: List[List[float]]) -> List[List[float]]:
    """
    Query OSRM API for travel time matrix
    
    Args:
        locations: List of [latitude, longitude] pairs
        
    Returns:
        N×N matrix of travel times in minutes
        
    Raises:
        requests.exceptions.RequestException: If API request fails
        requests.exceptions.Timeout: If request exceeds timeout
        requests.exceptions.HTTPError: If API returns non-200 status
        json.JSONDecodeError: If response is not valid JSON
        KeyError: If API response is missing expected fields
    """
    # CRITICAL: OSRM expects "lon,lat" format, but we receive [lat, lon] pairs
    # Explicitly swap: locations[i] = [lat, lon], so we format as f"{lon},{lat}"
    coords = ";".join([f"{loc[1]},{loc[0]}" for loc in locations])
    
    # Construct OSRM Table Service URL
    url = f"http://router.project-osrm.org/table/v1/driving/{coords}?annotations=duration"
    
    # Make HTTP GET request with 10-second timeout
    response = requests.get(url, timeout=10)
    
    # Raise HTTPError for bad status codes
    response.raise_for_status()
    
    # Parse JSON response
    data = response.json()
    
    # Extract durations matrix (in seconds)
    durations = data['durations']
    
    # Convert duration values from seconds to minutes (explicit float division)
    time_matrix = [[duration / 60.0 for duration in row] for row in durations]
    
    return time_matrix


def solve_routing(
    customers: List,
    vehicle_capacities: List[float],
    df: pd.DataFrame
) -> Tuple[List[List[int]], float, List[List[float]]]:
    """
    Execute VRP solver with OSRM time matrix (fallback to Haversine)
    
    Args:
        customers: List of vrp_core.Customer objects
        vehicle_capacities: List of vehicle capacities (one per vehicle)
        df: DataFrame with customer data (used to generate time_matrix)
        
    Returns:
        Tuple of (routes, execution_time_ms, time_matrix)
        - routes: List of routes, each route is list of customer IDs
        - execution_time_ms: Solver execution time in milliseconds
        - time_matrix: The time matrix used (either OSRM or Haversine fallback)
        
    Raises:
        RuntimeError: If vrp_core module is not available
        Exception: If solver execution fails
    """
    if vrp_core is None:
        raise RuntimeError("vrp_core module not available")
    
    try:
        # Sort DataFrame by id to ensure correct indexing
        df_sorted = df.sort_values('id').reset_index(drop=True)
        
        # Extract locations from DataFrame
        locations = [[row['lat'], row['lon']] for _, row in df_sorted.iterrows()]
        
        # Try OSRM first, fall back to Haversine on any error
        try:
            time_matrix = get_osrm_matrix(locations)
            # Visual proof: Show sample travel time from depot to first customer
            sample_time = time_matrix[0][1] if len(time_matrix) > 1 else 0.0
            st.success(f"✅ Using OSRM real road network! (Sample: Depot→Customer1 = {sample_time:.1f} mins)")
        except Exception as e:
            # Fallback to Haversine-based calculation
            st.warning(
                f"⚠️ OSRM API unavailable ({type(e).__name__}). "
                f"Using Haversine-based travel times (40 km/h average speed)."
            )
            time_matrix = generate_time_matrix(df)
        
        # Create VRPSolver instance (no parameters in current API)
        solver = vrp_core.VRPSolver()
        
        # Measure execution time
        start_time = time.perf_counter()
        # Updated API: solve(customers, vehicle_capacities, use_simd, time_matrix)
        routes = solver.solve(customers, vehicle_capacities, True, time_matrix)
        end_time = time.perf_counter()
        
        # Convert to milliseconds
        execution_time_ms = (end_time - start_time) * 1000.0
        
        return routes, execution_time_ms, time_matrix
        
    except Exception as e:
        raise Exception(f"Solver execution failed: {str(e)}")


def validate_packing_for_routes(
    routes: List[List[int]],
    df: pd.DataFrame,
    vehicle_map: List[Dict],
    cargo_config: Dict[str, float]
) -> Dict[int, 'PackingResult']:
    """
    Validate 3D packing for all routes after VRP solver completes
    
    This function performs Task 8.1: Add packing validation after route generation.
    It extracts customer demands per route, generates packages, runs the packing
    algorithm, and stores results in session state.
    
    If parsed manifest data is available (from CSV upload), it uses the LIFO packing
    engine with actual package details. Otherwise, it falls back to the existing
    packing engine with generated packages.
    
    Args:
        routes: List of routes (each route is list of customer IDs)
        df: DataFrame with customer data (must have 'id' and 'demand' columns)
        vehicle_map: List of vehicle info dicts with cargo dimensions
        cargo_config: Dict with 'min_package_size' and 'max_package_size'
        
    Returns:
        Dict mapping route_id to PackingResult object
        
    Raises:
        ValueError: If inputs are invalid or missing required data
        ImportError: If packing_engine module cannot be imported
        
    Requirements: 6.1, 6.2
    """
    # Task 9.2: Validate inputs - Requirement 6.3
    if routes is None:
        raise ValueError("routes cannot be None")
    if df is None or df.empty:
        raise ValueError("Customer DataFrame cannot be None or empty")
    if vehicle_map is None or len(vehicle_map) == 0:
        raise ValueError("vehicle_map cannot be None or empty")
    if cargo_config is None:
        raise ValueError("cargo_config cannot be None")
    
    # Validate cargo_config has required keys
    if 'min_package_size' not in cargo_config:
        raise ValueError("cargo_config missing 'min_package_size'")
    if 'max_package_size' not in cargo_config:
        raise ValueError("cargo_config missing 'max_package_size'")
    
    # Task 9.2: Handle empty routes list gracefully
    if len(routes) == 0:
        return {}
    
    # Check if we have parsed manifest data (from CSV upload)
    import streamlit as st
    use_lifo_packing = (hasattr(st.session_state, 'parsed_manifest') and 
                        st.session_state.parsed_manifest is not None)
    
    if use_lifo_packing:
        # Use LIFO packing engine with actual package data
        try:
            from dashboard.lifo_packing_engine import LIFOPackingEngine, PackingResult as LIFOPackingResult
            
            packing_results = {}
            
            for route_id, route in enumerate(routes):
                try:
                    # Get vehicle for this route
                    if route_id >= len(vehicle_map):
                        st.warning(
                            f"⚠️ Vehicle profile missing for route {route_id + 1}. "
                            f"Using default Tempo profile."
                        )
                        vehicle = {
                            'name': 'Tempo',
                            'capacity': 50.0,
                            'cargo_length': 2.5,
                            'cargo_width': 1.5,
                            'cargo_height': 1.5
                        }
                    else:
                        vehicle = vehicle_map[route_id]
                    
                    # Extract packages for this route from parsed manifest
                    route_packages = []
                    for customer_id in route:
                        if customer_id == 0:  # Skip depot
                            continue
                        
                        # Find packages for this customer in parsed manifest
                        for destination in st.session_state.parsed_manifest:
                            for package in destination.packages:
                                # Match by customer ID (simplified - in real integration would match by destination)
                                route_packages.append(package)
                    
                    if len(route_packages) == 0:
                        # No packages for this route - create empty result
                        packing_results[route_id] = LIFOPackingResult(
                            placed_packages=[],
                            failed_packages=[],
                            utilization_percent=0.0
                        )
                        continue
                    
                    # Create LIFO packing engine
                    packing_engine = LIFOPackingEngine(
                        vehicle_length_m=vehicle.get('cargo_length', 2.5),
                        vehicle_width_m=vehicle.get('cargo_width', 1.5),
                        vehicle_height_m=vehicle.get('cargo_height', 1.5)
                    )
                    
                    # Pack route with LIFO strategy
                    # Pass stop order (route indices)
                    stop_order = list(range(1, len(route)))  # 1-indexed stops
                    packing_result = packing_engine.pack_route(route_packages, stop_order)
                    
                    packing_results[route_id] = packing_result
                    
                except Exception as e:
                    st.error(f"❌ Error processing route {route_id + 1} with LIFO packing: {str(e)}")
                    continue
            
            return packing_results
            
        except ImportError as e:
            st.error(f"❌ LIFO packing engine not available: {str(e)}")
            st.info("💡 Falling back to standard packing engine.")
            use_lifo_packing = False
    
    # Fall back to existing packing engine
    if not use_lifo_packing:
        try:
            from packing_engine import (
                PackageGenerator,
                FirstFitDecreasingPacker,
                VehicleProfile
            )
        except ImportError as e:
            raise ImportError(f"Failed to import packing_engine: {str(e)}")
        
        packing_results = {}
        
        for route_id, route in enumerate(routes):
            try:
                # Task 9.2: Handle missing vehicle profiles - use defaults with warning
                if route_id >= len(vehicle_map):
                    # This shouldn't happen, but handle gracefully
                    import streamlit as st
                    st.warning(
                        f"⚠️ Vehicle profile missing for route {route_id + 1}. "
                        f"Using default Tempo profile."
                    )
                    vehicle = {
                        'name': 'Tempo',
                        'capacity': 50.0,
                        'cargo_length': 2.5,
                        'cargo_width': 1.5,
                        'cargo_height': 1.5
                    }
                else:
                    vehicle = vehicle_map[route_id]
                
                # Extract customer demands for this route (exclude depot)
                customer_demands = []
                for customer_id in route:
                    if customer_id != 0:  # Skip depot
                        customer_row = df[df['id'] == customer_id]
                        if customer_row.empty:
                            # Task 9.2: Handle missing customer data gracefully
                            import streamlit as st
                            st.warning(
                                f"⚠️ Customer {customer_id} not found in data. Skipping."
                            )
                            continue
                        demand = int(customer_row.iloc[0]['demand'])
                        customer_demands.append((customer_id, demand))
                
                # Task 9.2: Handle empty customer demands (route with only depot)
                if len(customer_demands) == 0:
                    # Create empty packing result
                    from packing_engine import PackingResult
                    packing_results[route_id] = PackingResult(
                        placed=[],
                        overflow=[],
                        utilization=0.0
                    )
                    continue
                
                # Generate packages from demands with validation
                try:
                    package_generator = PackageGenerator(
                        min_dimension=cargo_config['min_package_size'],
                        max_dimension=cargo_config['max_package_size'],
                        random_seed=42  # Use fixed seed for consistency
                    )
                except ValueError as e:
                    # Task 9.1: Display error messages using st.error()
                    import streamlit as st
                    st.error(f"❌ Invalid package dimensions: {str(e)}")
                    raise
                
                packages = package_generator.generate_packages(customer_demands)
                
                # Create vehicle profile with cargo dimensions and validation
                try:
                    vehicle_profile = VehicleProfile(
                        vehicle_type=vehicle['name'],
                        capacity=vehicle['capacity'],
                        cargo_length=vehicle.get('cargo_length'),
                        cargo_width=vehicle.get('cargo_width'),
                        cargo_height=vehicle.get('cargo_height')
                    )
                except ValueError as e:
                    # Task 9.1: Display error messages using st.error()
                    import streamlit as st
                    st.error(
                        f"❌ Invalid cargo dimensions for {vehicle['name']}: {str(e)}"
                    )
                    raise
                
                # Pack packages into cargo bay with validation
                try:
                    packer = FirstFitDecreasingPacker(
                        cargo_length=vehicle_profile.cargo_length,
                        cargo_width=vehicle_profile.cargo_width,
                        cargo_height=vehicle_profile.cargo_height
                    )
                    packing_result = packer.pack(packages)
                except ValueError as e:
                    # Task 9.1: Display error messages using st.error()
                    import streamlit as st
                    st.error(
                        f"❌ Packing failed for route {route_id + 1}: {str(e)}"
                    )
                    raise
                
                # Store result
                packing_results[route_id] = packing_result
                
            except Exception as e:
                # Task 9.2: Handle errors gracefully for individual routes
                import streamlit as st
                st.error(
                    f"❌ Error processing route {route_id + 1}: {str(e)}"
                )
                # Continue with other routes instead of failing completely
                continue
        
        return packing_results


# Route color palette (Cyan, Magenta, Yellow, Green, Orange, Purple)
ROUTE_COLORS = [
    [0, 255, 255],    # Cyan (Route 1)
    [255, 0, 255],    # Magenta (Route 2)
    [255, 255, 0],    # Yellow (Route 3)
    [0, 255, 0],      # Green (Route 4)
    [255, 128, 0],    # Orange (Route 5)
    [128, 0, 255],    # Purple (Route 6)
]


def calculate_route_timing(
    route: List[int],
    df: pd.DataFrame,
    time_matrix: List[List[float]]
) -> List[Dict]:
    """
    Calculate arrival times and waiting times for each customer in a route
    
    Args:
        route: List of customer IDs in visit order
        df: DataFrame with customer data (must have 'id', 'start_window', 'end_window', 'service_time')
        time_matrix: N×N matrix of travel times in minutes
        
    Returns:
        List of dicts with timing information for each customer:
        - customer_id: Customer ID
        - arrival_time: Time of arrival in minutes from start of day
        - waiting_time: Waiting time in minutes (0 if no waiting)
        - departure_time: Time of departure in minutes from start of day
    """
    timing_info = []
    current_time = 0.0
    
    for i, customer_id in enumerate(route):
        # Find customer in DataFrame
        customer_row = df[df['id'] == customer_id].iloc[0]
        
        # Calculate arrival time
        if i == 0:
            # First customer (depot) - arrival time is 0
            arrival_time = 0.0
        else:
            # Get previous customer ID
            prev_customer_id = route[i - 1]
            # Get travel time from time_matrix
            travel_time = time_matrix[prev_customer_id][customer_id]
            arrival_time = current_time + travel_time
        
        # Calculate waiting time
        start_window = customer_row['start_window']
        waiting_time = max(0.0, start_window - arrival_time)
        
        # Calculate departure time
        service_time = customer_row.get('service_time', 10)
        departure_time = arrival_time + waiting_time + service_time
        
        # Update current time for next iteration
        current_time = departure_time
        
        timing_info.append({
            'customer_id': customer_id,
            'arrival_time': arrival_time,
            'waiting_time': waiting_time,
            'departure_time': departure_time
        })
    
    return timing_info


def routes_to_coordinates(
    routes: List[List[int]],
    df: pd.DataFrame
) -> List[Dict]:
    """
    Convert route indices to geographic coordinates for visualization
    
    Args:
        routes: List of routes, each route is list of customer IDs
        df: DataFrame with customer data (must have 'id', 'lat', 'lon' columns)
        
    Returns:
        List of dicts with:
        - route_id: Vehicle/route number (0, 1, 2, ...)
        - path: List of [lon, lat] coordinates
        - color: RGB color tuple for this route
    """
    route_data = []
    
    for route_id, route in enumerate(routes):
        # Map customer IDs to coordinates
        path = []
        for customer_id in route:
            # Find customer in DataFrame
            customer_row = df[df['id'] == customer_id]
            if not customer_row.empty:
                lat = customer_row.iloc[0]['lat']
                lon = customer_row.iloc[0]['lon']
                # Note: pydeck expects [lon, lat] order
                path.append([lon, lat])
        
        # Assign color from palette (cycle if more routes than colors)
        color = ROUTE_COLORS[route_id % len(ROUTE_COLORS)]
        
        route_data.append({
            'route_id': route_id,
            'path': path,
            'color': color
        })
    
    return route_data


# ============================================================================
# Visualization Module
# ============================================================================

def display_route_with_vehicle(route_idx: int, route: List[int], vehicle_map: List[Dict]) -> str:
    """
    Display route with vehicle assignment
    
    Args:
        route_idx: Index of route (0, 1, 2, ...)
        route: List of customer IDs
        vehicle_map: List of vehicle info dicts with keys: name, instance, capacity
    
    Returns:
        Formatted string like "Route 1 (Truck #1 - Cap 50)"
    
    Requirements: 4.2, 4.3, 4.4
    """
    # Validate inputs
    if vehicle_map is None or route_idx >= len(vehicle_map):
        # Fallback if vehicle_map is not available or index is out of bounds
        return f"Route {route_idx + 1}"
    
    # Get vehicle information for this route
    vehicle = vehicle_map[route_idx]
    
    # Format: "Route {i} ({VehicleName} #{instance} - Cap {capacity})"
    return f"Route {route_idx + 1} ({vehicle['name']} #{vehicle['instance']} - Cap {vehicle['capacity']})"


def calculate_fleet_utilization(
    routes: List[List[int]],
    df: pd.DataFrame,
    vehicle_map: List[Dict]
) -> Tuple[float, float, float]:
    """
    Calculate fleet utilization metrics
    
    Args:
        routes: List of routes (each route is list of customer IDs)
        df: DataFrame with customer data (must have 'id' and 'demand' columns)
        vehicle_map: List of vehicle info dicts with keys: name, instance, capacity
    
    Returns:
        Tuple of (total_capacity, total_demand, utilization_percentage)
        - total_capacity: Sum of all vehicle capacities
        - total_demand: Sum of all customer demands served
        - utilization_percentage: (total_demand / total_capacity) × 100
    
    Requirements: 4.5
    """
    # Validate inputs
    if vehicle_map is None or not vehicle_map:
        return 0.0, 0.0, 0.0
    
    if routes is None or not routes:
        return 0.0, 0.0, 0.0
    
    if df is None or df.empty:
        return 0.0, 0.0, 0.0
    
    # Calculate total fleet capacity from vehicle_map
    total_capacity = sum(vehicle['capacity'] for vehicle in vehicle_map)
    
    # Calculate total demand served from routes
    total_demand = 0.0
    for route in routes:
        for customer_id in route:
            # Skip depot (customer_id = 0)
            if customer_id == 0:
                continue
            
            # Find customer in DataFrame and add their demand
            customer_row = df[df['id'] == customer_id]
            if not customer_row.empty:
                total_demand += customer_row.iloc[0]['demand']
    
    # Calculate utilization percentage
    if total_capacity > 0:
        utilization_percentage = (total_demand / total_capacity) * 100.0
    else:
        utilization_percentage = 0.0
    
    return total_capacity, total_demand, utilization_percentage


def create_customer_layer(df: pd.DataFrame, dynamic_customer_ids: List[int] = None) -> pdk.Layer:
    """
    Create pydeck ScatterplotLayer for customer locations with visual distinction for emergency orders
    
    Args:
        df: DataFrame with customer data (must have 'lat', 'lon', 'demand' columns)
        dynamic_customer_ids: List of customer IDs that are emergency orders (default: None)
        
    Returns:
        pdk.Layer object (ScatterplotLayer) for customer visualization
    """
    # Prepare data for pydeck (needs lon, lat order)
    layer_data = df.copy()
    
    # Add column to identify dynamic customers
    if dynamic_customer_ids is None:
        dynamic_customer_ids = []
    layer_data['is_dynamic'] = layer_data['id'].isin(dynamic_customer_ids)
    
    # Add color column: yellow (255,255,0) for dynamic, red (255,0,0) for original
    layer_data['color'] = layer_data['is_dynamic'].apply(
        lambda is_dyn: [255, 255, 0] if is_dyn else [255, 0, 0]
    )
    
    # Create ScatterplotLayer
    layer = pdk.Layer(
        'ScatterplotLayer',
        data=layer_data,
        get_position='[lon, lat]',
        get_color='color',  # Use color column
        get_radius='demand * 50',  # Radius proportional to demand
        pickable=True,
        auto_highlight=True
    )
    
    return layer


def create_route_layers(route_data: List[Dict]) -> List[pdk.Layer]:
    """
    Create PathLayer for each route
    
    Args:
        route_data: List of dicts with 'route_id', 'path', and 'color' keys
        
    Returns:
        List of pdk.Layer objects (PathLayer) for route visualization
    """
    layers = []
    
    for route in route_data:
        # Create PathLayer for this route
        layer = pdk.Layer(
            'PathLayer',
            data=[route],  # PathLayer expects list of objects with 'path' key
            get_path='path',
            get_color='color',
            width_scale=1,
            width_min_pixels=3,
            pickable=True,
            auto_highlight=True
        )
        layers.append(layer)
    
    return layers


def render_map(
    customer_layer: pdk.Layer,
    route_layers: List[pdk.Layer],
    df: pd.DataFrame
):
    """
    Render pydeck map with all layers
    
    Args:
        customer_layer: ScatterplotLayer for customers
        route_layers: List of PathLayer objects for routes
        df: DataFrame with customer data (used to calculate viewport center)
    """
    # Calculate viewport center from customer coordinates
    center_lat = df['lat'].mean()
    center_lon = df['lon'].mean()
    
    # Create view state
    view_state = pdk.ViewState(
        latitude=center_lat,
        longitude=center_lon,
        zoom=13,  # City view zoom level
        pitch=0
    )
    
    # Combine all layers
    all_layers = [customer_layer] + route_layers
    
    # Create tooltip with conditional EMERGENCY label
    tooltip_html = '''
    <div>
        <b>{is_dynamic, select, true {🚨 EMERGENCY} other {}}</b>
        <div>Customer {id}</div>
        <div>Demand: {demand}</div>
        <div>Time Window: {start_window}-{end_window}</div>
    </div>
    '''
    
    # Create deck with dark map style
    deck = pdk.Deck(
        layers=all_layers,
        initial_view_state=view_state,
        map_style='mapbox://styles/mapbox/dark-v10',
        tooltip={
            'html': tooltip_html,
            'style': {
                'backgroundColor': 'steelblue',
                'color': 'white'
            }
        }
    )
    
    # Render with Streamlit
    st.pydeck_chart(deck)


# ============================================================================
# UI Components Module
# ============================================================================

def render_sidebar() -> Dict:
    """
    Render sidebar with all controls
    
    Returns:
        Dict with:
        - vehicle_profiles: List[Dict] (list of vehicle profiles with name, capacity, quantity)
        - uploaded_file: UploadedFile or None
        - run_solver: bool (button clicked state)
    """
    st.sidebar.header("Configuration")
    
    # Initialize vehicle_profiles in session state if not present
    if 'vehicle_profiles' not in st.session_state:
        st.session_state.vehicle_profiles = [
            {
                "name": "Truck",
                "capacity": 50.0,
                "quantity": 2,
                "cargo_length": get_default_cargo_length("Truck"),
                "cargo_width": get_default_cargo_width("Truck"),
                "cargo_height": get_default_cargo_height("Truck"),
                "fuel_efficiency": 8.0  # km/L
            },
            {
                "name": "Van",
                "capacity": 20.0,
                "quantity": 2,
                "cargo_length": get_default_cargo_length("Van"),
                "cargo_width": get_default_cargo_width("Van"),
                "cargo_height": get_default_cargo_height("Van"),
                "fuel_efficiency": 12.0  # km/L
            },
            {
                "name": "Bike",
                "capacity": 10.0,
                "quantity": 1,
                "cargo_length": get_default_cargo_length("Bike"),
                "cargo_width": get_default_cargo_width("Bike"),
                "cargo_height": get_default_cargo_height("Bike"),
                "fuel_efficiency": 30.0  # km/L
            }
        ]
    
    # Fleet Configuration Section
    st.sidebar.subheader("🚛 Fleet Configuration")
    
    # Display current fleet composition
    if st.session_state.vehicle_profiles:
        st.sidebar.write("**Current Fleet:**")
        for i, profile in enumerate(st.session_state.vehicle_profiles):
            col1, col2 = st.sidebar.columns([3, 1])
            with col1:
                fuel_eff = profile.get('fuel_efficiency', 10.0)
                st.write(f"{profile['name']}: {profile['quantity']}x @ {profile['capacity']} cap, {fuel_eff} km/L")
            with col2:
                # Remove button for each profile
                if st.button("❌", key=f"remove_{i}", help=f"Remove {profile['name']}"):
                    st.session_state.vehicle_profiles.pop(i)
                    st.rerun()
        
        # Calculate and display total fleet size
        total_fleet_size = sum(p['quantity'] for p in st.session_state.vehicle_profiles)
        st.sidebar.info(f"**Total Vehicles:** {total_fleet_size}")
    else:
        st.sidebar.warning("No vehicles configured. Add at least one vehicle profile.")
    
    # Add new vehicle profile section
    with st.sidebar.expander("➕ Add Vehicle Profile", expanded=False):
        # Input fields for new vehicle profile
        new_vehicle_name = st.text_input(
            "Vehicle Name",
            value="Truck",
            key="new_vehicle_name",
            help="Name for this vehicle type (e.g., Truck, Van, Bike)"
        )
        
        new_vehicle_capacity = st.number_input(
            "Capacity",
            min_value=0.1,
            value=20.0,
            step=1.0,
            key="new_vehicle_capacity",
            help="Maximum capacity for this vehicle type"
        )
        
        new_vehicle_quantity = st.number_input(
            "Quantity",
            min_value=1,
            value=1,
            step=1,
            key="new_vehicle_quantity",
            help="Number of vehicles of this type"
        )
        
        # Cargo bay dimension inputs
        st.write("**Cargo Bay Dimensions (meters)**")
        
        # Get default values based on vehicle name
        default_length = get_default_cargo_length(new_vehicle_name)
        default_width = get_default_cargo_width(new_vehicle_name)
        default_height = get_default_cargo_height(new_vehicle_name)
        
        new_cargo_length = st.number_input(
            "Length (m)",
            min_value=0.1,
            value=default_length,
            step=0.1,
            key="new_cargo_length",
            help="Cargo bay length in meters"
        )
        
        new_cargo_width = st.number_input(
            "Width (m)",
            min_value=0.1,
            value=default_width,
            step=0.1,
            key="new_cargo_width",
            help="Cargo bay width in meters"
        )
        
        new_cargo_height = st.number_input(
            "Height (m)",
            min_value=0.1,
            value=default_height,
            step=0.1,
            key="new_cargo_height",
            help="Cargo bay height in meters"
        )
        
        # Fuel efficiency input
        st.write("**Fuel Efficiency**")
        new_fuel_efficiency = st.number_input(
            "Fuel Efficiency (km/L)",
            min_value=0.1,
            value=10.0,
            step=0.5,
            key="new_fuel_efficiency",
            help="Vehicle fuel efficiency in kilometers per liter"
        )
        
        # Add Vehicle button
        if st.button("Add Vehicle", type="secondary", use_container_width=True):
            # Create new profile with cargo dimensions and fuel efficiency
            new_profile = {
                "name": new_vehicle_name,
                "capacity": float(new_vehicle_capacity),
                "quantity": int(new_vehicle_quantity),
                "cargo_length": float(new_cargo_length),
                "cargo_width": float(new_cargo_width),
                "cargo_height": float(new_cargo_height),
                "fuel_efficiency": float(new_fuel_efficiency)
            }
            
            # Validate the new profile
            validation_errors = validate_vehicle_profiles([new_profile])
            
            if validation_errors:
                # Display validation errors
                for error in validation_errors:
                    st.error(error)
            else:
                # Add to vehicle_profiles list
                st.session_state.vehicle_profiles.append(new_profile)
                st.success(f"✅ Added {new_vehicle_quantity}x {new_vehicle_name}")
                st.rerun()
    
    st.sidebar.header("Data Source")
    
    # File uploader for CSV manifest (new feature)
    uploaded_manifest = st.sidebar.file_uploader(
        "Upload Package Manifest CSV",
        type=['csv'],
        help="CSV file with package details: Order ID, Source Name, Destination Name, Latitude, Longitude, Length (cm), Width (cm), Height (cm), Weight (kg), Fragile, This Side Up",
        key="manifest_uploader"
    )
    
    # File uploader for customer CSV (existing feature)
    uploaded_file = st.sidebar.file_uploader(
        "Upload Customer CSV",
        type=['csv'],
        help="CSV file with columns: id, lat, lon, demand, start_window, end_window",
        key="customer_uploader"
    )
    
    # Run solver button
    run_solver = st.sidebar.button(
        "Run Solver",
        type="primary",
        use_container_width=True
    )
    
    return {
        'vehicle_profiles': st.session_state.vehicle_profiles,
        'uploaded_file': uploaded_file,
        'uploaded_manifest': uploaded_manifest,
        'run_solver': run_solver
    }


def render_operations_config() -> Dict[str, float]:
    """
    Render operations configuration expander in sidebar
    
    Creates a sidebar expander with three number inputs for cost parameters:
    fuel price, vehicle mileage, and driver wage. All inputs have validation
    to ensure positive values greater than zero.
    
    Returns:
        Dict with keys: 'fuel_price', 'vehicle_mileage', 'driver_wage'
        All values are floats representing the cost parameters
    
    Requirements: 2.1, 2.2, 2.3, 2.4, 2.6
    """
    with st.sidebar.expander("⚙️ Operations Config"):
        # Fuel price input (₹ per liter)
        fuel_price = st.number_input(
            "Fuel Price (₹/L)",
            min_value=0.01,
            value=100.0,
            step=1.0,
            help="Cost per liter of fuel in rupees"
        )
        
        # Vehicle mileage input (km per liter)
        vehicle_mileage = st.number_input(
            "Vehicle Mileage (km/L)",
            min_value=0.01,
            value=10.0,
            step=0.1,
            help="Vehicle fuel efficiency in kilometers per liter"
        )
        
        # Driver wage input (₹ per hour)
        driver_wage = st.number_input(
            "Driver Wage (₹/hour)",
            min_value=0.01,
            value=500.0,
            step=10.0,
            help="Hourly wage for driver in rupees"
        )
    
    # Validate all parameters are positive (Streamlit's min_value handles this, but double-check)
    if fuel_price <= 0 or vehicle_mileage <= 0 or driver_wage <= 0:
        st.sidebar.error("❌ All cost parameters must be positive numbers greater than zero")
        # Return default values if validation fails
        return {
            'fuel_price': 100.0,
            'vehicle_mileage': 10.0,
            'driver_wage': 500.0
        }
    
    return {
        'fuel_price': fuel_price,
        'vehicle_mileage': vehicle_mileage,
        'driver_wage': driver_wage
    }


def render_cargo_config() -> Dict[str, float]:
    """
    Render cargo configuration expander in sidebar
    
    Creates a sidebar expander with two number inputs for package dimension
    constraints: minimum and maximum package size. All inputs have validation
    to ensure positive values and that min < max.
    
    Also includes a checkbox to enable/disable 3D packing validation.
    
    Returns:
        Dict with keys: 'min_package_size', 'max_package_size', 'enable_3d_packing'
        All dimension values are floats representing dimensions in meters
        enable_3d_packing is a boolean
    
    Requirements: 2.2, 6.3, 6.4, 6.5
    """
    # Initialize cargo config in session state if not present
    if 'min_package_size' not in st.session_state:
        st.session_state.min_package_size = 0.3
    if 'max_package_size' not in st.session_state:
        st.session_state.max_package_size = 0.8
    if 'enable_3d_packing' not in st.session_state:
        st.session_state.enable_3d_packing = True  # Enabled by default
    
    with st.sidebar.expander("📦 Cargo Config"):
        # Checkbox to enable/disable 3D packing validation - Task 8.2
        enable_3d_packing = st.checkbox(
            "Enable 3D Packing Validation",
            value=st.session_state.enable_3d_packing,
            help="When enabled, validates that packages physically fit in cargo bays after routing"
        )
        
        # Store checkbox state
        st.session_state.enable_3d_packing = enable_3d_packing
        
        # Min package size input (meters)
        min_package_size = st.number_input(
            "Min Package Size (m)",
            min_value=0.01,
            value=st.session_state.min_package_size,
            step=0.1,
            help="Minimum dimension for generated packages in meters",
            disabled=not enable_3d_packing  # Disable if 3D packing is off
        )
        
        # Max package size input (meters)
        max_package_size = st.number_input(
            "Max Package Size (m)",
            min_value=0.01,
            value=st.session_state.max_package_size,
            step=0.1,
            help="Maximum dimension for generated packages in meters",
            disabled=not enable_3d_packing  # Disable if 3D packing is off
        )
        
        # Validate min < max
        if min_package_size >= max_package_size:
            st.error("❌ Min package size must be less than max package size")
            # Return previous valid values
            return {
                'min_package_size': st.session_state.min_package_size,
                'max_package_size': st.session_state.max_package_size,
                'enable_3d_packing': enable_3d_packing
            }
        
        # Store valid values in session state
        st.session_state.min_package_size = min_package_size
        st.session_state.max_package_size = max_package_size
    
    return {
        'min_package_size': min_package_size,
        'max_package_size': max_package_size,
        'enable_3d_packing': enable_3d_packing
    }


def render_financial_overview(
    fleet_metrics: FleetMetrics,
    route_metrics: List[RouteMetrics]
):
    """
    Render financial overview section with metrics
    
    Displays comprehensive financial metrics in a two-row layout using
    Streamlit's metric components. The first row shows cost breakdown
    (total, fuel, labor), and the second row shows operational metrics
    (distance, duration, efficiency KPIs).
    
    Args:
        fleet_metrics: Aggregated fleet metrics (FleetMetrics object)
        route_metrics: List of per-route metrics (List[RouteMetrics])
    
    UI Structure:
        st.subheader("💰 Financial Overview")
        
        Row 1 (3 columns):
            - Total Cost (₹)
            - Fuel Cost (₹)
            - Labor Cost (₹)
        
        Row 2 (4 columns):
            - Total Distance (km)
            - Total Duration (hours)
            - Cost per km (₹/km)
            - Cost per Delivery (₹/delivery)
    
    Requirements: 1.6, 5.7
    """
    st.subheader("💰 Financial Overview")
    
    # Row 1: Cost breakdown (3 columns)
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            label="Total Cost",
            value=f"₹{fleet_metrics.total_cost:,.2f}"
        )
    
    with col2:
        st.metric(
            label="Fuel Cost",
            value=f"₹{fleet_metrics.total_fuel_cost:,.2f}"
        )
    
    with col3:
        st.metric(
            label="Labor Cost",
            value=f"₹{fleet_metrics.total_labor_cost:,.2f}"
        )
    
    # Row 2: Operational metrics and KPIs (4 columns)
    col4, col5, col6, col7 = st.columns(4)
    
    with col4:
        st.metric(
            label="Total Distance",
            value=f"{fleet_metrics.total_distance_km:,.2f} km"
        )
    
    with col5:
        st.metric(
            label="Total Duration",
            value=f"{fleet_metrics.total_duration_hours:,.2f} hrs"
        )
    
    with col6:
        st.metric(
            label="Cost per km",
            value=f"₹{fleet_metrics.cost_per_km:,.2f}/km"
        )
    
    with col7:
        st.metric(
            label="Cost per Delivery",
            value=f"₹{fleet_metrics.cost_per_delivery:,.2f}/delivery"
        )


def render_cost_analysis_chart(route_metrics: List[RouteMetrics]):
    """
    Render bar chart comparing cost per route
    
    Creates a stacked bar chart showing fuel cost and labor cost breakdown
    for each route. The chart helps identify which routes are most expensive
    and visualizes the cost composition.
    
    Args:
        route_metrics: List of per-route metrics (List[RouteMetrics])
    
    UI Structure:
        st.subheader("📊 Cost Analysis by Route")
        
        Create DataFrame:
            columns: ['Route', 'Fuel Cost', 'Labor Cost']
            rows: One per route
        
        Display stacked bar chart using st.bar_chart()
        X-axis: Route ID
        Y-axis: Cost (₹)
        Colors: Different colors for Fuel vs Labor
    
    Requirements: 4.2, 4.3, 4.4
    """
    st.subheader("📊 Cost Analysis by Route")
    
    # Handle edge case: empty route_metrics list
    if not route_metrics:
        st.info("No route data available for cost analysis")
        return
    
    # Create DataFrame from route_metrics
    chart_data = []
    for metrics in route_metrics:
        chart_data.append({
            'Route': f"Route {metrics.route_id + 1}",
            'Fuel Cost': metrics.fuel_cost,
            'Labor Cost': metrics.labor_cost
        })
    
    df_chart = pd.DataFrame(chart_data)
    
    # Set Route as index for proper x-axis labeling
    df_chart = df_chart.set_index('Route')
    
    # Display stacked bar chart
    st.bar_chart(df_chart)


def render_chaos_controls() -> Tuple[bool, bool]:
    """
    Render chaos mode controls in sidebar
    
    Creates UI controls for emergency order injection and simulation reset.
    Displays a header and two buttons for chaos mode operations.
    
    Returns:
        Tuple of (inject_button, reset_button) states:
        - inject_button: True if "Inject Emergency Order" button was clicked
        - reset_button: True if "Reset Simulation" button was clicked
    
    Requirements: 1.1, 4.3
    """
    st.sidebar.header("🚨 Chaos Mode")
    
    # Display status indicator if chaos mode is active
    if st.session_state.chaos_mode_active and len(st.session_state.dynamic_customers) > 0:
        num_emergency_orders = len(st.session_state.dynamic_customers)
        st.sidebar.info(f"🚨 **Active Emergency Orders: {num_emergency_orders}**")
    
    inject_button = st.sidebar.button(
        "🚨 Inject Emergency Order",
        type="secondary",
        use_container_width=True,
        help="Add a random emergency order and re-optimize routes"
    )
    
    reset_button = st.sidebar.button(
        "🔄 Reset Simulation",
        type="secondary",
        use_container_width=True,
        help="Clear all injected orders and return to original state"
    )
    
    return inject_button, reset_button


def render_download_button(
    routes: List[List[int]],
    df: pd.DataFrame,
    time_matrix: List[List[float]]
):
    """
    Render download button for driver manifests
    
    Creates a download button in the sidebar that generates a CSV file
    containing driver manifests for all routes. The button is disabled
    when no routes are available.
    
    Args:
        routes: List of routes (each route is list of customer IDs)
        df: DataFrame with customer data
        time_matrix: N×N matrix of travel times in minutes
    
    UI Structure:
        st.sidebar.download_button(
            label="📥 Download Driver Manifests",
            data=csv_data,
            file_name=f"fleet_manifest_{timestamp}.csv",
            mime="text/csv"
        )
    
    Button is disabled if routes is None or empty
    
    Requirements: 3.2, 3.5
    """
    # Check if routes exist and are not empty
    button_disabled = routes is None or len(routes) == 0
    
    if button_disabled:
        # Display disabled button with help text
        st.sidebar.download_button(
            label="📥 Download Driver Manifests",
            data="",
            file_name="fleet_manifest.csv",
            mime="text/csv",
            disabled=True,
            use_container_width=True,
            help="Run the solver first to generate routes"
        )
    else:
        try:
            # Validate inputs before generating manifest
            if df is None or df.empty:
                st.sidebar.error("❌ Customer data is missing")
                return
            
            if time_matrix is None:
                st.sidebar.error("❌ Time matrix is missing")
                return
            
            # Generate driver manifest DataFrame
            manifest_df = generate_driver_manifest(routes, df, time_matrix)
            
            # Convert DataFrame to CSV string
            csv_data = manifest_df.to_csv(index=False)
            
            # Generate timestamp for filename
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"fleet_manifest_{timestamp}.csv"
            
            # Display enabled download button
            st.sidebar.download_button(
                label="📥 Download Driver Manifests",
                data=csv_data,
                file_name=filename,
                mime="text/csv",
                use_container_width=True,
                help="Download CSV file with driver manifests for all routes"
            )
        except Exception as e:
            st.sidebar.error(f"❌ Error generating manifest: {str(e)}")


def show_reoptimization_toast(execution_time_ms: float):
    """
    Display toast notification with re-optimization time
    
    Shows a temporary notification indicating successful fleet re-routing
    with the execution time in milliseconds. Uses lightning bolt icon
    for visual distinction.
    
    Args:
        execution_time_ms: Solver execution time in milliseconds
    
    Requirements: 2.1
    """
    st.toast(
        f"⚡ Fleet Re-routed in {execution_time_ms:.2f}ms!",
        icon="⚡"
    )


def render_metrics(execution_time_ms: float):
    """
    Display performance metrics in prominent cards
    
    Args:
        execution_time_ms: Solver execution time in milliseconds
    """
    st.metric(
        label="Solver Execution Time (ms)",
        value=f"{execution_time_ms:.2f}"
    )


def main():
    """Entry point for Streamlit application"""
    # Task 7.1: Set up Streamlit page configuration
    st.set_page_config(
        page_title="High-Frequency Logistics Dashboard",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # --- Session State Initialization ---
    if 'routes' not in st.session_state:
        st.session_state.routes = None
    if 'time_matrix' not in st.session_state:
        st.session_state.time_matrix = None
    if 'execution_time_ms' not in st.session_state:
        st.session_state.execution_time_ms = None
    if 'original_customers' not in st.session_state:
        st.session_state.original_customers = None
    if 'dynamic_customers' not in st.session_state:
        st.session_state.dynamic_customers = []
    if 'chaos_mode_active' not in st.session_state:
        st.session_state.chaos_mode_active = False
    if 'current_time' not in st.session_state:
        st.session_state.current_time = 0.0
    if 'reoptimization_times' not in st.session_state:
        st.session_state.reoptimization_times = []
    if 'packing_results' not in st.session_state:
        st.session_state.packing_results = None  # Task 8.1: Store packing results
    
    # Initialize chaos mode state
    initialize_chaos_state()
    
    # Display error if vrp_core failed to load
    if vrp_core is None:
        st.warning(vrp_core_error)
        st.info(
            "**Dashboard Demo Mode**\n\n"
            "The dashboard is running in demo mode. You can:\n"
            "- ✅ View demo customer data\n"
            "- ✅ Upload and validate CSV files\n"
            "- ✅ Explore the interactive map\n"
            "- ✅ Test all UI components\n"
            "- ❌ Solver execution not available\n\n"
            "The C++ solver has been verified separately and works correctly."
        )
        # Don't stop - allow demo mode to continue
    
    # Task 7.2: Main application flow
    
    # Display title and branding
    st.title("🚚 High-Frequency Logistics Dashboard")
    st.markdown("*Optimized Vehicle Routing with Real-Time Visualization*")
    
    # Render sidebar and get user inputs
    config = render_sidebar()
    
    # Render chaos mode controls
    inject_button, reset_button = render_chaos_controls()
    
    # Render operations config and get cost parameters
    cost_config = render_operations_config()
    
    # Render cargo config and get package dimension parameters
    cargo_config = render_cargo_config()
    
    # Render download button for driver manifests
    # Note: This needs to be called after we have routes, time_matrix, and df
    # We'll call it later in the flow after data is loaded
    
    # Load data: use uploaded CSV if provided, else use demo data
    try:
        # Initialize session state for parsed manifest data
        if 'parsed_manifest' not in st.session_state:
            st.session_state.parsed_manifest = None
        
        # Handle manifest CSV upload (new feature)
        if config.get('uploaded_manifest') is not None:
            st.info("📦 Processing package manifest CSV...")
            
            # Import CSV parser
            from dashboard.csv_parser import CSVParser
            
            # Save uploaded file temporarily
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix='.csv', mode='wb') as tmp_file:
                tmp_file.write(config['uploaded_manifest'].getvalue())
                tmp_path = tmp_file.name
            
            # Parse manifest
            parser = CSVParser()
            destinations, error_message = parser.parse_manifest(tmp_path)
            
            # Clean up temp file
            import os
            os.unlink(tmp_path)
            
            if error_message:
                # Display validation error
                st.error(f"❌ Manifest Validation Error: {error_message}")
                st.info("💡 Please check your CSV file format and data values.")
                st.session_state.parsed_manifest = None
            else:
                # Success! Store parsed manifest
                st.session_state.parsed_manifest = destinations
                total_packages = sum(len(dest.packages) for dest in destinations)
                st.success(f"✅ Manifest parsed successfully! {len(destinations)} destinations, {total_packages} packages")
                
                # Display manifest preview
                with st.expander("📦 View Parsed Manifest", expanded=False):
                    for dest in destinations:
                        st.write(f"**{dest.name}** ({dest.latitude}, {dest.longitude})")
                        st.write(f"  Total Weight: {dest.total_weight_kg:.2f} kg")
                        st.write(f"  Packages: {len(dest.packages)}")
                        for pkg in dest.packages:
                            special = []
                            if pkg.fragile:
                                special.append("⚠️ FRAGILE")
                            if pkg.this_side_up:
                                special.append("⬆️ THIS SIDE UP")
                            special_str = " ".join(special) if special else ""
                            st.write(f"    - {pkg.order_id}: {pkg.weight_kg:.2f} kg, {pkg.length_m*100:.0f}x{pkg.width_m*100:.0f}x{pkg.height_m*100:.0f} cm {special_str}")
                        st.write("---")
        
        # Handle customer CSV upload (existing feature)
        if config['uploaded_file'] is not None:
            st.info("📁 Using uploaded CSV data")
            df = load_customer_csv(config['uploaded_file'])
            # Store as original customers if first load
            if st.session_state.original_customers is None:
                st.session_state.original_customers = df
        else:
            st.info("🎲 Using demo dataset (Mumbai/Bandra area)")
            df = generate_demo_data()
            # Store as original customers if first load
            if st.session_state.original_customers is None:
                st.session_state.original_customers = df
        
        # If chaos mode is active, use combined customer list for visualization
        if st.session_state.chaos_mode_active:
            df = get_current_customers()
            st.info(f"🚨 Chaos Mode Active: {len(st.session_state.dynamic_customers)} emergency order(s) injected")
        
        # Display data preview
        with st.expander("📊 View Customer Data", expanded=False):
            st.dataframe(df, use_container_width=True)
        
        # Render download button in sidebar (after data is loaded)
        # Pass current routes, df, and time_matrix from session state
        render_download_button(
            routes=st.session_state.routes,
            df=df,
            time_matrix=st.session_state.time_matrix
        )
        
    except ValueError as e:
        st.error(f"❌ Data Loading Error: {str(e)}")
        st.stop()
    except Exception as e:
        st.error(f"❌ Unexpected Error: {str(e)}")
        st.stop()
    
    # Initialize session state for routes and execution time
    if 'routes' not in st.session_state:
        st.session_state.routes = None
        st.session_state.execution_time_ms = None
        st.session_state.time_matrix = None
    
    # Initialize vehicle_map in session state if not present
    if 'vehicle_map' not in st.session_state:
        st.session_state.vehicle_map = None
    
    # Handle emergency order injection
    if inject_button:
        try:
            with st.spinner("🚨 Injecting emergency order and re-optimizing..."):
                # Get current customers (original + dynamic)
                current_customers = get_current_customers()
                
                # Generate new emergency order
                new_order = generate_emergency_order(
                    current_customers,
                    st.session_state.current_time
                )
                
                # Store previous solution before re-optimization (for infeasibility handling)
                previous_routes = st.session_state.routes
                previous_execution_time = st.session_state.execution_time_ms
                previous_time_matrix = st.session_state.time_matrix
                
                # Append to dynamic customers list
                st.session_state.dynamic_customers.append(new_order)
                st.session_state.chaos_mode_active = True
                
                # Merge customers and convert to Customer objects
                combined_customers = get_current_customers()
                customers = dataframe_to_customers(combined_customers)
                
                # Flatten and sort fleet configuration
                vehicle_capacities, vehicle_map = flatten_and_sort_fleet(config['vehicle_profiles'])
                
                # Call solver with updated customer list
                start_time = time.perf_counter()
                routes, execution_time_ms, time_matrix = solve_routing(
                    customers,
                    vehicle_capacities,
                    combined_customers
                )
                end_time = time.perf_counter()
                
                # Check for infeasibility: routes are empty or incomplete
                total_customers_in_routes = sum(len(route) for route in routes) if routes else 0
                expected_customers = len(combined_customers)
                is_infeasible = not routes or total_customers_in_routes < expected_customers
                
                if is_infeasible:
                    # Keep previous solution and display warning
                    st.session_state.routes = previous_routes
                    st.session_state.execution_time_ms = previous_execution_time
                    st.session_state.time_matrix = previous_time_matrix
                    
                    # Display warning toast
                    st.toast(
                        "⚠️ Emergency order could not be fully integrated. Showing best available solution.",
                        icon="⚠️"
                    )
                    
                    st.warning(f"⚠️ Emergency order #{new_order.iloc[0]['id']} added to customer list but could not be fully routed due to constraints.")
                else:
                    # Update session state with new routes and time matrix
                    st.session_state.routes = routes
                    st.session_state.execution_time_ms = execution_time_ms
                    st.session_state.time_matrix = time_matrix
                    st.session_state.vehicle_map = vehicle_map
                    
                    # Task 8.1: Run packing validation if enabled
                    if cargo_config['enable_3d_packing'] and routes:
                        try:
                            # Task 9.2: Skip packing if routes are empty (VRP solver failure)
                            if not routes or all(len(route) <= 1 for route in routes):
                                st.warning(
                                    "⚠️ Skipping 3D packing validation: No valid routes generated."
                                )
                                st.session_state.packing_results = None
                            else:
                                packing_results = validate_packing_for_routes(
                                    routes=routes,
                                    df=combined_customers,
                                    vehicle_map=vehicle_map,
                                    cargo_config=cargo_config
                                )
                                st.session_state.packing_results = packing_results
                        except ValueError as e:
                            # Task 9.1: Display validation error messages
                            st.error(f"❌ Packing validation error: {str(e)}")
                            st.session_state.packing_results = None
                        except ImportError as e:
                            # Task 9.2: Handle missing packing engine module
                            st.error(f"❌ Packing engine not available: {str(e)}")
                            st.session_state.packing_results = None
                        except Exception as e:
                            st.error(f"❌ Packing validation failed: {str(e)}")
                            st.session_state.packing_results = None
                    else:
                        st.session_state.packing_results = None
                    
                    # Track re-optimization time for chaos mode statistics
                    st.session_state.reoptimization_times.append(execution_time_ms)
                    
                    # Show performance toast notification
                    show_reoptimization_toast(execution_time_ms)
                    
                    st.success(f"✅ Emergency order #{new_order.iloc[0]['id']} injected successfully!")
                
                # CRITICAL FIX: Force page rerun to update df with new emergency order
                # This ensures the visualization section uses the updated combined customer list
                st.rerun()
                
        except RuntimeError as e:
            st.error(f"❌ Injection Error: {str(e)}")
        except Exception as e:
            st.error(f"❌ Emergency Order Injection Failed: {str(e)}")
    
    # Handle reset simulation button
    if reset_button:
        handle_reset_button()
    
    # If "Run Solver" clicked: convert data, call solve_routing(), display metrics
    if config['run_solver']:
        try:
            # Validate vehicle profiles before running solver
            validation_errors = validate_vehicle_profiles(config['vehicle_profiles'])
            
            if validation_errors:
                # Display validation errors
                st.error("❌ Invalid fleet configuration:")
                for error in validation_errors:
                    st.error(f"  • {error}")
            elif not config['vehicle_profiles']:
                # Empty fleet configuration
                st.warning("⚠️ Fleet configuration is empty. Please add at least one vehicle profile.")
            else:
                with st.spinner("🔄 Running VRP solver..."):
                    # Convert DataFrame to Customer objects
                    customers = dataframe_to_customers(df)
                    
                    # Flatten and sort fleet configuration
                    vehicle_capacities, vehicle_map = flatten_and_sort_fleet(config['vehicle_profiles'])
                    
                    # Call solver (it will generate OSRM or Haversine time_matrix internally)
                    routes, execution_time_ms, time_matrix = solve_routing(
                        customers,
                        vehicle_capacities,
                        df
                    )
                    
                    # Store in session state (use the ACTUAL time_matrix from solver)
                    st.session_state.routes = routes
                    st.session_state.execution_time_ms = execution_time_ms
                    st.session_state.time_matrix = time_matrix
                    st.session_state.vehicle_map = vehicle_map
                    
                    # Task 8.1: Run packing validation if enabled
                    if cargo_config['enable_3d_packing'] and routes:
                        with st.spinner("📦 Validating 3D packing..."):
                            try:
                                # Task 9.2: Skip packing if routes are empty (VRP solver failure)
                                if not routes or all(len(route) <= 1 for route in routes):
                                    st.warning(
                                        "⚠️ Skipping 3D packing validation: No valid routes generated. "
                                        "This may be due to capacity or time window constraints."
                                    )
                                    st.session_state.packing_results = None
                                else:
                                    packing_results = validate_packing_for_routes(
                                        routes=routes,
                                        df=df,
                                        vehicle_map=vehicle_map,
                                        cargo_config=cargo_config
                                    )
                                    st.session_state.packing_results = packing_results
                                    
                                    # Check for overflow and display warning
                                    total_overflow = sum(
                                        len(result.overflow) 
                                        for result in packing_results.values()
                                    )
                                    if total_overflow > 0:
                                        st.warning(
                                            f"⚠️ **3D Packing Validation:** {total_overflow} package(s) "
                                            f"could not fit in cargo bays. Check the Cargo View tab for details."
                                        )
                                    else:
                                        st.success("✅ All packages fit successfully in cargo bays!")
                            except ValueError as e:
                                # Task 9.1: Display validation error messages
                                st.error(f"❌ Packing validation error: {str(e)}")
                                st.info("💡 Check your cargo configuration and package dimensions.")
                                st.session_state.packing_results = None
                            except ImportError as e:
                                # Task 9.2: Handle missing packing engine module
                                st.error(f"❌ Packing engine not available: {str(e)}")
                                st.info("💡 Ensure packing_engine.py is in the dashboard directory.")
                                st.session_state.packing_results = None
                            except Exception as e:
                                st.error(f"❌ Packing validation failed: {str(e)}")
                                st.session_state.packing_results = None
                    else:
                        # Clear packing results if 3D packing is disabled
                        st.session_state.packing_results = None
                    
                    st.success("✅ Solver completed successfully!")
                
        except RuntimeError as e:
            st.error(f"❌ Solver Error: {str(e)}")
        except Exception as e:
            st.error(f"❌ Solver Execution Failed: {str(e)}")
    
    # Display metrics if solver has been run
    if st.session_state.execution_time_ms is not None:
        st.subheader("📈 Performance Metrics")
        
        # Determine number of columns based on chaos mode status
        if st.session_state.chaos_mode_active and len(st.session_state.dynamic_customers) > 0:
            # Show 5 columns when chaos mode is active
            col1, col2, col3, col4, col5 = st.columns(5)
        else:
            # Show 3 columns for normal mode
            col1, col2, col3 = st.columns(3)
            col4, col5 = None, None
        
        with col1:
            render_metrics(st.session_state.execution_time_ms)
        
        with col2:
            if st.session_state.routes:
                st.metric(
                    label="Number of Routes",
                    value=len(st.session_state.routes)
                )
        
        with col3:
            if st.session_state.routes:
                total_customers = sum(len(route) for route in st.session_state.routes)
                st.metric(
                    label="Total Customers Served",
                    value=total_customers
                )
        
        # Check for unassigned customers and display warning
        if st.session_state.routes is not None:
            # Get current customer data
            current_df = get_current_customers()
            
            # Detect unassigned customers
            unassigned_customers = detect_unassigned_customers(
                st.session_state.routes,
                current_df
            )
            
            # Display warning if unassigned customers exist
            if unassigned_customers:
                st.warning(
                    f"⚠️ **{len(unassigned_customers)} customer(s) could not be assigned to any route.**\n\n"
                    f"Unassigned customer IDs: {', '.join(map(str, unassigned_customers))}\n\n"
                    f"**Suggestions:**\n"
                    f"- Add more vehicles to the fleet\n"
                    f"- Increase vehicle capacities\n"
                    f"- Adjust customer time windows\n"
                    f"- Reduce customer demands"
                )
        
        # Show chaos mode statistics if active
        if st.session_state.chaos_mode_active and len(st.session_state.dynamic_customers) > 0:
            with col4:
                st.metric(
                    label="Dynamic Orders Injected",
                    value=len(st.session_state.dynamic_customers)
                )
            
            with col5:
                # Calculate average re-optimization time if multiple injections
                if len(st.session_state.reoptimization_times) > 0:
                    avg_reopt_time = sum(st.session_state.reoptimization_times) / len(st.session_state.reoptimization_times)
                    st.metric(
                        label="Avg Re-optimization Time (ms)",
                        value=f"{avg_reopt_time:.2f}"
                    )
                else:
                    st.metric(
                        label="Avg Re-optimization Time (ms)",
                        value="N/A"
                    )
        
        # Display fleet utilization if vehicle_map is available
        if st.session_state.vehicle_map is not None and st.session_state.routes is not None:
            st.subheader("🚛 Fleet Utilization")
            
            # Get current customer data
            current_df = get_current_customers()
            
            # Calculate fleet utilization
            total_capacity, total_demand, utilization_percentage = calculate_fleet_utilization(
                st.session_state.routes,
                current_df,
                st.session_state.vehicle_map
            )
            
            # Display utilization metrics in columns
            util_col1, util_col2, util_col3 = st.columns(3)
            
            with util_col1:
                st.metric(
                    label="Total Fleet Capacity",
                    value=f"{total_capacity:.1f}"
                )
            
            with util_col2:
                st.metric(
                    label="Total Demand Served",
                    value=f"{total_demand:.1f}"
                )
            
            with util_col3:
                st.metric(
                    label="Fleet Utilization",
                    value=f"{utilization_percentage:.1f}%"
                )
    
    # Display financial overview if routes exist
    if st.session_state.routes is not None and len(st.session_state.routes) > 0:
        try:
            # Validate required data is available
            if st.session_state.time_matrix is None:
                st.error("❌ Financial calculations require time matrix data. Please run the solver first.")
            elif st.session_state.vehicle_map is None:
                st.error("❌ Financial calculations require vehicle data. Please run the solver first.")
            else:
                # Get current customer data
                current_df = get_current_customers()
                
                # Validate customer data
                if current_df is None or current_df.empty:
                    st.error("❌ Customer data is missing. Cannot calculate financial metrics.")
                else:
                    # Validate cost parameters
                    if (cost_config['fuel_price'] <= 0 or 
                        cost_config['driver_wage'] <= 0):
                        st.error("❌ Invalid cost parameters. All values must be positive numbers greater than zero.")
                    else:
                        # Calculate financial metrics using vehicle-specific fuel efficiency
                        from dashboard.financial_engine import FinancialEngine
                        from dashboard.fleet_composer import VehicleType
                        
                        # Create financial engine
                        financial_engine = FinancialEngine(
                            fuel_price_per_L=cost_config['fuel_price'],
                            driver_hourly_wage=cost_config['driver_wage']
                        )
                        
                        # Calculate route costs with vehicle-specific fuel efficiency
                        route_costs = []
                        for route_id, route in enumerate(st.session_state.routes):
                            # Get vehicle for this route
                            if route_id < len(st.session_state.vehicle_map):
                                vehicle_info = st.session_state.vehicle_map[route_id]
                                
                                # Create VehicleType object
                                vehicle = VehicleType(
                                    name=vehicle_info['name'],
                                    capacity_kg=vehicle_info['capacity'],
                                    length_m=vehicle_info.get('cargo_length', 2.5),
                                    width_m=vehicle_info.get('cargo_width', 1.5),
                                    height_m=vehicle_info.get('cargo_height', 1.5),
                                    fuel_efficiency_km_per_L=vehicle_info.get('fuel_efficiency', 10.0),
                                    count=1
                                )
                                
                                # Calculate route distance and duration
                                route_distance_km = calculate_route_distance(
                                    route, st.session_state.time_matrix
                                )
                                route_duration_hours = calculate_route_duration(
                                    route, current_df, st.session_state.time_matrix
                                )
                                
                                # Calculate route cost
                                route_cost = financial_engine.calculate_route_cost(
                                    route_id=route_id,
                                    route_distance_km=route_distance_km,
                                    route_time_hours=route_duration_hours,
                                    vehicle=vehicle
                                )
                                route_costs.append(route_cost)
                        
                        # Generate cost summary
                        cost_summary = financial_engine.generate_cost_summary(route_costs)
                        
                        # Display financial overview
                        st.subheader("💰 Financial Overview")
                        
                        # Row 1: Cost breakdown (3 columns)
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.metric(
                                label="Total Cost",
                                value=f"₹{cost_summary['total_cost']:,.2f}"
                            )
                        
                        with col2:
                            st.metric(
                                label="Fuel Cost",
                                value=f"₹{cost_summary['total_fuel_cost']:,.2f}"
                            )
                        
                        with col3:
                            st.metric(
                                label="Labor Cost",
                                value=f"₹{cost_summary['total_labor_cost']:,.2f}"
                            )
                        
                        # Row 2: Fuel consumption metrics
                        col4, col5 = st.columns(2)
                        
                        with col4:
                            st.metric(
                                label="Total Fuel Consumed",
                                value=f"{cost_summary['total_fuel_consumed_L']:,.2f} L"
                            )
                        
                        with col5:
                            # Calculate average cost per km
                            total_distance = sum(rc.distance_km for rc in route_costs)
                            cost_per_km = cost_summary['total_cost'] / total_distance if total_distance > 0 else 0
                            st.metric(
                                label="Cost per km",
                                value=f"₹{cost_per_km:,.2f}/km"
                            )
                        
                        # Display vehicle-specific efficiency breakdown
                        if cost_summary['vehicle_efficiency_breakdown']:
                            st.subheader("🚛 Vehicle Efficiency Breakdown")
                            
                            efficiency_data = []
                            for vehicle_name, stats in cost_summary['vehicle_efficiency_breakdown'].items():
                                efficiency_data.append({
                                    'Vehicle': vehicle_name,
                                    'Routes': stats['route_count'],
                                    'Distance (km)': f"{stats['total_distance_km']:.2f}",
                                    'Fuel Used (L)': f"{stats['total_fuel_consumed_L']:.2f}",
                                    'Efficiency (km/L)': f"{stats['fuel_efficiency_km_per_L']:.2f}"
                                })
                            
                            efficiency_df = pd.DataFrame(efficiency_data)
                            st.dataframe(efficiency_df, use_container_width=True, hide_index=True)
                        
                        # Display per-route cost breakdown
                        st.subheader("📊 Cost Analysis by Route")
                        
                        # Create detailed route cost table
                        route_cost_data = []
                        for rc in route_costs:
                            route_cost_data.append({
                                'Route': f"Route {rc.route_id + 1}",
                                'Vehicle': rc.vehicle_name,
                                'Distance (km)': f"{rc.distance_km:.2f}",
                                'Time (hrs)': f"{rc.time_hours:.2f}",
                                'Fuel Used (L)': f"{rc.fuel_consumed_L:.2f}",
                                'Fuel Cost (₹)': f"{rc.fuel_cost:.2f}",
                                'Labor Cost (₹)': f"{rc.labor_cost:.2f}",
                                'Total Cost (₹)': f"{rc.total_cost:.2f}"
                            })
                        
                        route_cost_df = pd.DataFrame(route_cost_data)
                        st.dataframe(route_cost_df, use_container_width=True, hide_index=True)
                        
                        # Display cost comparison chart
                        chart_data = []
                        for rc in route_costs:
                            chart_data.append({
                                'Route': f"Route {rc.route_id + 1}",
                                'Fuel Cost': rc.fuel_cost,
                                'Labor Cost': rc.labor_cost
                            })
                        
                        df_chart = pd.DataFrame(chart_data)
                        df_chart = df_chart.set_index('Route')
                        st.bar_chart(df_chart)
                        
        except ValueError as e:
            st.error(f"❌ Validation Error: {str(e)}")
            st.info("💡 Please check your cost parameters and ensure all values are positive.")
        except KeyError as e:
            st.error(f"❌ Data Error: {str(e)}")
            st.info("💡 The customer data may be missing required columns.")
        except Exception as e:
            st.error(f"❌ Financial Calculation Error: {str(e)}")
            st.info("💡 Please try running the solver again or check your input data.")
    
    # Create tabs for different visualizations
    tab1, tab2 = st.tabs(["🗺️ Route Map", "📦 Cargo View"])
    
    # Tab 1: Route Map Visualization
    with tab1:
        st.subheader("🗺️ Route Visualization")
        
        try:
            # CRITICAL: Always use the combined customer dataset for visualization
            # This ensures emergency orders (dynamic customers) are included
            visualization_df = df  # df is already set to get_current_customers() if chaos mode is active
            
            # Extract dynamic customer IDs from session state
            dynamic_customer_ids = []
            if st.session_state.chaos_mode_active and st.session_state.dynamic_customers:
                for dynamic_customer_df in st.session_state.dynamic_customers:
                    dynamic_customer_ids.extend(dynamic_customer_df['id'].tolist())
            
            # Create customer layer with dynamic customer IDs for visual highlighting
            customer_layer = create_customer_layer(visualization_df, dynamic_customer_ids)
            
            # Create route layers if routes exist
            route_layers = []
            if st.session_state.routes is not None:
                route_data = routes_to_coordinates(st.session_state.routes, visualization_df)
                route_layers = create_route_layers(route_data)
            
            # Render map
            render_map(customer_layer, route_layers, visualization_df)
            
            # Display route details if available
            if st.session_state.routes is not None:
                with st.expander("🚛 View Route Details", expanded=False):
                    for route_id, route in enumerate(st.session_state.routes):
                        # Use display_route_with_vehicle() to show route header with vehicle info
                        if st.session_state.vehicle_map is not None:
                            route_header = display_route_with_vehicle(route_id, route, st.session_state.vehicle_map)
                        else:
                            route_header = f"Route {route_id + 1}"
                        
                        st.write(f"**{route_header}:** {' → '.join(map(str, route))}")
                        
                        # Calculate and display timing information if time_matrix is available
                        if st.session_state.time_matrix is not None:
                            timing_info = calculate_route_timing(route, visualization_df, st.session_state.time_matrix)
                            
                            # Get vehicle information for this route
                            vehicle_info = ""
                            if st.session_state.vehicle_map is not None and route_id < len(st.session_state.vehicle_map):
                                vehicle = st.session_state.vehicle_map[route_id]
                                vehicle_info = f"{vehicle['name']} #{vehicle['instance']} (Cap {vehicle['capacity']})"
                            
                            # Get service time for each customer
                            timing_data = []
                            for info in timing_info:
                                customer_id = info['customer_id']
                                customer_row = visualization_df[visualization_df['id'] == customer_id].iloc[0]
                                service_time = customer_row.get('service_time', 10)
                                
                                # Check if this is an emergency order
                                is_emergency = customer_id in dynamic_customer_ids
                                
                                timing_data.append({
                                    'Customer ID': customer_id,
                                    'Vehicle': vehicle_info,
                                    'Arrival Time': f"{info['arrival_time']:.1f} min",
                                    'Service Time': f"{service_time:.1f} min",
                                    'Waiting Time': f"{info['waiting_time']:.1f} min",
                                    'Departure Time': f"{info['departure_time']:.1f} min",
                                    'Is Dynamic': is_emergency
                                })
                            
                            timing_df = pd.DataFrame(timing_data)
                            
                            # Define columns to display (exclude Is Dynamic)
                            display_cols = ['Customer ID', 'Vehicle', 'Arrival Time', 'Service Time', 'Waiting Time', 'Departure Time']
                            
                            # Highlight emergency orders in yellow
                            # Note: We need to check the full DataFrame (with Is Dynamic) for styling logic
                            def highlight_row(row):
                                # Access the original DataFrame to check Is Dynamic status
                                is_dynamic = timing_df.loc[row.name, 'Is Dynamic']
                                color = 'background-color: yellow' if is_dynamic else ''
                                return [color] * len(row)
                            
                            # Step 1: Select display columns FIRST
                            display_df = timing_df[display_cols]
                            
                            # Step 2: Apply styling AFTER column selection
                            styled_df = display_df.style.apply(highlight_row, axis=1)
                            
                            # Step 3: Display the styled DataFrame
                            st.dataframe(styled_df, use_container_width=True, hide_index=True)
                            
                            # Add legend for emergency orders
                            if any(customer_id in dynamic_customer_ids for customer_id in [info['customer_id'] for info in timing_info]):
                                st.caption("💡 Emergency orders are highlighted in yellow")
                        
                        # Add manifest download buttons if manifest data is available
                        if st.session_state.parsed_manifest is not None:
                            st.write("**📥 Download Driver Manifest:**")
                            
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                # CSV Download Button
                                try:
                                    from dashboard.manifest_builder import ManifestBuilder
                                    
                                    manifest_builder = ManifestBuilder()
                                    
                                    # Get packages for this route from parsed manifest
                                    route_packages = []
                                    for customer_id in route:
                                        if customer_id == 0:  # Skip depot
                                            continue
                                        # Find packages for this customer
                                        for destination in st.session_state.parsed_manifest:
                                            route_packages.extend(destination.packages)
                                    
                                    # Generate CSV manifest
                                    csv_content = manifest_builder.generate_csv(
                                        route=route,
                                        packages=route_packages,
                                        destinations=st.session_state.parsed_manifest
                                    )
                                    
                                    # Create download button
                                    from datetime import datetime
                                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                    filename = f"route_{route_id + 1}_manifest_{timestamp}.csv"
                                    
                                    st.download_button(
                                        label="📄 Download CSV",
                                        data=csv_content,
                                        file_name=filename,
                                        mime="text/csv",
                                        key=f"csv_download_{route_id}",
                                        use_container_width=True
                                    )
                                except Exception as e:
                                    st.error(f"❌ CSV generation error: {str(e)}")
                            
                            with col2:
                                # PDF Download Button
                                try:
                                    from dashboard.manifest_builder import ManifestBuilder
                                    from dashboard.financial_engine import FinancialEngine, RouteCost
                                    from dashboard.fleet_composer import VehicleType
                                    
                                    manifest_builder = ManifestBuilder()
                                    
                                    # Get packages for this route from parsed manifest
                                    route_packages = []
                                    for customer_id in route:
                                        if customer_id == 0:  # Skip depot
                                            continue
                                        # Find packages for this customer
                                        for destination in st.session_state.parsed_manifest:
                                            route_packages.extend(destination.packages)
                                    
                                    # Get vehicle info
                                    vehicle_name = "Unknown Vehicle"
                                    if st.session_state.vehicle_map is not None and route_id < len(st.session_state.vehicle_map):
                                        vehicle_info = st.session_state.vehicle_map[route_id]
                                        vehicle_name = f"{vehicle_info['name']} #{vehicle_info['instance']}"
                                        
                                        # Create VehicleType for cost calculation
                                        vehicle = VehicleType(
                                            name=vehicle_info['name'],
                                            capacity_kg=vehicle_info['capacity'],
                                            length_m=vehicle_info.get('cargo_length', 2.5),
                                            width_m=vehicle_info.get('cargo_width', 1.5),
                                            height_m=vehicle_info.get('cargo_height', 1.5),
                                            fuel_efficiency_km_per_L=vehicle_info.get('fuel_efficiency', 10.0),
                                            count=1
                                        )
                                        
                                        # Calculate route cost
                                        route_distance_km = calculate_route_distance(
                                            route, st.session_state.time_matrix
                                        )
                                        route_duration_hours = calculate_route_duration(
                                            route, visualization_df, st.session_state.time_matrix
                                        )
                                        
                                        financial_engine = FinancialEngine(
                                            fuel_price_per_L=cost_config['fuel_price'],
                                            driver_hourly_wage=cost_config['driver_wage']
                                        )
                                        
                                        route_cost = financial_engine.calculate_route_cost(
                                            route_id=route_id,
                                            route_distance_km=route_distance_km,
                                            route_time_hours=route_duration_hours,
                                            vehicle=vehicle
                                        )
                                    else:
                                        # Create dummy route cost if vehicle info not available
                                        route_cost = RouteCost(
                                            route_id=route_id,
                                            vehicle_name=vehicle_name,
                                            distance_km=0.0,
                                            time_hours=0.0,
                                            fuel_efficiency_km_per_L=10.0,
                                            fuel_consumed_L=0.0,
                                            fuel_cost=0.0,
                                            labor_cost=0.0,
                                            total_cost=0.0
                                        )
                                    
                                    # Generate PDF manifest
                                    pdf_bytes = manifest_builder.generate_pdf(
                                        route=route,
                                        packages=route_packages,
                                        destinations=st.session_state.parsed_manifest,
                                        vehicle_name=vehicle_name,
                                        route_cost=route_cost
                                    )
                                    
                                    # Create download button
                                    from datetime import datetime
                                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                    filename = f"route_{route_id + 1}_manifest_{timestamp}.pdf"
                                    
                                    st.download_button(
                                        label="📑 Download PDF",
                                        data=pdf_bytes,
                                        file_name=filename,
                                        mime="application/pdf",
                                        key=f"pdf_download_{route_id}",
                                        use_container_width=True
                                    )
                                except Exception as e:
                                    st.error(f"❌ PDF generation error: {str(e)}")
                        
                        st.write("---")  # Separator between routes
            
        except Exception as e:
            st.error(f"❌ Visualization Error: {str(e)}")
    
    # Tab 2: Cargo Loading Visualization
    with tab2:
        st.subheader("📦 Cargo Loading Plan")
        
        # Check if 3D packing is enabled
        if not cargo_config['enable_3d_packing']:
            st.info(
                "📦 **3D Packing Validation is disabled.**\n\n"
                "Enable it in the sidebar (📦 Cargo Config) to validate that packages "
                "physically fit in cargo bays and view 3D loading visualizations."
            )
        # Check if routes exist
        elif st.session_state.routes is None or len(st.session_state.routes) == 0:
            st.info("🚛 Run the solver first to generate routes and view cargo loading plans.")
        # Check if packing results exist
        elif st.session_state.packing_results is None:
            st.info("📦 Run the solver with 3D packing enabled to view cargo loading plans.")
        else:
            try:
                # Import packing engine components
                from packing_engine import (
                    VehicleProfile,
                    CargoVisualizationRenderer
                )
                
                # Get current customer data
                current_df = get_current_customers()
                
                # Task 9.2: Validate that packing results and vehicle map are available
                if st.session_state.vehicle_map is None or len(st.session_state.vehicle_map) == 0:
                    st.error("❌ Vehicle configuration is missing. Please run the solver again.")
                elif len(st.session_state.packing_results) == 0:
                    st.info("📦 No packing results available. Routes may be empty.")
                else:
                    # Vehicle selector for multi-vehicle solutions
                    if len(st.session_state.routes) > 1:
                        # Create vehicle options with names
                        vehicle_options = []
                        for i, vehicle in enumerate(st.session_state.vehicle_map):
                            vehicle_options.append(f"{vehicle['name']} #{vehicle['instance']} (Route {i+1})")
                        
                        selected_vehicle_idx = st.selectbox(
                            "Select Vehicle",
                            range(len(vehicle_options)),
                            format_func=lambda i: vehicle_options[i]
                        )
                    else:
                        selected_vehicle_idx = 0
                    
                    # Task 9.2: Handle invalid vehicle selection - Requirement 6.3
                    if selected_vehicle_idx >= len(st.session_state.vehicle_map):
                        st.error(
                            f"❌ Invalid vehicle selection (index {selected_vehicle_idx}). "
                            f"Defaulting to first vehicle."
                        )
                        selected_vehicle_idx = 0
                    
                    if selected_vehicle_idx not in st.session_state.packing_results:
                        st.error(
                            f"❌ No packing result available for selected vehicle. "
                            f"Please run the solver again."
                        )
                    else:
                        # Get selected vehicle info and packing result
                        selected_vehicle = st.session_state.vehicle_map[selected_vehicle_idx]
                        packing_result = st.session_state.packing_results[selected_vehicle_idx]
                        
                        # Task 9.2: Validate vehicle has cargo dimensions
                        if ('cargo_length' not in selected_vehicle or 
                            'cargo_width' not in selected_vehicle or 
                            'cargo_height' not in selected_vehicle):
                            st.warning(
                                f"⚠️ Cargo dimensions missing for {selected_vehicle['name']}. "
                                f"Using default dimensions."
                            )
                            # Use defaults
                            selected_vehicle['cargo_length'] = get_default_cargo_length(selected_vehicle['name'])
                            selected_vehicle['cargo_width'] = get_default_cargo_width(selected_vehicle['name'])
                            selected_vehicle['cargo_height'] = get_default_cargo_height(selected_vehicle['name'])
                        
                        # Create vehicle profile with cargo dimensions
                        try:
                            vehicle_profile = VehicleProfile(
                                vehicle_type=selected_vehicle['name'],
                                capacity=selected_vehicle['capacity'],
                                cargo_length=selected_vehicle['cargo_length'],
                                cargo_width=selected_vehicle['cargo_width'],
                                cargo_height=selected_vehicle['cargo_height']
                            )
                        except ValueError as e:
                            st.error(f"❌ Invalid vehicle profile: {str(e)}")
                            st.stop()
                        
                        # Display packing summary statistics
                        summary = packing_result.summary()
                        
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            st.metric(
                                label="Total Packages",
                                value=summary['total_packages']
                            )
                        
                        with col2:
                            st.metric(
                                label="Placed Packages",
                                value=summary['placed_packages']
                            )
                        
                        with col3:
                            st.metric(
                                label="Overflow Packages",
                                value=summary['overflow_packages'],
                                delta=None if summary['overflow_packages'] == 0 else "⚠️ Overflow"
                            )
                        
                        with col4:
                            st.metric(
                                label="Cargo Utilization",
                                value=f"{summary['utilization_percent']:.1f}%"
                            )
                        
                        # Display warning if overflow exists
                        if summary['overflow_packages'] > 0:
                            st.warning(
                                f"⚠️ **{summary['overflow_packages']} package(s) could not fit in the cargo bay.**\n\n"
                                f"**Suggestions:**\n"
                                f"- Use a larger vehicle for this route\n"
                                f"- Reduce package sizes (adjust min/max dimensions)\n"
                                f"- Split the route across multiple vehicles"
                            )
                        
                        # Render 3D visualization
                        try:
                            renderer = CargoVisualizationRenderer()
                            vehicle_id = f"{selected_vehicle['name']} #{selected_vehicle['instance']}"
                            fig = renderer.render(vehicle_profile, packing_result, vehicle_id)
                            st.plotly_chart(fig, use_container_width=True)
                        except ImportError as e:
                            st.error(f"❌ Visualization Error: {str(e)}")
                            st.info("Install plotly to enable 3D visualization: `pip install plotly`")
                        except Exception as e:
                            st.error(f"❌ Visualization Error: {str(e)}")
            
            except ImportError as e:
                st.error(f"❌ Failed to import packing engine: {str(e)}")
                st.info("Ensure packing_engine.py is in the dashboard directory.")
            except Exception as e:
                st.error(f"❌ Unexpected error in cargo visualization: {str(e)}")


if __name__ == "__main__":
    main()
