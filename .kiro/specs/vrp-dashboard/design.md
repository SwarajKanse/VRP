# Design Document: VRP Dashboard

## Overview

The VRP Dashboard is a Streamlit-based web application that provides an interactive interface for solving Vehicle Routing Problems using an existing C++ solver (vrp_core). The dashboard features a professional dark-mode interface with real-time map visualization using Deck.gl, allowing logistics operators to configure parameters, load customer data, execute the solver, and visualize optimized routes on an interactive map.

The system architecture follows a three-layer design:
1. **Presentation Layer**: Streamlit UI components for user interaction
2. **Integration Layer**: Python functions that bridge the UI and C++ solver
3. **Solver Layer**: Existing vrp_core C++ module with Python bindings

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────┐
│                    Streamlit Dashboard                   │
│  ┌────────────┐  ┌──────────────┐  ┌─────────────────┐ │
│  │  Sidebar   │  │  Main Area   │  │  Metric Cards   │ │
│  │  Controls  │  │  Deck.gl Map │  │  Performance    │ │
│  └────────────┘  └──────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              Integration Layer (Python)                  │
│  ┌──────────────────┐  ┌──────────────────────────┐    │
│  │  Data Converter  │  │  solve_routing()         │    │
│  │  CSV → Customer  │  │  Orchestrates solver     │    │
│  └──────────────────┘  └──────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              VRP Solver (C++ / vrp_core)                │
│  ┌──────────────────┐  ┌──────────────────────────┐    │
│  │  VRPSolver       │  │  Customer                │    │
│  │  solve()         │  │  Location                │    │
│  └──────────────────┘  └──────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Initialization**: Dashboard loads with demo dataset and default parameters
2. **Configuration**: User adjusts vehicle capacity, vehicle count, or uploads CSV
3. **Execution**: User clicks "Run Solver" → Integration layer converts data → C++ solver executes
4. **Visualization**: Routes returned → Converted to map layers → Rendered via pydeck
5. **Metrics**: Execution time displayed in metric card

### Windows DLL Path Fix

On Windows systems, the C++ extension module (vrp_core.pyd) requires explicit DLL directory registration before import. This must occur at the module level before any vrp_core imports:

```python
import os, sys
if os.name == 'nt':
    build_path = os.path.abspath(os.path.join(
        os.path.dirname(__file__), '..', 'build', 'Release'
    ))
    if os.path.exists(build_path):
        os.add_dll_directory(build_path)
        sys.path.append(build_path)
```

This ensures the Windows loader can find dependent DLLs at runtime.

## Components and Interfaces

### 1. Main Application Module (`dashboard/app.py`)

**Responsibilities:**
- Initialize Streamlit configuration (wide layout, dark theme)
- Render sidebar controls
- Render main visualization area
- Coordinate data flow between UI and solver

**Key Functions:**

```python
def main():
    """Entry point for Streamlit application"""
    # Configure page
    # Render sidebar
    # Render main area
    # Handle solver execution
```

### 2. Data Management Module

**Responsibilities:**
- Generate demo dataset
- Load and validate CSV files
- Convert between pandas DataFrame and vrp_core.Customer objects

**Key Functions:**

```python
def generate_demo_data() -> pd.DataFrame:
    """
    Generate 5-10 random customers in Mumbai/Bandra area
    Returns DataFrame with columns: id, lat, lon, demand, start_window, end_window
    """
    
def load_customer_csv(uploaded_file) -> pd.DataFrame:
    """
    Load and validate CSV file
    Raises ValueError if required columns missing
    """
    
def dataframe_to_customers(df: pd.DataFrame) -> List[vrp_core.Customer]:
    """
    Convert DataFrame rows to vrp_core.Customer objects
    Maps: id, lat, lon, demand, start_window, end_window
    """
```

### 3. Solver Integration Module

**Responsibilities:**
- Execute VRP solver with timing
- Convert solver output to visualization format

**Key Functions:**

```python
def solve_routing(
    customers: List[vrp_core.Customer],
    capacity: int,
    num_vehicles: int
) -> Tuple[List[List[int]], float]:
    """
    Execute VRP solver and measure execution time
    
    Args:
        customers: List of Customer objects
        capacity: Vehicle capacity constraint
        num_vehicles: Number of available vehicles
        
    Returns:
        (routes, execution_time_ms)
        routes: List of routes, each route is list of customer IDs
        execution_time_ms: Solver execution time in milliseconds
    """
    
def routes_to_coordinates(
    routes: List[List[int]],
    df: pd.DataFrame
) -> List[Dict]:
    """
    Convert route indices to geographic coordinates for visualization
    
    Returns list of dicts with:
        - route_id: Vehicle/route number
        - path: List of [lon, lat] coordinates
        - color: RGB color for this route
    """
```

### 4. Visualization Module

**Responsibilities:**
- Create pydeck layers for customers and routes
- Configure map view and styling

**Key Functions:**

```python
def create_customer_layer(df: pd.DataFrame) -> pdk.Layer:
    """
    Create ScatterplotLayer for customer locations
    - Red color
    - Size proportional to demand
    """
    
def create_route_layers(route_data: List[Dict]) -> List[pdk.Layer]:
    """
    Create PathLayer or ArcLayer for each route
    - Different color per route (Cyan, Magenta, Yellow, etc.)
    - Line width based on route importance
    """
    
def render_map(customer_layer: pdk.Layer, route_layers: List[pdk.Layer]):
    """
    Render pydeck map with all layers
    - Dark map style
    - Auto-center on data
    - Enable zoom/pan
    """
```

### 5. UI Components Module

**Responsibilities:**
- Render sidebar controls
- Render metric cards
- Handle user interactions

**Key Functions:**

```python
def render_sidebar() -> Dict:
    """
    Render sidebar with all controls
    
    Returns dict with:
        - capacity: int
        - num_vehicles: int
        - uploaded_file: UploadedFile or None
        - run_solver: bool (button clicked)
    """
    
def render_metrics(execution_time_ms: float):
    """
    Display performance metrics in prominent cards
    """
```

## Data Models

### Customer Data Structure

The dashboard works with customer data in three representations:

**1. CSV/DataFrame Format (Input)**
```
Columns: id, lat, lon, demand, start_window, end_window
Types:   int, float, float, int, int, int
```

**2. vrp_core.Customer (C++ Binding)**
```cpp
struct Customer {
    int id;
    double lat;
    double lon;
    int demand;
    int start_window;
    int end_window;
};
```

**3. Visualization Format (Output)**
```python
{
    'route_id': int,           # Vehicle number (0, 1, 2, ...)
    'path': [[lon, lat], ...], # Ordered coordinates
    'color': [R, G, B]         # RGB color tuple
}
```

### Demo Dataset Specification

The demo dataset provides immediate functionality without file upload:

```python
Demo Dataset Characteristics:
- Number of customers: 5-10 (random)
- Geographic area: Mumbai/Bandra
  - Latitude range: 19.05 to 19.08
  - Longitude range: 72.82 to 72.85
- Demand: Random integers 1-10
- Time windows: 
  - start_window: Random 0-480 (8 hours)
  - end_window: start_window + 60-120 (1-2 hour window)
- Depot (customer 0): Center of area (19.065, 72.835)
```

### Route Color Mapping

Routes are assigned distinct colors for visual differentiation:

```python
ROUTE_COLORS = [
    [0, 255, 255],    # Cyan (Route 1)
    [255, 0, 255],    # Magenta (Route 2)
    [255, 255, 0],    # Yellow (Route 3)
    [0, 255, 0],      # Green (Route 4)
    [255, 128, 0],    # Orange (Route 5)
    [128, 0, 255],    # Purple (Route 6)
    # ... extend as needed
]
```

## Correctness Properties


*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property Reflection

After analyzing all acceptance criteria, I identified the following testable properties and performed redundancy elimination:

**Redundancy Analysis:**
- Properties 8.1 and 8.4 both test DataFrame ↔ Customer conversion, but 8.4 is more comprehensive (round-trip)
- Properties 6.2 and 6.8 both involve customer data in visualization, but serve different purposes (layer content vs viewport calculation)
- Properties 4.3 and 4.4 both validate demo data, but test different aspects (geographic bounds vs data validity)

**Consolidated Properties:**
After reflection, the following properties provide unique validation value without redundancy:

### Property 1: Demo Dataset Geographic Bounds

*For any* generated demo dataset, all customer coordinates should fall within the Mumbai/Bandra geographic area (latitude: 19.05-19.08, longitude: 72.82-72.85).

**Validates: Requirements 4.3**

### Property 2: Demo Dataset Validity

*For any* generated demo dataset, all customers should have valid data: latitude in [-90, 90], longitude in [-180, 180], demand > 0, and end_window > start_window.

**Validates: Requirements 4.4**

### Property 3: CSV Column Validation

*For any* uploaded CSV file, if it is missing any required column (id, lat, lon, demand, start_window, end_window), the validation should reject it with an error.

**Validates: Requirements 4.6**

### Property 4: DataFrame to Customer Conversion Preserves Data

*For any* pandas DataFrame row with customer data, converting to vrp_core.Customer and back to a dict should preserve all field values (id, lat, lon, demand, start_window, end_window).

**Validates: Requirements 5.2, 8.1, 8.4**

### Property 5: Solver Execution Returns Positive Time

*For any* valid solver execution with customers and parameters, the measured execution time should be a positive number (> 0 milliseconds).

**Validates: Requirements 5.5**

### Property 6: Customer Layer Contains All Customers

*For any* customer dataset, the scatter plot layer should contain exactly the same number of data points as there are customers in the dataset.

**Validates: Requirements 6.2**

### Property 7: Marker Size Correlates with Demand

*For any* two customers in the visualization, the customer with higher demand should have a marker size greater than or equal to the customer with lower demand.

**Validates: Requirements 6.3**

### Property 8: Route Color Uniqueness

*For any* set of routes with N vehicles (where N ≤ number of available colors), each route should be assigned a distinct color from the color palette.

**Validates: Requirements 6.6**

### Property 9: Map Viewport Centers on Data

*For any* customer dataset, the map viewport center coordinates should be within the bounding box of all customer locations.

**Validates: Requirements 6.8**

### Property 10: Route Coordinate Conversion Completeness

*For any* route (list of customer IDs) and corresponding DataFrame, converting the route to coordinates should produce a path with the same number of points as there are customers in the route.

**Validates: Requirements 8.2, 8.3**

## Error Handling

### Input Validation Errors

**CSV Validation Failures:**
- Missing required columns → Display error message listing missing columns
- Invalid data types → Display error message with row/column information
- Empty file → Display error message requesting valid data

**Parameter Validation:**
- Capacity < 1 → Prevented by UI (number input min=1)
- Num vehicles < 1 → Prevented by UI (number input min=1)

### Solver Execution Errors

**C++ Solver Exceptions:**
- Infeasible problem → Catch exception, display user-friendly error message
- Invalid customer data → Catch exception, display validation error
- Memory allocation failure → Catch exception, display system error message

**Error Display Strategy:**
- Use Streamlit's `st.error()` for prominent error messages
- Include actionable guidance (e.g., "Please check your CSV format")
- Log detailed error information for debugging

### DLL Loading Errors (Windows)

**Missing Build Directory:**
- Check if build/Release exists before adding to DLL path
- If missing, display error: "C++ solver module not found. Please build the project first."

**Import Failure:**
- Catch ImportError when importing vrp_core
- Display error with instructions to verify build and dependencies

## Testing Strategy

### Dual Testing Approach

The dashboard will be validated using both unit tests and property-based tests:

**Unit Tests** (pytest):
- Specific examples of data conversion
- Edge cases (empty datasets, single customer, etc.)
- Error conditions (missing columns, invalid data)
- UI component rendering (specific inputs → expected outputs)
- Integration points (CSV loading, solver calling)

**Property-Based Tests** (Hypothesis):
- Universal properties across all valid inputs
- Data conversion correctness (Properties 4, 10)
- Validation logic (Properties 1, 2, 3)
- Visualization consistency (Properties 6, 7, 8, 9)
- Performance measurement (Property 5)

### Property Test Configuration

**Testing Framework:** pytest with Hypothesis library

**Configuration:**
- Minimum 100 iterations per property test
- Each test tagged with: `# Feature: vrp-dashboard, Property N: [property text]`
- Use Hypothesis strategies for generating test data:
  - `st.floats()` for coordinates with appropriate bounds
  - `st.integers()` for demand, time windows
  - `st.lists()` for customer collections
  - `st.dataframes()` for pandas DataFrame generation

**Example Test Structure:**
```python
from hypothesis import given, strategies as st
import hypothesis.extra.pandas as pdst

@given(pdst.data_frames([
    pdst.column('id', dtype=int),
    pdst.column('lat', elements=st.floats(19.05, 19.08)),
    pdst.column('lon', elements=st.floats(72.82, 72.85)),
    pdst.column('demand', elements=st.integers(1, 100)),
    pdst.column('start_window', elements=st.integers(0, 480)),
    pdst.column('end_window', elements=st.integers(60, 600))
]))
def test_property_4_conversion_preserves_data(df):
    # Feature: vrp-dashboard, Property 4: DataFrame to Customer conversion preserves data
    # Test implementation
    pass
```

### Unit Test Focus Areas

1. **Data Generation:**
   - Demo dataset has correct number of customers (5-10)
   - Demo dataset depot is at (19.065, 72.835)
   - CSV parsing handles various formats

2. **Conversion Functions:**
   - Empty DataFrame → empty customer list
   - Single customer → single Customer object
   - DataFrame with missing optional columns → default values

3. **Visualization:**
   - Empty routes → no path layers
   - Single-customer route → single point path
   - Route colors cycle correctly when vehicles > available colors

4. **Error Handling:**
   - CSV with missing 'lat' column → ValueError
   - Solver exception → error message displayed
   - Non-existent build directory → graceful handling

### Integration Testing

**End-to-End Scenarios:**
1. Load demo data → Run solver → Verify visualization renders
2. Upload valid CSV → Run solver → Verify routes displayed
3. Upload invalid CSV → Verify error message shown
4. Adjust parameters → Run solver → Verify results update

**Testing Approach:**
- Use Streamlit's testing utilities for component testing
- Mock vrp_core.VRPSolver for isolated dashboard testing
- Use actual solver for integration tests

### Manual Testing Checklist

Since Streamlit is a visual framework, manual testing is essential:

- [ ] Dashboard loads without errors
- [ ] Dark theme applied correctly
- [ ] Sidebar controls are functional
- [ ] Demo data displays on map
- [ ] File upload accepts CSV
- [ ] Solver executes and returns routes
- [ ] Routes visualized with correct colors
- [ ] Execution time displayed
- [ ] Map zoom/pan works smoothly
- [ ] Error messages display clearly
- [ ] Windows DLL path fix works

### Performance Testing

**Metrics to Monitor:**
- Solver execution time (primary metric)
- Dashboard render time
- Map interaction responsiveness

**Benchmarks:**
- 10 customers: < 10ms solver time
- 50 customers: < 100ms solver time
- 100 customers: < 500ms solver time

These benchmarks validate the "high-frequency" performance positioning.
