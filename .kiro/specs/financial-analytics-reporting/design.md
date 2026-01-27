# Design Document: Financial Analytics & Reporting

## Overview

The Financial Analytics & Reporting feature extends the existing VRP Dashboard with business intelligence capabilities. This feature transforms the dashboard from a technical routing tool into a comprehensive fleet management platform by adding financial modeling, cost analysis, and operational reporting.

The design follows the existing dashboard architecture pattern with modular functions organized by responsibility. All financial calculations are performed in Python using data from the existing session state (routes, time_matrix, customer data), ensuring seamless integration without modifying the C++ solver.

### Key Design Principles

1. **Non-invasive Integration**: Financial features use existing data structures without modifying the C++ solver
2. **Reactive Calculations**: Financial metrics update automatically when cost parameters change
3. **Modular Architecture**: Financial logic is organized into dedicated functions following existing patterns
4. **Session State Driven**: All calculations derive from st.session_state data (routes, time_matrix)
5. **Windows Compatibility**: Preserves existing DLL loading configuration

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit Dashboard                       │
├─────────────────────────────────────────────────────────────┤
│  Sidebar                │  Main Content Area                 │
│  ┌──────────────────┐  │  ┌──────────────────────────────┐ │
│  │ Existing Controls│  │  │ Existing Metrics             │ │
│  │ - Capacity       │  │  │ - Execution Time             │ │
│  │ - Num Vehicles   │  │  │ - Number of Routes           │ │
│  │ - File Upload    │  │  │ - Customers Served           │ │
│  │ - Run Solver     │  │  └──────────────────────────────┘ │
│  │ - Chaos Mode     │  │                                    │
│  ├──────────────────┤  │  ┌──────────────────────────────┐ │
│  │ NEW: Operations  │  │  │ NEW: Financial Overview      │ │
│  │ Config           │  │  │ - Total Cost                 │ │
│  │ - Fuel Price     │  │  │ - Fuel Cost                  │ │
│  │ - Mileage        │  │  │ - Labor Cost                 │ │
│  │ - Driver Wage    │  │  │ - Cost/km, Cost/Delivery     │ │
│  └──────────────────┘  │  └──────────────────────────────┘ │
│  ┌──────────────────┐  │                                    │
│  │ NEW: Download    │  │  ┌──────────────────────────────┐ │
│  │ Driver Manifests │  │  │ NEW: Cost Analysis Chart     │ │
│  └──────────────────┘  │  │ - Bar chart: Cost per Route  │ │
│                         │  └──────────────────────────────┘ │
│                         │                                    │
│                         │  ┌──────────────────────────────┐ │
│                         │  │ Existing: Route Visualization│ │
│                         │  │ - Map with routes            │ │
│                         │  └──────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

```
Session State (st.session_state)
├── routes: List[List[int]]
├── time_matrix: List[List[float]]
├── execution_time_ms: float
└── (customer DataFrame via get_current_customers())
         │
         ├──> Financial Calculation Module
         │    ├── calculate_route_metrics()
         │    │   └── Returns: List[RouteMetrics]
         │    │       ├── route_id
         │    │       ├── distance_km
         │    │       ├── duration_hours
         │    │       ├── fuel_cost
         │    │       └── labor_cost
         │    │
         │    └── calculate_fleet_metrics()
         │        └── Returns: FleetMetrics
         │            ├── total_distance_km
         │            ├── total_duration_hours
         │            ├── total_fuel_cost
         │            ├── total_labor_cost
         │            ├── total_cost
         │            ├── cost_per_km
         │            └── cost_per_delivery
         │
         ├──> Visualization Module
         │    └── render_financial_overview()
         │        └── Displays metrics using st.metric()
         │
         ├──> Chart Module
         │    └── render_cost_analysis_chart()
         │        └── Displays bar chart using st.bar_chart()
         │
         └──> Export Module
              └── generate_driver_manifest()
                  └── Returns: DataFrame with manifest data
```

## Components and Interfaces

### 1. Financial Calculation Module

#### RouteMetrics (Data Structure)

```python
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
```

#### FleetMetrics (Data Structure)

```python
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
```

#### calculate_route_distance()

```python
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
    
    Algorithm:
        For each consecutive pair (i, j) in route:
            travel_time_minutes = time_matrix[i][j]
            distance_km = (travel_time_minutes / 60) * avg_speed_kmh
        Return sum of all distances
    """
```

#### calculate_route_duration()

```python
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
    
    Algorithm:
        Use existing calculate_route_timing() function to get timing info
        Sum: travel_time + service_time + waiting_time for all stops
        Convert minutes to hours
    """
```

#### calculate_route_metrics()

```python
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
    
    Algorithm:
        1. distance_km = calculate_route_distance(route, time_matrix)
        2. duration_hours = calculate_route_duration(route, df, time_matrix)
        3. fuel_cost = (distance_km / vehicle_mileage) * fuel_price
        4. labor_cost = duration_hours * driver_wage
        5. total_cost = fuel_cost + labor_cost
        6. num_customers = len(route) - 1  # Exclude depot
        7. Return RouteMetrics(...)
    """
```

#### calculate_fleet_metrics()

```python
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
```

### 2. UI Components Module

#### render_operations_config()

```python
def render_operations_config() -> Dict[str, float]:
    """
    Render operations configuration expander in sidebar
    
    Returns:
        Dict with keys: 'fuel_price', 'vehicle_mileage', 'driver_wage'
    
    UI Structure:
        st.sidebar.expander("⚙️ Operations Config"):
            - Number input: Fuel Price (₹/L) [default: 100, min: 0.01]
            - Number input: Vehicle Mileage (km/L) [default: 10, min: 0.01]
            - Number input: Driver Wage (₹/hour) [default: 500, min: 0.01]
    """
```

#### render_financial_overview()

```python
def render_financial_overview(
    fleet_metrics: FleetMetrics,
    route_metrics: List[RouteMetrics]
):
    """
    Render financial overview section with metrics
    
    Args:
        fleet_metrics: Aggregated fleet metrics
        route_metrics: List of per-route metrics
    
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
    """
```

#### render_cost_analysis_chart()

```python
def render_cost_analysis_chart(route_metrics: List[RouteMetrics]):
    """
    Render bar chart comparing cost per route
    
    Args:
        route_metrics: List of per-route metrics
    
    UI Structure:
        st.subheader("📊 Cost Analysis by Route")
        
        Create DataFrame:
            columns: ['Route', 'Total Cost', 'Fuel Cost', 'Labor Cost']
            rows: One per route
        
        Display stacked bar chart using st.bar_chart()
        X-axis: Route ID
        Y-axis: Cost (₹)
        Colors: Different colors for Fuel vs Labor
    """
```

#### render_download_button()

```python
def render_download_button(
    routes: List[List[int]],
    df: pd.DataFrame,
    time_matrix: List[List[float]]
):
    """
    Render download button for driver manifests
    
    Args:
        routes: List of routes
        df: DataFrame with customer data
        time_matrix: N×N matrix of travel times
    
    UI Structure:
        st.sidebar.download_button(
            label="📥 Download Driver Manifests",
            data=csv_data,
            file_name=f"fleet_manifest_{timestamp}.csv",
            mime="text/csv"
        )
    
    Button is disabled if routes is None or empty
    """
```

### 3. Export Module

#### generate_driver_manifest()

```python
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
```

#### format_time()

```python
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
```

## Data Models

### Input Data

The financial analytics module consumes existing data from session state:

```python
# From st.session_state
routes: List[List[int]]  # List of routes, each route is list of customer IDs
time_matrix: List[List[float]]  # N×N matrix of travel times in minutes
execution_time_ms: float  # Solver execution time

# From get_current_customers()
df: pd.DataFrame  # Customer data with columns:
    # - id: int
    # - lat: float
    # - lon: float
    # - demand: float
    # - start_window: float
    # - end_window: float
    # - service_time: float
```

### Configuration Data

```python
# User-configurable cost parameters
fuel_price: float = 100.0  # ₹ per liter
vehicle_mileage: float = 10.0  # km per liter
driver_wage: float = 500.0  # ₹ per hour
avg_speed_kmh: float = 40.0  # km/h (derived from time_matrix)
```

### Output Data

```python
# Per-route metrics
RouteMetrics:
    route_id: int
    distance_km: float
    duration_hours: float
    fuel_cost: float
    labor_cost: float
    total_cost: float
    num_customers: int

# Fleet-level metrics
FleetMetrics:
    total_distance_km: float
    total_duration_hours: float
    total_fuel_cost: float
    total_labor_cost: float
    total_cost: float
    cost_per_km: float
    cost_per_delivery: float
    num_routes: int
    num_customers: int

# Driver manifest
ManifestRow:
    Route_ID: int
    Stop_Number: int
    Customer_ID: int
    Arrival_Time: str  # "HH:MM"
    Action: str  # "Deliver" or "Pickup"
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Fleet Distance Aggregation

*For any* set of routes and time_matrix, the total fleet distance calculated by `calculate_fleet_metrics()` should equal the sum of distances calculated by `calculate_route_distance()` for each individual route.

**Validates: Requirements 1.1**

### Property 2: Fleet Duration Aggregation

*For any* set of routes, customer data, and time_matrix, the total fleet duration calculated by `calculate_fleet_metrics()` should equal the sum of durations calculated by `calculate_route_duration()` for each individual route.

**Validates: Requirements 1.2**

### Property 3: Cost Calculation Formulas

*For any* valid distance, duration, fuel_price, vehicle_mileage, and driver_wage values (all positive), the following relationships must hold:
- fuel_cost = (distance / vehicle_mileage) * fuel_price
- labor_cost = duration * driver_wage
- total_cost = fuel_cost + labor_cost

**Validates: Requirements 1.3, 1.4, 1.5**

### Property 4: Route Metrics Calculation

*For any* route, customer data, time_matrix, and cost parameters (all positive), the `calculate_route_metrics()` function should return a RouteMetrics object where:
- distance_km equals the sum of distances between consecutive stops
- duration_hours equals the sum of travel time, service time, and waiting time
- fuel_cost equals (distance_km / vehicle_mileage) * fuel_price
- labor_cost equals duration_hours * driver_wage
- total_cost equals fuel_cost + labor_cost
- num_customers equals len(route) - 1 (excluding depot)

**Validates: Requirements 4.1, 5.1, 5.2, 5.3, 5.4**

### Property 5: Cost Parameter Independence

*For any* routing solution (routes, time_matrix, customer data), changing cost parameters (fuel_price, vehicle_mileage, driver_wage) should produce different financial metrics without requiring re-execution of the solver. Specifically, calling `calculate_fleet_metrics()` twice with the same routes but different cost parameters should produce different costs but identical distance and duration values.

**Validates: Requirements 2.5**

### Property 6: Positive Cost Parameter Validation

*For any* cost parameter value, validation should accept the value if and only if it is a positive number greater than zero. Values that are zero, negative, or non-numeric should be rejected.

**Validates: Requirements 2.6**

### Property 7: Manifest Structure Completeness

*For any* routing solution (routes, customer data, time_matrix), the `generate_driver_manifest()` function should return a DataFrame where:
- Every row has columns: Route_ID, Stop_Number, Customer_ID, Arrival_Time, Action
- The number of rows equals the total number of stops across all routes
- Route_ID values are 1-indexed and sequential (1, 2, 3, ...)
- Stop_Number values are 1-indexed and sequential within each route
- Arrival_Time values are formatted as "HH:MM"
- All Customer_IDs appear in the original customer data

**Validates: Requirements 3.1, 3.3, 3.4**

### Property 8: Cost Per Kilometer Calculation

*For any* total_cost and total_distance where total_distance > 0, the cost_per_km should equal total_cost / total_distance. When total_distance equals 0, cost_per_km should equal 0 (edge case handling).

**Validates: Requirements 5.5**

### Property 9: Cost Per Delivery Calculation

*For any* total_cost and num_customers where num_customers > 0, the cost_per_delivery should equal total_cost / num_customers. When num_customers equals 0, cost_per_delivery should equal 0 (edge case handling).

**Validates: Requirements 5.6**

### Property 10: Chaos Mode Cost Recalculation

*For any* initial routing solution, when emergency orders are added (chaos mode), the `calculate_fleet_metrics()` function should produce different financial metrics that reflect the updated routes. Specifically, if routes change from R1 to R2, then metrics(R1) ≠ metrics(R2) unless R1 and R2 are identical.

**Validates: Requirements 6.4**

### Property 11: Time Matrix Integration

*For any* routing solution, the distance calculations performed by `calculate_route_distance()` should use the time_matrix parameter to derive distances. Specifically, for any two consecutive customers i and j in a route, the travel time should be read from time_matrix[i][j], and distance should be calculated as (time_matrix[i][j] / 60) * avg_speed_kmh.

**Validates: Requirements 6.1**

### Property 12: Routes Integration

*For any* list of routes, the `calculate_fleet_metrics()` function should process all routes in the list. Specifically, the number of RouteMetrics objects returned should equal len(routes), and each RouteMetrics.route_id should correspond to the index of that route in the input list.

**Validates: Requirements 6.2**

## Error Handling

### Input Validation

1. **Cost Parameters**: All cost parameters (fuel_price, vehicle_mileage, driver_wage) must be positive numbers greater than zero. The UI should prevent invalid inputs using Streamlit's `min_value` parameter.

2. **Division by Zero**: 
   - Cost per kilometer calculation: Handle case where total_distance = 0 by returning 0
   - Cost per delivery calculation: Handle case where num_customers = 0 by returning 0

3. **Missing Data**:
   - If routes is None or empty, financial calculations should not be performed
   - If time_matrix is None, distance calculations cannot be performed
   - If customer DataFrame is missing required columns, raise ValueError with descriptive message

### Edge Cases

1. **Empty Routes**: If a route contains only the depot (length 1), it should have:
   - distance_km = 0
   - duration_hours = 0
   - fuel_cost = 0
   - labor_cost = 0
   - num_customers = 0

2. **Single Customer Route**: If a route contains depot + one customer + depot, calculations should handle the round trip correctly.

3. **Zero Service Time**: If a customer has service_time = 0, duration calculation should still include travel time and waiting time.

4. **Large Numbers**: Financial calculations should handle large fleets (100+ routes) without overflow or precision loss.

### Error Messages

All error conditions should provide clear, actionable error messages:

```python
# Example error messages
"Cost parameters must be positive numbers greater than zero"
"No routing solution available. Please run the solver first."
"Time matrix is required for distance calculations"
"Customer data is missing required columns: {missing_columns}"
```

## Testing Strategy

### Dual Testing Approach

This feature will use both unit tests and property-based tests for comprehensive coverage:

**Unit Tests** will focus on:
- Specific examples with known expected outputs
- Edge cases (empty routes, zero values, single customer)
- Integration with existing dashboard components
- Error handling and validation

**Property-Based Tests** will focus on:
- Universal properties that hold for all valid inputs
- Mathematical formula correctness across random inputs
- Aggregation consistency (sum of parts equals whole)
- Data structure invariants

### Property-Based Testing Configuration

- **Library**: Hypothesis (Python property-based testing library)
- **Iterations**: Minimum 100 iterations per property test
- **Test Tagging**: Each property test must reference its design document property
- **Tag Format**: `# Feature: financial-analytics-reporting, Property {number}: {property_text}`

### Test Organization

```
tests/
├── test_financial_calculations.py
│   ├── Unit tests for calculation functions
│   └── Property tests for Properties 1-4, 8-9, 11-12
├── test_financial_integration.py
│   ├── Integration tests with dashboard
│   └── Property tests for Properties 5, 10
├── test_manifest_generation.py
│   ├── Unit tests for manifest export
│   └── Property tests for Property 7
└── test_cost_validation.py
    ├── Unit tests for input validation
    └── Property tests for Property 6
```

### Example Property Test

```python
from hypothesis import given, strategies as st
import pytest

# Feature: financial-analytics-reporting, Property 3: Cost Calculation Formulas
@given(
    distance=st.floats(min_value=0.1, max_value=10000),
    duration=st.floats(min_value=0.1, max_value=100),
    fuel_price=st.floats(min_value=0.1, max_value=1000),
    vehicle_mileage=st.floats(min_value=0.1, max_value=50),
    driver_wage=st.floats(min_value=0.1, max_value=10000)
)
def test_cost_calculation_formulas(distance, duration, fuel_price, vehicle_mileage, driver_wage):
    """Property 3: Cost calculation formulas are mathematically correct"""
    # Calculate costs
    fuel_cost = (distance / vehicle_mileage) * fuel_price
    labor_cost = duration * driver_wage
    total_cost = fuel_cost + labor_cost
    
    # Verify relationships
    assert fuel_cost >= 0
    assert labor_cost >= 0
    assert abs(total_cost - (fuel_cost + labor_cost)) < 0.01  # Floating point tolerance
    assert total_cost >= fuel_cost
    assert total_cost >= labor_cost
```

### Unit Test Coverage

Unit tests should cover:

1. **Calculation Functions**:
   - `calculate_route_distance()` with various route lengths
   - `calculate_route_duration()` with different service times
   - `calculate_route_metrics()` with known inputs
   - `calculate_fleet_metrics()` with multiple routes

2. **UI Components**:
   - `render_operations_config()` returns correct default values
   - `render_financial_overview()` displays metrics correctly
   - `render_cost_analysis_chart()` handles empty data
   - `render_download_button()` is disabled when no routes exist

3. **Export Functions**:
   - `generate_driver_manifest()` with single route
   - `generate_driver_manifest()` with multiple routes
   - `format_time()` with various minute values

4. **Edge Cases**:
   - Empty routes list
   - Single customer routes
   - Zero service times
   - Division by zero scenarios

### Integration Testing

Integration tests should verify:

1. Financial metrics update when cost parameters change
2. Financial metrics recalculate when chaos mode adds emergency orders
3. Download button generates valid CSV data
4. Financial overview section appears/disappears based on route availability
5. Cost analysis chart displays correct number of bars

### Manual Testing Checklist

- [ ] Upload CSV and run solver, verify financial metrics appear
- [ ] Change fuel price, verify costs update without re-running solver
- [ ] Change vehicle mileage, verify costs update correctly
- [ ] Change driver wage, verify costs update correctly
- [ ] Click download button, verify CSV file downloads with correct name
- [ ] Open CSV file, verify all columns and data are present
- [ ] Inject emergency order (chaos mode), verify costs recalculate
- [ ] Reset simulation, verify financial metrics clear
- [ ] View cost analysis chart, verify bars match number of routes
- [ ] Test with demo data (no CSV upload)
