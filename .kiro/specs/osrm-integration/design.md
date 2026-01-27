# Design Document: OSRM Integration

## Overview

This design specifies the integration of the Open Source Routing Machine (OSRM) API into the VRP solver dashboard to replace Haversine-based time calculations with real road network travel times. The implementation will add a new `get_osrm_matrix()` function, modify the `solve_routing()` function to use OSRM data, and implement robust error handling with automatic fallback to the existing Haversine-based approach.

The design follows a minimal-change approach: only `dashboard/app.py` will be modified, with no changes to C++ code, bindings, or other Python files. The existing `generate_time_matrix()` function will be preserved as a fallback mechanism.

## Architecture

### High-Level Flow

```
User clicks "Run Solver"
    ↓
solve_routing() called
    ↓
Try: get_osrm_matrix(locations)
    ↓
    ├─ Success → Use OSRM time matrix
    │             ↓
    │          Pass to C++ solver
    │             ↓
    │          Display success message
    │
    └─ Failure → Catch exception
                  ↓
               generate_time_matrix() (fallback)
                  ↓
               Pass to C++ solver
                  ↓
               Display warning message
```

### Component Interaction

```
┌─────────────────────────────────────────┐
│         Streamlit Dashboard             │
│         (dashboard/app.py)              │
├─────────────────────────────────────────┤
│                                         │
│  ┌──────────────────────────────────┐  │
│  │   solve_routing()                │  │
│  │                                  │  │
│  │  Try:                            │  │
│  │    time_matrix =                 │  │
│  │      get_osrm_matrix(locations)  │  │
│  │  Except:                         │  │
│  │    time_matrix =                 │  │
│  │      generate_time_matrix(df)    │  │
│  └──────────────────────────────────┘  │
│              ↓                          │
│  ┌──────────────────────────────────┐  │
│  │   vrp_core.VRPSolver.solve()     │  │
│  │   (C++ solver - unchanged)       │  │
│  └──────────────────────────────────┘  │
└─────────────────────────────────────────┘
              ↓
    ┌─────────────────────┐
    │   OSRM API          │
    │   (External)        │
    └─────────────────────┘
```

## Components and Interfaces

### 1. get_osrm_matrix() Function

**Purpose:** Query the OSRM Table Service API and return a travel time matrix.

**Function Signature:**
```python
def get_osrm_matrix(locations: List[List[float]]) -> List[List[float]]:
    """
    Query OSRM API for travel time matrix
    
    Args:
        locations: List of [latitude, longitude] pairs
        
    Returns:
        N×N matrix of travel times in minutes
        
    Raises:
        requests.exceptions.RequestException: If API request fails
        ValueError: If API returns invalid data
        KeyError: If API response is missing expected fields
    """
```

**Implementation Details:**

1. **Coordinate Conversion:**
   - Input: `[[lat1, lon1], [lat2, lon2], ...]`
   - Convert to OSRM format: `"lon1,lat1;lon2,lat2;..."`
   - OSRM expects longitude first, latitude second

2. **URL Construction:**
   ```python
   base_url = "http://router.project-osrm.org/table/v1/driving/"
   coordinates = ";".join([f"{lon},{lat}" for lat, lon in locations])
   url = f"{base_url}{coordinates}?annotations=duration"
   ```

3. **HTTP Request:**
   ```python
   response = requests.get(url, timeout=10)
   response.raise_for_status()  # Raises HTTPError for bad status codes
   ```

4. **Response Parsing:**
   ```python
   data = response.json()
   durations = data['durations']  # N×N matrix in seconds
   time_matrix = [[duration / 60.0 for duration in row] for row in durations]
   ```

5. **Error Handling:**
   - Network errors: `requests.exceptions.ConnectionError`
   - Timeout: `requests.exceptions.Timeout`
   - HTTP errors: `requests.exceptions.HTTPError`
   - JSON parsing: `json.JSONDecodeError`
   - Missing fields: `KeyError`
   - All exceptions should propagate to caller for fallback handling

### 2. Modified solve_routing() Function

**Purpose:** Execute VRP solver with OSRM-based time matrix, falling back to Haversine if OSRM fails.

**Updated Implementation:**

```python
def solve_routing(
    customers: List,
    capacity: int,
    num_vehicles: int,
    df: pd.DataFrame
) -> Tuple[List[List[int]], float]:
    """
    Execute VRP solver with OSRM time matrix (fallback to Haversine)
    
    Args:
        customers: List of vrp_core.Customer objects
        capacity: Vehicle capacity constraint
        num_vehicles: Number of available vehicles
        df: DataFrame with customer data
        
    Returns:
        Tuple of (routes, execution_time_ms)
    """
    if vrp_core is None:
        raise RuntimeError("vrp_core module not available")
    
    try:
        # Extract locations from DataFrame
        df_sorted = df.sort_values('id').reset_index(drop=True)
        locations = [[row['lat'], row['lon']] for _, row in df_sorted.iterrows()]
        
        # Try OSRM first
        try:
            time_matrix = get_osrm_matrix(locations)
            st.info("✅ Using OSRM real road network travel times")
        except Exception as e:
            # Fallback to Haversine
            st.warning(
                f"⚠️ OSRM API unavailable ({type(e).__name__}). "
                f"Using Haversine-based travel times (40 km/h average speed)."
            )
            time_matrix = generate_time_matrix(df)
        
        # Create solver and execute
        solver = vrp_core.VRPSolver()
        start_time = time.perf_counter()
        routes = solver.solve(customers, float(capacity), True, time_matrix)
        end_time = time.perf_counter()
        
        execution_time_ms = (end_time - start_time) * 1000.0
        return routes, execution_time_ms
        
    except Exception as e:
        raise Exception(f"Solver execution failed: {str(e)}")
```

**Key Changes:**
1. Extract locations from DataFrame before time matrix generation
2. Wrap `get_osrm_matrix()` call in try-except block
3. Display user-friendly messages using Streamlit components
4. Preserve existing solver invocation logic
5. Maintain backward compatibility with existing code

### 3. Preserved generate_time_matrix() Function

**Purpose:** Fallback mechanism for time matrix generation using Haversine distance.

**Status:** No changes required. This function remains as-is and serves as the fallback when OSRM is unavailable.

## Data Models

### OSRM API Request

**URL Format:**
```
http://router.project-osrm.org/table/v1/driving/{coordinates}?annotations=duration
```

**Coordinates Format:**
```
lon1,lat1;lon2,lat2;lon3,lat3;...
```

**Example:**
```
http://router.project-osrm.org/table/v1/driving/72.835,19.065;72.840,19.070?annotations=duration
```

### OSRM API Response

**Structure:**
```json
{
  "code": "Ok",
  "durations": [
    [0, 234.5, 456.7],
    [234.5, 0, 345.6],
    [456.7, 345.6, 0]
  ],
  "sources": [...],
  "destinations": [...]
}
```

**Fields:**
- `code`: Status code ("Ok" for success)
- `durations`: N×N matrix of travel times in seconds
- `sources`: Array of source location objects (not used)
- `destinations`: Array of destination location objects (not used)

### Time Matrix Format

**Internal Representation:**
```python
List[List[float]]  # N×N matrix
```

**Example:**
```python
[
    [0.0, 3.9, 7.6],      # From customer 0 to all customers (minutes)
    [3.9, 0.0, 5.8],      # From customer 1 to all customers (minutes)
    [7.6, 5.8, 0.0]       # From customer 2 to all customers (minutes)
]
```

**Properties:**
- Diagonal elements are 0.0 (travel time from location to itself)
- Matrix is generally symmetric for undirected road networks
- Values are in minutes (converted from OSRM's seconds)

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*


### Property 1: Coordinate Order Transformation

*For any* list of [latitude, longitude] coordinate pairs, when constructing the OSRM API URL, the coordinates in the URL string should appear in [longitude, latitude] order (reversed from input).

**Validates: Requirements 1.2**

### Property 2: URL Format Compliance

*For any* set of N locations, the constructed OSRM URL should match the pattern `http://router.project-osrm.org/table/v1/driving/{coords}?annotations=duration` where `{coords}` is a semicolon-separated list of `lon,lat` pairs.

**Validates: Requirements 1.3**

### Property 3: Time Unit Conversion

*For any* OSRM API response containing duration values in seconds, the returned time matrix should contain those same values divided by 60.0 (converted to minutes).

**Validates: Requirements 1.4**

### Property 4: Matrix Dimensions

*For any* input of N locations, the returned time matrix should be an N×N matrix where the number of rows equals the number of columns equals N.

**Validates: Requirements 1.5**

### Property 5: Exception Handling for Network Errors

*For any* network error (ConnectionError, Timeout, HTTPError), when calling `get_osrm_matrix()`, the exception should propagate to the caller without crashing the application.

**Validates: Requirements 3.1, 3.5**

### Property 6: Fallback Activation

*For any* exception raised by `get_osrm_matrix()`, the `solve_routing()` function should automatically invoke `generate_time_matrix()` as a fallback and continue execution successfully.

**Validates: Requirements 3.2**

### Property 7: Fallback User Notification

*For any* OSRM API failure that triggers fallback mode, a warning message should be displayed to the user indicating that Haversine-based times are being used.

**Validates: Requirements 3.3, 6.2**

### Property 8: HTTP Error Handling

*For any* HTTP response with a non-200 status code, the `get_osrm_matrix()` function should raise an HTTPError exception.

**Validates: Requirements 5.3**

### Property 9: JSON Response Parsing

*For any* valid OSRM JSON response containing a "durations" field, the parsing should successfully extract the duration matrix without raising exceptions.

**Validates: Requirements 5.4**

## Error Handling

### Error Categories

1. **Network Errors**
   - `requests.exceptions.ConnectionError`: Network unreachable, DNS failure
   - `requests.exceptions.Timeout`: Request exceeds 10-second timeout
   - Handling: Catch in `solve_routing()`, fall back to `generate_time_matrix()`

2. **HTTP Errors**
   - `requests.exceptions.HTTPError`: Non-200 status codes (404, 500, etc.)
   - Handling: Raised by `response.raise_for_status()`, caught in `solve_routing()`

3. **Data Errors**
   - `json.JSONDecodeError`: Invalid JSON response
   - `KeyError`: Missing "durations" field in response
   - `ValueError`: Invalid data types or values
   - Handling: Catch in `solve_routing()`, fall back to `generate_time_matrix()`

4. **Input Validation Errors**
   - Empty location list
   - Invalid coordinate values (lat not in [-90, 90], lon not in [-180, 180])
   - Handling: Validate in `get_osrm_matrix()`, raise `ValueError` with descriptive message

### Error Flow Diagram

```
get_osrm_matrix(locations)
    ↓
Validate inputs
    ↓
    ├─ Invalid → Raise ValueError
    │
    └─ Valid → Construct URL
                  ↓
               Make HTTP request (timeout=10s)
                  ↓
                  ├─ Network Error → Raise ConnectionError/Timeout
                  ├─ HTTP Error → Raise HTTPError
                  │
                  └─ Success (200) → Parse JSON
                                        ↓
                                        ├─ Parse Error → Raise JSONDecodeError
                                        ├─ Missing Field → Raise KeyError
                                        │
                                        └─ Success → Return time_matrix

All exceptions caught in solve_routing():
    ↓
Display warning to user
    ↓
Fall back to generate_time_matrix()
    ↓
Continue with solver execution
```

### User-Facing Error Messages

**OSRM Success:**
```
✅ Using OSRM real road network travel times
```

**OSRM Failure (Generic):**
```
⚠️ OSRM API unavailable (ConnectionError). Using Haversine-based travel times (40 km/h average speed).
```

**OSRM Failure (Timeout):**
```
⚠️ OSRM API unavailable (Timeout). Using Haversine-based travel times (40 km/h average speed).
```

**OSRM Failure (HTTP Error):**
```
⚠️ OSRM API unavailable (HTTPError). Using Haversine-based travel times (40 km/h average speed).
```

## Testing Strategy

### Dual Testing Approach

This feature requires both unit tests and property-based tests to ensure comprehensive coverage:

- **Unit tests**: Verify specific examples, edge cases, and error conditions
- **Property tests**: Verify universal properties across all inputs

Both testing approaches are complementary and necessary for comprehensive coverage. Unit tests catch concrete bugs in specific scenarios, while property tests verify general correctness across a wide range of inputs.

### Unit Testing

**Test Cases for get_osrm_matrix():**

1. **Happy Path Test**
   - Input: 3 valid Mumbai locations
   - Expected: 3×3 matrix with reasonable travel times
   - Validates: Basic functionality

2. **Single Location Test**
   - Input: 1 location
   - Expected: 1×1 matrix with [0.0]
   - Validates: Edge case handling

3. **Coordinate Order Test**
   - Input: Known coordinates
   - Expected: URL contains lon,lat (not lat,lon)
   - Validates: Requirement 1.2

4. **Timeout Test**
   - Mock: Slow API response (>10 seconds)
   - Expected: Timeout exception raised
   - Validates: Requirement 3.4

5. **HTTP Error Test**
   - Mock: 404 or 500 response
   - Expected: HTTPError raised
   - Validates: Requirement 5.3

6. **Invalid JSON Test**
   - Mock: Malformed JSON response
   - Expected: JSONDecodeError raised
   - Validates: Error handling

7. **Missing Field Test**
   - Mock: JSON without "durations" field
   - Expected: KeyError raised
   - Validates: Error handling

**Test Cases for solve_routing() Integration:**

1. **OSRM Success Path**
   - Mock: Successful OSRM response
   - Expected: OSRM matrix used, success message displayed
   - Validates: Requirements 2.1, 2.2, 6.1

2. **OSRM Failure Fallback**
   - Mock: OSRM raises ConnectionError
   - Expected: Fallback to generate_time_matrix(), warning displayed
   - Validates: Requirements 3.1, 3.2, 3.3

3. **DLL Configuration Preservation**
   - Verify: DLL loading block unchanged after modifications
   - Expected: os.add_dll_directory() calls intact
   - Validates: Requirements 4.1, 4.2

### Property-Based Testing

**Configuration:**
- Library: Hypothesis (Python)
- Minimum iterations: 100 per property test
- Tag format: `# Feature: osrm-integration, Property {N}: {description}`

**Property Test 1: Coordinate Order Transformation**
```python
# Feature: osrm-integration, Property 1: Coordinate Order Transformation
@given(st.lists(st.tuples(st.floats(-90, 90), st.floats(-180, 180)), min_size=1, max_size=10))
def test_coordinate_order_property(locations):
    # For any list of [lat, lon] pairs, URL should contain lon,lat order
    url = construct_osrm_url(locations)
    for lat, lon in locations:
        assert f"{lon},{lat}" in url
```

**Property Test 2: URL Format Compliance**
```python
# Feature: osrm-integration, Property 2: URL Format Compliance
@given(st.lists(st.tuples(st.floats(-90, 90), st.floats(-180, 180)), min_size=1, max_size=10))
def test_url_format_property(locations):
    # For any locations, URL should match expected pattern
    url = construct_osrm_url(locations)
    assert url.startswith("http://router.project-osrm.org/table/v1/driving/")
    assert "?annotations=duration" in url
```

**Property Test 3: Time Unit Conversion**
```python
# Feature: osrm-integration, Property 3: Time Unit Conversion
@given(st.lists(st.lists(st.floats(0, 10000), min_size=1, max_size=10), min_size=1, max_size=10))
def test_time_conversion_property(durations_seconds):
    # For any duration matrix in seconds, output should be in minutes
    time_matrix = convert_durations_to_minutes(durations_seconds)
    for i in range(len(durations_seconds)):
        for j in range(len(durations_seconds[i])):
            assert abs(time_matrix[i][j] - durations_seconds[i][j] / 60.0) < 0.001
```

**Property Test 4: Matrix Dimensions**
```python
# Feature: osrm-integration, Property 4: Matrix Dimensions
@given(st.lists(st.tuples(st.floats(-90, 90), st.floats(-180, 180)), min_size=1, max_size=10))
def test_matrix_dimensions_property(locations):
    # For any N locations, output should be N×N matrix
    # Note: This requires mocking OSRM API
    with mock_osrm_response(locations):
        time_matrix = get_osrm_matrix(locations)
        n = len(locations)
        assert len(time_matrix) == n
        for row in time_matrix:
            assert len(row) == n
```

**Property Test 5: Exception Handling for Network Errors**
```python
# Feature: osrm-integration, Property 5: Exception Handling for Network Errors
@given(st.sampled_from([ConnectionError, Timeout, HTTPError]))
def test_network_error_handling_property(error_type):
    # For any network error, exception should propagate without crash
    with mock.patch('requests.get', side_effect=error_type("Test error")):
        with pytest.raises(error_type):
            get_osrm_matrix([[19.065, 72.835]])
```

**Property Test 6: Fallback Activation**
```python
# Feature: osrm-integration, Property 6: Fallback Activation
@given(st.sampled_from([ConnectionError, Timeout, HTTPError, JSONDecodeError, KeyError]))
def test_fallback_property(error_type):
    # For any OSRM error, solve_routing should fall back successfully
    with mock.patch('get_osrm_matrix', side_effect=error_type("Test error")):
        # Should not raise exception, should use fallback
        routes, time_ms = solve_routing(customers, capacity, num_vehicles, df)
        assert routes is not None
```

**Property Test 7: Fallback User Notification**
```python
# Feature: osrm-integration, Property 7: Fallback User Notification
@given(st.sampled_from([ConnectionError, Timeout, HTTPError]))
def test_fallback_notification_property(error_type):
    # For any OSRM failure, warning message should be displayed
    with mock.patch('get_osrm_matrix', side_effect=error_type("Test error")):
        with mock.patch('streamlit.warning') as mock_warning:
            solve_routing(customers, capacity, num_vehicles, df)
            assert mock_warning.called
            assert "Haversine" in str(mock_warning.call_args)
```

### Integration Testing

**End-to-End Test:**
1. Start dashboard
2. Load demo data
3. Click "Run Solver"
4. Verify OSRM is called (or fallback if API down)
5. Verify routes are generated
6. Verify appropriate message displayed

**Manual Testing Checklist:**
- [ ] Dashboard loads without errors
- [ ] DLL loading still works on Windows
- [ ] OSRM success message appears when API is available
- [ ] Fallback warning appears when API is unavailable (test by disconnecting network)
- [ ] Routes are generated in both OSRM and fallback modes
- [ ] No crashes or unhandled exceptions

## Implementation Notes

### Dependencies

**New Dependency:**
```python
import requests  # For HTTP communication with OSRM API
```

**Installation:**
```bash
pip install requests
```

### Code Location

All changes are confined to `dashboard/app.py`:
- Add `get_osrm_matrix()` function after `generate_time_matrix()`
- Modify `solve_routing()` function to use OSRM with fallback
- No changes to C++ code, bindings, or other Python files

### Performance Considerations

**OSRM API Latency:**
- Typical response time: 100-500ms for small matrices (<20 locations)
- Timeout set to 10 seconds to handle larger matrices or slow networks
- Fallback ensures user experience is not degraded by API issues

**Comparison:**
- Haversine calculation: ~1ms for 10 locations (local computation)
- OSRM API call: ~200ms for 10 locations (network + computation)
- Trade-off: Slightly slower but much more accurate

### Future Enhancements

1. **Caching:** Cache OSRM responses to avoid repeated API calls for same locations
2. **Self-Hosted OSRM:** Deploy local OSRM instance for faster response times and no rate limits
3. **Traffic Data:** Integrate real-time traffic data for time-of-day routing
4. **Alternative Routing Engines:** Support for Google Maps API, Mapbox, etc.
5. **Batch Processing:** Optimize for large location sets using OSRM's batch API features
