# Design Document: Dynamic Event Injection (Chaos Mode)

## Overview

The Chaos Mode feature adds real-time dynamic re-routing capabilities to the VRP solver dashboard. This feature allows users to inject emergency orders during runtime and observe the system's ability to re-optimize routes in sub-millisecond time, demonstrating the solver's suitability for high-frequency, event-driven logistics scenarios.

The implementation focuses on three key aspects:
1. **UI Integration**: Adding emergency order injection controls to the Streamlit dashboard
2. **State Management**: Persisting injected orders across interactions using Streamlit session state
3. **Performance Monitoring**: Measuring and displaying re-optimization latency to validate high-frequency capabilities

## Architecture

### Component Overview

The chaos mode feature integrates into the existing dashboard architecture without modifying the core C++ solver. The architecture follows a layered approach:

```
┌─────────────────────────────────────────────────────────┐
│                  Streamlit Dashboard                     │
│  ┌────────────────────────────────────────────────────┐ │
│  │         Chaos Mode UI Components                   │ │
│  │  - Emergency Order Button                          │ │
│  │  - Reset Simulation Button                         │ │
│  │  - Performance Toast Notifications                 │ │
│  └────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────┐ │
│  │         State Management Layer                     │ │
│  │  - st.session_state.dynamic_customers              │ │
│  │  - st.session_state.original_customers             │ │
│  │  - st.session_state.chaos_mode_active              │ │
│  └────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────┐ │
│  │         Emergency Order Generator                  │ │
│  │  - Random location within bounds                   │ │
│  │  - Random demand (1-5)                             │ │
│  │  - Time window calculation                         │ │
│  └────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────┐ │
│  │         Existing Solver Integration                │ │
│  │  - solve_routing() with updated customer list     │ │
│  │  - OSRM/Haversine time matrix generation          │ │
│  │  - Performance timing measurement                  │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### Integration Points

The feature integrates with existing dashboard components:

1. **Sidebar Controls**: New buttons added to the sidebar alongside existing configuration controls
2. **Data Management**: Extends the existing customer data flow to support dynamic additions
3. **Solver Integration**: Reuses the existing `solve_routing()` function without modification
4. **Visualization**: Leverages existing map rendering with enhanced visual markers for new orders

## Components and Interfaces

### 1. Emergency Order Generator

**Purpose**: Generate realistic emergency orders with random but valid constraints.

**Function Signature**:
```python
def generate_emergency_order(
    existing_df: pd.DataFrame,
    current_time: float
) -> pd.DataFrame
```

**Parameters**:
- `existing_df`: DataFrame containing current customers (used to determine geographic bounds)
- `current_time`: Current simulation time in minutes (used to calculate time windows)

**Returns**:
- Single-row DataFrame with new customer data

**Algorithm**:
1. Calculate bounding box from existing customer coordinates:
   - `min_lat`, `max_lat` = min/max of existing customer latitudes
   - `min_lon`, `max_lon` = min/max of existing customer longitudes
2. Generate random location within bounds:
   - `lat = random.uniform(min_lat, max_lat)`
   - `lon = random.uniform(min_lon, max_lon)`
3. Generate random demand: `demand = random.randint(1, 5)`
4. Calculate time window:
   - `start_window = current_time` (immediate service needed)
   - `end_window = current_time + 30` (30-minute window)
5. Set service time: `service_time = 5` (priority handling)
6. Assign new customer ID: `id = max(existing_df['id']) + 1`

**Edge Cases**:
- If `existing_df` has only depot (id=0), use default bounds (e.g., Mumbai area)
- If `current_time` is near end of day, adjust window to not exceed day boundary

### 2. State Management Module

**Purpose**: Persist dynamic customer data across Streamlit interactions.

**Session State Variables**:

```python
# Original customer data (loaded from CSV or demo)
st.session_state.original_customers: pd.DataFrame

# Dynamically injected customers
st.session_state.dynamic_customers: List[pd.DataFrame]

# Flag indicating if chaos mode has been activated
st.session_state.chaos_mode_active: bool

# Current simulation time (for time window calculations)
st.session_state.current_time: float
```

**Initialization Logic**:
```python
def initialize_chaos_state():
    """Initialize session state variables for chaos mode"""
    if 'original_customers' not in st.session_state:
        st.session_state.original_customers = None
    if 'dynamic_customers' not in st.session_state:
        st.session_state.dynamic_customers = []
    if 'chaos_mode_active' not in st.session_state:
        st.session_state.chaos_mode_active = False
    if 'current_time' not in st.session_state:
        st.session_state.current_time = 0.0
```

**Data Merging Logic**:
```python
def get_current_customers() -> pd.DataFrame:
    """Get combined customer list (original + dynamic)"""
    if st.session_state.original_customers is None:
        return pd.DataFrame()
    
    # Start with original customers
    combined = st.session_state.original_customers.copy()
    
    # Append all dynamic customers
    for dynamic_customer in st.session_state.dynamic_customers:
        combined = pd.concat([combined, dynamic_customer], ignore_index=True)
    
    return combined
```

### 3. UI Components

**Emergency Order Button**:
```python
def render_chaos_controls():
    """Render chaos mode controls in sidebar"""
    st.sidebar.header("🚨 Chaos Mode")
    
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
```

**Performance Toast Notification**:
```python
def show_reoptimization_toast(execution_time_ms: float):
    """Display toast notification with re-optimization time"""
    st.toast(
        f"⚡ Fleet Re-routed in {execution_time_ms:.2f}ms!",
        icon="⚡"
    )
```

**Visual Highlighting for New Orders**:
```python
def create_customer_layer_with_highlights(
    df: pd.DataFrame,
    dynamic_customer_ids: List[int]
) -> pdk.Layer:
    """Create customer layer with visual distinction for emergency orders"""
    # Add a column to identify dynamic customers
    df['is_dynamic'] = df['id'].isin(dynamic_customer_ids)
    
    # Create ScatterplotLayer with conditional coloring
    layer = pdk.Layer(
        'ScatterplotLayer',
        data=df,
        get_position='[lon, lat]',
        get_color='[255, 255, 0] if is_dynamic else [255, 0, 0]',  # Yellow for dynamic, red for original
        get_radius='demand * 50',
        pickable=True,
        auto_highlight=True
    )
    
    return layer
```

### 4. Integration with Existing Solver

**Modified Main Flow**:
```python
def main():
    # ... existing setup code ...
    
    # Initialize chaos mode state
    initialize_chaos_state()
    
    # Load data (store as original if first load)
    if config['uploaded_file'] is not None:
        df = load_customer_csv(config['uploaded_file'])
        if st.session_state.original_customers is None:
            st.session_state.original_customers = df
    else:
        df = generate_demo_data()
        if st.session_state.original_customers is None:
            st.session_state.original_customers = df
    
    # Render chaos controls
    inject_button, reset_button = render_chaos_controls()
    
    # Handle emergency order injection
    if inject_button:
        current_customers = get_current_customers()
        new_order = generate_emergency_order(
            current_customers,
            st.session_state.current_time
        )
        st.session_state.dynamic_customers.append(new_order)
        st.session_state.chaos_mode_active = True
        
        # Trigger re-optimization
        combined_customers = get_current_customers()
        customers = dataframe_to_customers(combined_customers)
        
        start_time = time.perf_counter()
        routes, execution_time_ms, time_matrix = solve_routing(
            customers,
            config['capacity'],
            config['num_vehicles'],
            combined_customers
        )
        end_time = time.perf_counter()
        
        # Show performance toast
        show_reoptimization_toast(execution_time_ms)
        
        # Update session state
        st.session_state.routes = routes
        st.session_state.execution_time_ms = execution_time_ms
        st.session_state.time_matrix = time_matrix
    
    # Handle reset
    if reset_button:
        st.session_state.dynamic_customers = []
        st.session_state.chaos_mode_active = False
        st.session_state.current_time = 0.0
        st.session_state.routes = None
        st.session_state.execution_time_ms = None
        st.session_state.time_matrix = None
        st.rerun()
    
    # ... rest of existing code ...
```

## Data Models

### Emergency Order Data Structure

Emergency orders use the same data structure as regular customers:

```python
{
    'id': int,              # Unique customer ID (max existing ID + 1)
    'lat': float,           # Latitude (within existing customer bounds)
    'lon': float,           # Longitude (within existing customer bounds)
    'demand': int,          # Random demand (1-5)
    'start_window': float,  # Current time (immediate service)
    'end_window': float,    # Current time + 30 minutes
    'service_time': float   # 5 minutes (priority handling)
}
```

### Session State Schema

```python
{
    'original_customers': pd.DataFrame,      # Initial customer data
    'dynamic_customers': List[pd.DataFrame], # List of injected orders
    'chaos_mode_active': bool,               # Whether chaos mode is active
    'current_time': float,                   # Simulation time in minutes
    'routes': List[List[int]],              # Current route solution
    'execution_time_ms': float,             # Last solver execution time
    'time_matrix': List[List[float]]        # Current time matrix
}
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*


### Property 1: Valid Emergency Order Generation

*For any* existing customer dataset, when an emergency order is generated, the new customer must have:
- Location coordinates within the bounding box of existing customers
- Demand value between 1 and 5 (inclusive)
- Start window equal to current time
- End window equal to current time + 30 minutes
- Service time equal to 5 minutes

**Validates: Requirements 1.2**

### Property 2: Customer List Growth

*For any* existing customer list with N customers, injecting an emergency order must result in a customer list with N+1 customers, where the new customer has a unique ID greater than all existing IDs.

**Validates: Requirements 1.3**

### Property 3: Solver Invocation After Injection

*For any* customer list state, when an emergency order is injected, the solve_routing() function must be called with a customer list that includes the newly injected customer.

**Validates: Requirements 1.4**

### Property 4: Performance Toast Display

*For any* re-optimization execution, when the solver completes, a toast notification must be displayed containing the execution time in milliseconds.

**Validates: Requirements 2.1**

### Property 5: Visual Distinction for Emergency Orders

*For any* customer dataset containing both original and dynamic customers, the rendering function must assign different visual properties (color) to dynamic customers compared to original customers.

**Validates: Requirements 2.2**

### Property 6: Route Completeness

*For any* injected emergency order, the resulting route solution must include the new customer's ID in at least one vehicle route.

**Validates: Requirements 2.3**

### Property 7: Distance Matrix Configuration Respect

*For any* OSRM toggle state (enabled/disabled), the time matrix generation must use OSRM API when enabled and Haversine calculation when disabled, regardless of whether customers are original or dynamically injected.

**Validates: Requirements 3.1**

### Property 8: Graceful Infeasibility Handling

*For any* emergency order that makes the problem infeasible (e.g., impossible time constraints), the system must return a solution (either partial or original) without crashing and display a warning message to the user.

**Validates: Requirements 3.3**

### Property 9: Session State Persistence

*For any* sequence of emergency order injections, the session state must preserve all injected customers across page interactions (refreshes, button clicks), such that the combined customer list always includes both original and all dynamically added customers.

**Validates: Requirements 4.1, 4.2**

### Property 10: Reset to Initial State

*For any* customer list state containing N dynamic customers, clicking the "Reset Simulation" button must result in a customer list that contains only the original customers (no dynamic customers), and all chaos mode state variables must be reset to their initial values.

**Validates: Requirements 4.4**

## Error Handling

### Infeasible Problem Handling

When an injected emergency order makes the problem infeasible:

1. **Detection**: The solver may return an empty route list or routes that don't include all customers
2. **Fallback Strategy**: 
   - If solver returns empty routes, keep the previous solution
   - If solver returns partial routes, use the partial solution
3. **User Notification**: Display a warning toast: "⚠️ Emergency order could not be fully integrated. Showing best available solution."
4. **State Preservation**: Keep the emergency order in the customer list for transparency

### OSRM API Failure

When OSRM API is unavailable during emergency order injection:

1. **Automatic Fallback**: Use Haversine-based time matrix calculation
2. **User Notification**: Display warning about fallback (already implemented in existing code)
3. **Consistency**: Ensure all distance calculations use the same method (OSRM or Haversine) for the entire customer set

### Invalid Customer Data

When emergency order generation produces invalid data:

1. **Validation**: Check that generated coordinates are within valid lat/lon ranges
2. **Bounds Handling**: If existing customers span invalid bounds, use default bounds (Mumbai area)
3. **Time Window Validation**: Ensure start_window < end_window and both are non-negative

### Session State Corruption

When session state becomes corrupted or inconsistent:

1. **Defensive Initialization**: Always check for None values before accessing session state
2. **Recovery**: If corruption detected, reset to initial state and notify user
3. **Logging**: Log state transitions for debugging (optional, for development)

## Testing Strategy

### Dual Testing Approach

This feature requires both unit tests and property-based tests to ensure comprehensive coverage:

**Unit Tests** focus on:
- Specific examples of emergency order generation
- UI component rendering (button presence, toast display)
- Integration points (solver invocation, state updates)
- Edge cases (empty customer list, single customer, boundary coordinates)

**Property Tests** focus on:
- Universal properties across all possible customer datasets
- Randomized emergency order generation
- State persistence across multiple injections
- Reset behavior verification

### Property-Based Testing Configuration

**Testing Library**: Hypothesis (Python property-based testing library)

**Configuration**:
- Minimum 100 iterations per property test
- Each test tagged with feature name and property number
- Tag format: `# Feature: chaos-mode-injection, Property N: [property description]`

**Test Data Generators**:

```python
from hypothesis import given, strategies as st
from hypothesis.strategies import composite

@composite
def customer_dataframe(draw):
    """Generate random customer DataFrame for testing"""
    num_customers = draw(st.integers(min_value=2, max_value=20))
    
    customers = [{
        'id': 0,
        'lat': 19.065,
        'lon': 72.835,
        'demand': 0,
        'start_window': 0,
        'end_window': 600,
        'service_time': 0
    }]
    
    for i in range(1, num_customers):
        customers.append({
            'id': i,
            'lat': draw(st.floats(min_value=19.05, max_value=19.08)),
            'lon': draw(st.floats(min_value=72.82, max_value=72.85)),
            'demand': draw(st.integers(min_value=1, max_value=10)),
            'start_window': draw(st.floats(min_value=0, max_value=480)),
            'end_window': draw(st.floats(min_value=60, max_value=600)),
            'service_time': 10
        })
    
    return pd.DataFrame(customers)

@composite
def current_time(draw):
    """Generate random current time for testing"""
    return draw(st.floats(min_value=0, max_value=570))  # 0 to 570 (leaves room for 30-min window)
```

### Unit Test Examples

**Test 1: Button Presence**
```python
def test_chaos_controls_render():
    """Verify chaos mode buttons are present in sidebar"""
    # Render sidebar
    inject_button, reset_button = render_chaos_controls()
    
    # Assert buttons exist
    assert inject_button is not None
    assert reset_button is not None
```

**Test 2: Emergency Order Structure**
```python
def test_emergency_order_structure():
    """Verify emergency order has required fields"""
    df = generate_demo_data()
    new_order = generate_emergency_order(df, current_time=100.0)
    
    # Assert required columns exist
    assert 'id' in new_order.columns
    assert 'lat' in new_order.columns
    assert 'lon' in new_order.columns
    assert 'demand' in new_order.columns
    assert 'start_window' in new_order.columns
    assert 'end_window' in new_order.columns
    assert 'service_time' in new_order.columns
    
    # Assert single row
    assert len(new_order) == 1
```

**Test 3: Reset Behavior**
```python
def test_reset_clears_dynamic_customers():
    """Verify reset button clears all injected orders"""
    # Setup: inject some orders
    st.session_state.dynamic_customers = [
        pd.DataFrame([{'id': 10, 'lat': 19.06, 'lon': 72.83, 'demand': 3}]),
        pd.DataFrame([{'id': 11, 'lat': 19.07, 'lon': 72.84, 'demand': 2}])
    ]
    st.session_state.chaos_mode_active = True
    
    # Simulate reset button click
    handle_reset_button()
    
    # Assert state is cleared
    assert len(st.session_state.dynamic_customers) == 0
    assert st.session_state.chaos_mode_active == False
```

### Property Test Examples

**Property Test 1: Valid Emergency Order Generation**
```python
# Feature: chaos-mode-injection, Property 1: Valid Emergency Order Generation
@given(df=customer_dataframe(), time=current_time())
def test_property_valid_emergency_order(df, time):
    """For any customer dataset, generated emergency orders must be valid"""
    new_order = generate_emergency_order(df, time)
    
    # Extract bounds from existing customers
    min_lat, max_lat = df['lat'].min(), df['lat'].max()
    min_lon, max_lon = df['lon'].min(), df['lon'].max()
    
    # Assert location within bounds
    assert min_lat <= new_order.iloc[0]['lat'] <= max_lat
    assert min_lon <= new_order.iloc[0]['lon'] <= max_lon
    
    # Assert demand in valid range
    assert 1 <= new_order.iloc[0]['demand'] <= 5
    
    # Assert time window properties
    assert new_order.iloc[0]['start_window'] == time
    assert new_order.iloc[0]['end_window'] == time + 30
    
    # Assert service time
    assert new_order.iloc[0]['service_time'] == 5
```

**Property Test 2: Customer List Growth**
```python
# Feature: chaos-mode-injection, Property 2: Customer List Growth
@given(df=customer_dataframe(), time=current_time())
def test_property_customer_list_growth(df, time):
    """For any customer list, injection must increase list size by 1"""
    original_count = len(df)
    max_id = df['id'].max()
    
    new_order = generate_emergency_order(df, time)
    combined = pd.concat([df, new_order], ignore_index=True)
    
    # Assert list grew by 1
    assert len(combined) == original_count + 1
    
    # Assert new ID is unique and greater than max
    assert new_order.iloc[0]['id'] > max_id
```

**Property Test 3: Session State Persistence**
```python
# Feature: chaos-mode-injection, Property 9: Session State Persistence
@given(
    df=customer_dataframe(),
    num_injections=st.integers(min_value=1, max_value=10)
)
def test_property_session_state_persistence(df, num_injections):
    """For any sequence of injections, session state must preserve all customers"""
    # Initialize state
    st.session_state.original_customers = df
    st.session_state.dynamic_customers = []
    
    # Inject multiple orders
    for i in range(num_injections):
        new_order = generate_emergency_order(
            get_current_customers(),
            current_time=i * 10.0
        )
        st.session_state.dynamic_customers.append(new_order)
    
    # Get combined list
    combined = get_current_customers()
    
    # Assert all customers present
    assert len(combined) == len(df) + num_injections
    
    # Assert original customers preserved
    for _, original_customer in df.iterrows():
        assert original_customer['id'] in combined['id'].values
```

### Integration Testing

**End-to-End Chaos Mode Flow**:
1. Load initial customer data (demo or CSV)
2. Click "Inject Emergency Order" button
3. Verify new customer appears in customer list
4. Verify solver is invoked with updated list
5. Verify toast notification displays execution time
6. Verify map highlights new customer
7. Verify new customer appears in at least one route
8. Click "Reset Simulation" button
9. Verify customer list returns to original state
10. Verify all chaos mode state variables are reset

**OSRM Integration Test**:
1. Enable OSRM toggle
2. Inject emergency order
3. Verify OSRM API is called for time matrix
4. Disable OSRM toggle
5. Inject another emergency order
6. Verify Haversine calculation is used

**Performance Validation Test**:
1. Load dataset with 20 customers
2. Inject 10 emergency orders sequentially
3. Measure re-optimization time for each injection
4. Assert all re-optimization times < 10ms (target latency)
5. Display performance statistics (min, max, avg, p95)

### Test Coverage Goals

- **Unit Test Coverage**: 90%+ of new code (emergency order generation, state management, UI components)
- **Property Test Coverage**: All 10 correctness properties implemented as property tests
- **Integration Test Coverage**: All user workflows (injection, reset, OSRM toggle)
- **Edge Case Coverage**: Empty lists, single customer, boundary coordinates, infeasible problems

### Testing Tools

- **pytest**: Test runner and framework
- **hypothesis**: Property-based testing library
- **streamlit.testing**: Streamlit component testing utilities (if available)
- **unittest.mock**: Mocking for OSRM API calls and solver invocations

## Implementation Notes

### Windows DLL Configuration Preservation

**CRITICAL**: The dashboard file (`dashboard/app.py`) contains Windows-specific DLL loading configuration that MUST be preserved:

```python
# --- UNIVERSAL WINDOWS DLL FIX ---
if os.name == 'nt':
    # ... existing DLL path configuration ...
    os.add_dll_directory(r"C:\mingw64\bin")
    os.add_dll_directory(os.path.abspath("build"))
```

This configuration is essential for loading the C++ extension on Windows. All modifications to `dashboard/app.py` must preserve this block exactly as-is.

### Performance Considerations

**Target Latency**: < 10ms for re-optimization

**Optimization Strategies**:
1. **Incremental Matrix Updates**: When OSRM is disabled, only calculate distances for new customer (not full matrix rebuild)
2. **Caching**: Cache OSRM responses for repeated coordinate pairs
3. **Async OSRM Calls**: Use async requests for OSRM API to avoid blocking UI
4. **Solver Warm Start**: Reuse previous solution as starting point for re-optimization (future enhancement)

**Current Implementation**: Initial version will rebuild full time matrix on each injection. Optimization can be added in future iterations if performance targets are not met.

### Streamlit-Specific Considerations

**Session State Behavior**:
- Streamlit reruns the entire script on each interaction
- Session state persists across reruns
- Must initialize session state variables before first use
- Use `st.rerun()` to force immediate UI update after state changes

**Button Click Handling**:
- Button clicks return `True` only on the interaction where clicked
- Must handle button logic immediately in the same script run
- Cannot rely on button state persisting across reruns

**Toast Notifications**:
- `st.toast()` displays temporary notifications
- Toasts auto-dismiss after a few seconds
- Multiple toasts can be queued
- Use icons for visual distinction (⚡ for performance, ⚠️ for warnings)

### Future Enhancements

**Potential Extensions** (not in current scope):
1. **Configurable Emergency Order Parameters**: Allow user to specify demand, time window, location
2. **Multiple Simultaneous Injections**: Inject multiple orders at once
3. **Order Cancellation**: Remove previously injected orders
4. **Replay Mode**: Record and replay injection sequences
5. **Performance Analytics Dashboard**: Track re-optimization latency over time
6. **Stress Testing Mode**: Automated rapid injection for performance testing
7. **Real-time Data Integration**: Connect to external order management system
