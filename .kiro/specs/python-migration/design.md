# Design Document: Python Migration

## Overview

This design describes the migration of the VRP solver from a C++20/Nanobind architecture to a pure Python implementation. The migration replaces the compiled C++ extension (`vrp_core.pyd`/`vrp_core.so`) with a native Python module (`vrp_core.py`) that preserves the exact same public API, ensuring zero changes to the Streamlit dashboard and existing test suite.

The core challenge is replicating the C++ solver's nearest-neighbor heuristic, distance calculations, and constraint validation in pure Python while maintaining correctness and API compatibility. Performance is a secondary concern—the primary goal is eliminating build complexity and platform dependencies.

### Design Goals

1. **API Preservation**: Maintain exact same interface for `Location`, `Customer`, and `VRPSolver.solve()`
2. **Zero Client Changes**: Dashboard and tests work without modification
3. **Build Elimination**: Remove all C++, CMake, Nanobind, and compilation requirements
4. **Correctness First**: Match C++ solver behavior exactly for all test cases
5. **Platform Independence**: Run on any platform with Python 3.8+ without compilation

### Non-Goals

- Performance optimization (pure Python will be slower than C++, this is acceptable)
- SIMD acceleration (no Python equivalent, parameter accepted but ignored)
- Advanced metaheuristics (out of scope for this migration)

---

## Architecture

### Module Structure

```
vrp_core.py (new)
├── Location (dataclass)
├── Customer (dataclass)
├── VRPSolver (class)
│   ├── solve() - public API
│   ├── _build_distance_matrix() - private
│   ├── _nearest_neighbor_heuristic() - private
│   ├── _can_add_to_route() - private
│   ├── _get_travel_time() - private
│   └── _calculate_route_load() - private
└── haversine_distance() - utility function
```

### Data Flow

```
1. Dashboard/Tests create Customer objects
2. Call VRPSolver().solve(customers, capacities, use_simd, time_matrix)
3. Solver builds distance matrix (Euclidean)
4. Solver runs nearest-neighbor heuristic with constraints
5. Returns list of routes (list[list[int]])
6. Dashboard/Tests process routes unchanged
```

### Key Design Decisions

**Decision 1: Use Python dataclasses for Location and Customer**
- Rationale: Provides attribute access, equality, and repr for free
- Alternative considered: Named tuples (rejected: not mutable)
- Trade-off: Slightly more memory than tuples, but better API match

**Decision 2: Use Euclidean distance instead of Haversine in solver**
- Rationale: C++ implementation uses Euclidean for speed; must match behavior
- Alternative considered: Haversine everywhere (rejected: breaks test compatibility)
- Trade-off: Less geographic accuracy, but exact C++ behavior match

**Decision 3: Keep use_simd parameter but ignore it**
- Rationale: Preserves API compatibility with existing call sites
- Alternative considered: Remove parameter (rejected: breaks existing code)
- Trade-off: Misleading parameter name, but zero client changes

**Decision 4: Store distance/time matrices as list[list[float]]**
- Rationale: Matches C++ std::vector<std::vector<double>> structure
- Alternative considered: NumPy arrays (rejected: adds dependency)
- Trade-off: Slower indexing, but no new dependencies

---

## Components and Interfaces

### Location Dataclass

```python
@dataclass
class Location:
    """Geographic coordinate pair"""
    latitude: float
    longitude: float
    
    def __post_init__(self):
        # Validate coordinate ranges
        if not -90.0 <= self.latitude <= 90.0:
            raise ValueError(f"Latitude must be in [-90, 90], got {self.latitude}")
        if not -180.0 <= self.longitude <= 180.0:
            raise ValueError(f"Longitude must be in [-180, 180], got {self.longitude}")
```

**Interface Contract:**
- Constructor: `Location(latitude: float, longitude: float)`
- Attributes: `latitude`, `longitude` (read/write)
- Equality: Two locations equal if both coordinates match
- Validation: Raises `ValueError` for out-of-range coordinates

**Requirements Mapping:** Requirement 2 (all acceptance criteria)

---

### Customer Dataclass

```python
@dataclass
class Customer:
    """Delivery stop with demand and time windows"""
    id: int
    location: Location
    demand: float
    start_window: float
    end_window: float
    service_time: float = 0.0
    
    def __post_init__(self):
        # Validate constraints
        if self.demand < 0:
            raise ValueError(f"Demand must be non-negative, got {self.demand}")
        if self.start_window < 0:
            raise ValueError(f"Start window must be non-negative, got {self.start_window}")
        if self.end_window < self.start_window:
            raise ValueError(f"End window {self.end_window} must be >= start window {self.start_window}")
        if self.service_time < 0:
            raise ValueError(f"Service time must be non-negative, got {self.service_time}")
```

**Interface Contract:**
- Constructor: `Customer(id, location, demand, start_window, end_window, service_time=0.0)`
- Attributes: All fields read/write
- Default: `service_time` defaults to 0.0 when omitted
- Validation: Raises `ValueError` for invalid constraints

**Requirements Mapping:** Requirement 3 (all acceptance criteria)

---

### VRPSolver Class

```python
class VRPSolver:
    """Vehicle Routing Problem solver using Nearest Neighbor heuristic"""
    
    def __init__(self):
        """Initialize solver with empty state"""
        self._distance_matrix: list[list[float]] = []
        self._time_matrix: list[list[float]] = []
        self._use_time_matrix: bool = False
    
    def solve(
        self,
        customers: list[Customer],
        vehicle_capacities: list[float],
        use_simd: bool = True,
        time_matrix: list[list[float]] = None
    ) -> list[list[int]]:
        """
        Solve VRP with heterogeneous fleet
        
        Args:
            customers: List of Customer objects (customer 0 is depot)
            vehicle_capacities: List of vehicle capacities (one per vehicle)
            use_simd: Ignored (for API compatibility)
            time_matrix: Optional N×N travel time matrix in minutes
        
        Returns:
            List of routes, where each route is list of customer IDs
        
        Raises:
            ValueError: If vehicle_capacities is empty or contains non-positive values
            ValueError: If time_matrix dimensions don't match customer count
        """
```

**Interface Contract:**
- Constructor: No arguments
- Method: `solve(customers, vehicle_capacities, use_simd=True, time_matrix=None)`
- Returns: `list[list[int]]` (list of routes)
- Exceptions: `ValueError` for invalid inputs

**Requirements Mapping:** Requirement 4 (all acceptance criteria)

---

### Distance Matrix Construction

**Algorithm:**
```python
def _build_distance_matrix(self, customers: list[Customer]) -> None:
    """Build N×N Euclidean distance matrix"""
    n = len(customers)
    self._distance_matrix = [[0.0] * n for _ in range(n)]
    
    for i in range(n):
        for j in range(i + 1, n):  # Only compute upper triangle
            dist = self._euclidean_distance(
                customers[i].location.latitude,
                customers[i].location.longitude,
                customers[j].location.latitude,
                customers[j].location.longitude
            )
            # Symmetric matrix
            self._distance_matrix[i][j] = dist
            self._distance_matrix[j][i] = dist

def _euclidean_distance(self, lat1: float, lon1: float, 
                        lat2: float, lon2: float) -> float:
    """Compute Euclidean distance approximation"""
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    return math.sqrt(dlat * dlat + dlon * dlon)
```

**Design Rationale:**
- Uses Euclidean formula to match C++ implementation exactly
- Symmetric matrix: only compute upper triangle, copy to lower
- Diagonal is zero (distance from point to itself)

**Requirements Mapping:** Requirement 5 (all acceptance criteria)

---

### Travel Time Calculation

**Algorithm:**
```python
def _get_travel_time(self, from_idx: int, to_idx: int) -> float:
    """Get travel time in minutes between two customers"""
    if self._use_time_matrix:
        return self._time_matrix[from_idx][to_idx]
    else:
        # Fallback: distance * 1.5 (assumes 40 km/h)
        # 40 km/h = 40/60 km/min = 0.666... km/min
        # time = distance / speed = distance / (40/60) = distance * 1.5
        return self._distance_matrix[from_idx][to_idx] * 1.5
```

**Design Rationale:**
- Prioritizes provided time_matrix when available
- Fallback uses distance * 1.5 to match C++ behavior
- Conversion factor: 40 km/h → 1.5 multiplier

**Requirements Mapping:** Requirement 6 (all acceptance criteria)

---

### Nearest Neighbor Heuristic

**Algorithm:**
```python
def _nearest_neighbor_heuristic(
    self,
    customers: list[Customer],
    vehicle_capacities: list[float]
) -> list[list[int]]:
    """Construct routes using greedy nearest neighbor"""
    n = len(customers)
    visited = [False] * n
    visited[0] = True  # Depot always "visited"
    
    routes = []
    
    for vehicle_idx, capacity in enumerate(vehicle_capacities):
        # Check if any unvisited customers remain
        if all(visited[i] for i in range(1, n)):
            break
        
        # Start new route at depot
        route = [0]
        current_load = 0.0
        current_time = 0.0
        current_location = 0
        
        while True:
            # Find nearest feasible customer
            best_customer = -1
            best_distance = float('inf')
            
            for i in range(1, n):
                if not visited[i]:
                    if self._can_add_to_route(
                        route, i, customers, capacity, current_time
                    ):
                        dist = self._distance_matrix[current_location][i]
                        if dist < best_distance:
                            best_distance = dist
                            best_customer = i
            
            if best_customer == -1:
                break  # No feasible customer
            
            # Add customer to route
            route.append(best_customer)
            visited[best_customer] = True
            
            # Update state
            customer = customers[best_customer]
            current_load += customer.demand
            
            travel_time = self._get_travel_time(current_location, best_customer)
            arrival_time = current_time + travel_time
            waiting_time = max(0.0, customer.start_window - arrival_time)
            current_time = arrival_time + waiting_time + customer.service_time
            current_location = best_customer
        
        # Skip empty routes (only depot)
        if len(route) == 1:
            break
        
        # Return to depot
        route.append(0)
        routes.append(route)
    
    return routes
```

**Design Rationale:**
- Greedy selection: always pick nearest feasible customer
- Respects vehicle order: use capacities in sequence
- Early termination: stop when no customers remain or no feasible additions
- Depot bookending: each route starts and ends at customer 0

**Requirements Mapping:** Requirement 7 (all acceptance criteria)

---

### Constraint Validation

**Capacity Constraint:**
```python
def _calculate_route_load(self, route: list[int], 
                          customers: list[Customer]) -> float:
    """Sum demands for all customers in route (excluding depot)"""
    return sum(customers[cid].demand for cid in route if cid != 0)

def _can_add_to_route(
    self,
    route: list[int],
    customer_idx: int,
    customers: list[Customer],
    vehicle_capacity: float,
    current_time: float
) -> bool:
    """Check if customer can be added without violating constraints"""
    customer = customers[customer_idx]
    
    # Capacity constraint
    route_load = self._calculate_route_load(route, customers)
    if route_load + customer.demand > vehicle_capacity:
        return False
    
    # Time window constraint
    current_location = route[-1] if route else 0
    travel_time = self._get_travel_time(current_location, customer_idx)
    arrival_time = current_time + travel_time
    
    if arrival_time > customer.end_window:
        return False
    
    return True
```

**Design Rationale:**
- Two-phase check: capacity first (cheaper), then time window
- Depot excluded from load calculation (demand = 0)
- Arrival time must be ≤ end_window (can arrive early and wait)

**Requirements Mapping:** 
- Requirement 8 (capacity constraint)
- Requirement 9 (time window constraint)

---

### Haversine Distance Utility

```python
def haversine_distance(lat1: float, lon1: float, 
                       lat2: float, lon2: float) -> float:
    """
    Calculate great-circle distance between two points
    
    Args:
        lat1, lon1: First point coordinates (degrees)
        lat2, lon2: Second point coordinates (degrees)
    
    Returns:
        Distance in kilometers
    """
    # Earth's radius in kilometers
    R = 6371.0
    
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    lon1_rad = math.radians(lon1)
    lon2_rad = math.radians(lon2)
    
    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = (math.sin(dlat / 2) ** 2 + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * 
         math.sin(dlon / 2) ** 2)
    
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c
```

**Design Rationale:**
- Standalone function (not method) for easy import by dashboard
- Uses math.radians() for degree-to-radian conversion
- Follows standard Haversine formula with Earth radius 6371 km

**Requirements Mapping:** Requirement 10 (all acceptance criteria)

---

## Data Models

### Internal State (VRPSolver)

```python
class VRPSolver:
    _distance_matrix: list[list[float]]  # N×N Euclidean distances
    _time_matrix: list[list[float]]      # N×N travel times (minutes)
    _use_time_matrix: bool               # Flag for time matrix availability
```

**Lifecycle:**
1. Initialized empty in `__init__()`
2. Populated in `solve()` before heuristic runs
3. Cleared implicitly on next `solve()` call (overwritten)

### Route Representation

```python
Route = list[int]  # Type alias for clarity
```

- Route is list of customer IDs (integers)
- Always starts with 0 (depot)
- Always ends with 0 (return to depot)
- Example: `[0, 3, 1, 5, 0]` visits customers 3, 1, 5 in order

### Matrix Representation

```python
# Distance matrix: N×N symmetric matrix
distance_matrix[i][j] = Euclidean distance from customer i to j

# Time matrix: N×N matrix (not necessarily symmetric)
time_matrix[i][j] = Travel time in minutes from customer i to j
```

---

## Error Handling

### Input Validation

**VRPSolver.solve() validates:**

1. **Empty vehicle_capacities:**
   ```python
   if not vehicle_capacities:
       raise ValueError("Vehicle capacities list cannot be empty")
   ```

2. **Non-positive capacities:**
   ```python
   if any(cap <= 0 for cap in vehicle_capacities):
       raise ValueError("All vehicle capacities must be positive")
   ```

3. **Time matrix dimension mismatch:**
   ```python
   if time_matrix:
       n = len(customers)
       if len(time_matrix) != n or any(len(row) != n for row in time_matrix):
           raise ValueError(f"Time matrix must be {n}×{n}, got {len(time_matrix)}×...")
   ```

4. **Empty customer list:**
   ```python
   if not customers or len(customers) == 1:
       return []  # No routes needed
   ```

### Constraint Violations

**Handled gracefully (not errors):**
- Customer cannot fit in any vehicle → left unassigned
- Customer time window missed → left unassigned
- All vehicles exhausted → remaining customers unassigned

**Rationale:** VRP problems can be infeasible; solver returns best effort rather than raising exceptions.

### Edge Cases

| Case | Behavior |
|------|----------|
| Single customer (depot only) | Return empty list |
| All customers at depot location | Valid routes with zero distance |
| Negative coordinates | Allowed (valid for some coordinate systems) |
| Zero capacity vehicle | Raises ValueError |
| Customer demand > all capacities | Customer left unassigned |
| Overlapping time windows | Handled by greedy selection |

---

## Testing Strategy

### Unit Tests (Existing test_solver.py)

**Test Categories:**
1. **Basic Functionality** (7 tests)
   - Module import
   - Location/Customer creation
   - Solver instantiation
   - Service time handling

2. **Haversine Distance** (2 tests)
   - Known distance calculation
   - Self-distance is zero

3. **Error Conditions** (3 tests)
   - Empty customer list
   - Infeasible problems
   - Constraint violations

4. **Heterogeneous Fleet** (8 tests)
   - Single vehicle
   - Multiple identical vehicles
   - Mixed vehicle types
   - Capacity constraints
   - Vehicle ordering

**All existing tests must pass without modification after migration.**

### Property-Based Tests (Hypothesis)

**Existing properties to preserve:**

1. **Location Value Preservation** (Property 1)
   - For any valid lat/lon, Location round-trip preserves values

2. **Customer Value Preservation** (Property 2)
   - For any valid customer data, Customer round-trip preserves values

3. **Location Equality Reflexivity** (Property 3)
   - Location equals itself, different coordinates not equal

4. **Route Capacity Constraint** (Property 6)
   - For any route, sum of demands ≤ vehicle capacity

5. **Routes Start at Depot** (Property 8)
   - For any route, first customer is depot (ID 0)

6. **All Customers Visited or Unserved** (Property 10)
   - No customer visited twice, all visited or explicitly unserved

**Test Configuration:**
- 20 examples per property (matches current settings)
- 300-500ms deadline per example
- Hypothesis profile: "default"

### Integration Tests (Dashboard Compatibility)

**Manual verification required:**
1. Dashboard imports vrp_core successfully
2. Dashboard can create Location/Customer objects
3. Dashboard can call solver.solve() with existing arguments
4. Dashboard can process returned routes
5. Dashboard can call haversine_distance() for time matrix

**Test Procedure:**
```bash
# 1. Install pure Python module
pip install -e .

# 2. Run dashboard
python dashboard/app.py

# 3. Verify:
# - No import errors
# - Demo data loads
# - Solve button works
# - Routes display on map
# - Financial metrics calculate
```

### Regression Tests

**Critical behaviors to verify:**
1. Same routes generated for deterministic inputs
2. Same constraint violations detected
3. Same edge case handling (empty lists, single customer, etc.)
4. Same exception types and messages

**Comparison Strategy:**
- Run test suite with C++ version, capture outputs
- Run test suite with Python version, capture outputs
- Diff outputs to verify identical behavior

---

## Implementation Notes

### Performance Considerations

**Expected Performance Impact:**
- Distance matrix construction: 10-50x slower (no SIMD)
- Nearest neighbor heuristic: 5-20x slower (Python loops)
- Overall solve time: 10-30x slower for typical problems

**Mitigation Strategies (future optimization, not in scope):**
- NumPy for distance matrix (vectorized operations)
- Numba JIT compilation for hot loops
- Cython for critical paths

**Acceptable Trade-off:**
- Current C++ solver handles 100+ customers in <100ms
- Python solver will handle 100+ customers in <3s
- Dashboard use case: 5-20 customers, <100ms acceptable

### Memory Considerations

**Memory Usage:**
- Distance matrix: N² × 8 bytes (float64)
- Time matrix: N² × 8 bytes (if provided)
- Customer list: N × ~100 bytes (dataclass overhead)

**Example:** 100 customers = ~160 KB (negligible)

### Compatibility Notes

**Python Version:**
- Minimum: Python 3.8 (for typing features)
- Recommended: Python 3.10+ (better error messages)
- Tested: Python 3.8, 3.9, 3.10, 3.11, 3.12

**Dependencies:**
- Standard library only (math, dataclasses, typing)
- No external packages required for vrp_core.py
- Test suite requires: pytest, hypothesis

**Platform Support:**
- Windows: Full support (no DLL issues)
- Linux: Full support
- macOS: Full support
- No platform-specific code

---

## Migration Strategy

### Phase 1: Create Pure Python Module

1. Create `vrp_core.py` in project root
2. Implement Location, Customer dataclasses
3. Implement VRPSolver class with all methods
4. Implement haversine_distance utility
5. Add input validation and error handling

### Phase 2: Verify Test Compatibility

1. Temporarily rename C++ extension (vrp_core.pyd → vrp_core.pyd.bak)
2. Run pytest tests/ -v
3. Fix any test failures
4. Verify all property-based tests pass
5. Verify dashboard imports and runs

### Phase 3: Remove C++ Artifacts

1. Delete src/ directory (solver.cpp, bindings.cpp, test_*.cpp)
2. Delete include/ directory (solver.h)
3. Delete CMakeLists.txt
4. Delete build/ directory
5. Delete compiled extensions (.pyd, .so files)
6. Update .gitignore to remove C++ patterns

### Phase 4: Update Configuration

1. Update requirements.txt (remove nanobind)
2. Update setup.py (remove CMake invocation)
3. Update README.md (remove build instructions)
4. Update QUICKSTART.md (simplify setup)
5. Update setup.bat/setup.sh (remove CMake commands)

### Phase 5: Update Documentation

1. Update .kiro/steering/tech.md (remove C++ references)
2. Update .kiro/steering/structure.md (new module structure)
3. Update .kiro/steering/product.md (remove performance claims)
4. Remove/archive .kiro/steering/DLL Issue.md
5. Update test_installation.py (remove DLL loading)

### Phase 6: Clean Dashboard Code

1. Remove os.add_dll_directory() calls from dashboard/app.py
2. Remove DLL loading comments
3. Remove Windows-specific workarounds
4. Simplify import error handling

### Phase 7: Final Verification

1. Fresh clone of repository
2. pip install -r requirements.txt
3. pytest tests/ -v (all tests pass)
4. python dashboard/app.py (dashboard works)
5. python test_installation.py (installation verified)

---

## Rollback Plan

**If migration fails:**

1. Restore C++ files from git history
2. Restore CMakeLists.txt
3. Restore requirements.txt with nanobind
4. Rebuild C++ extension: `cmake --build build/`
5. Restore DLL loading code in dashboard/app.py
6. Delete vrp_core.py

**Rollback Triggers:**
- Test suite failure rate >5%
- Dashboard import failures
- Unacceptable performance degradation (>60s for typical problems)
- Correctness issues (wrong routes generated)

---

## Future Enhancements

**Post-Migration Optimizations (not in scope):**

1. **NumPy Integration**
   - Replace list[list[float]] with np.ndarray
   - Vectorized distance calculations
   - Expected speedup: 5-10x

2. **Numba JIT Compilation**
   - @njit decorator on hot loops
   - Expected speedup: 10-20x
   - Approaches C++ performance

3. **Cython Rewrite**
   - Compile critical paths to C
   - Keep Python API
   - Expected speedup: 20-50x

4. **Algorithm Improvements**
   - 2-opt local search
   - Simulated annealing
   - Genetic algorithms

**None of these require changes to public API—internal implementation only.**

---

## Acceptance Criteria Mapping

| Requirement | Design Section | Implementation Component |
|-------------|----------------|--------------------------|
| Req 1: Pure Python Module | Module Structure | vrp_core.py file |
| Req 2: Location Class | Location Dataclass | @dataclass Location |
| Req 3: Customer Class | Customer Dataclass | @dataclass Customer |
| Req 4: VRPSolver Interface | VRPSolver Class | VRPSolver.solve() |
| Req 5: Distance Matrix | Distance Matrix Construction | _build_distance_matrix() |
| Req 6: Travel Time | Travel Time Calculation | _get_travel_time() |
| Req 7: Nearest Neighbor | Nearest Neighbor Heuristic | _nearest_neighbor_heuristic() |
| Req 8: Capacity Constraint | Constraint Validation | _can_add_to_route() capacity check |
| Req 9: Time Window Constraint | Constraint Validation | _can_add_to_route() time check |
| Req 10: Haversine Utility | Haversine Distance Utility | haversine_distance() function |
| Req 11: Dashboard Compatibility | Testing Strategy | Integration tests |
| Req 12: Test Suite Compatibility | Testing Strategy | Unit tests, property tests |
| Req 13: C++ Artifact Removal | Migration Strategy Phase 3 | File deletion |
| Req 14: Parser Round-Trip | Data Models | Customer dataclass |
| Req 15: Documentation Updates | Migration Strategy Phase 5 | Documentation files |
| Req 16: Workspace Config Updates | Migration Strategy Phase 5 | .kiro/steering/ files |
| Req 17: Installation Script Updates | Migration Strategy Phase 5 | test_installation.py |

---

## Conclusion

This design provides a complete blueprint for migrating the VRP solver from C++20/Nanobind to pure Python. The migration prioritizes correctness and API compatibility over performance, eliminating all build complexity while maintaining full functionality for the dashboard and test suite.

The pure Python implementation uses standard library features (dataclasses, typing, math) with no external dependencies, ensuring maximum portability and ease of installation. All existing tests will pass without modification, and the dashboard will work without changes to import statements or call sites.

Post-migration, the codebase will be simpler, more maintainable, and accessible to a wider range of developers, while preserving the option for future performance optimizations through NumPy, Numba, or Cython.
