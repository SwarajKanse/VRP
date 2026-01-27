# Design Document: cpp-vrp-solver-foundation

## Overview

This design document describes the architecture and implementation approach for a high-performance Vehicle Routing Problem (VRP) solver foundation built in C++20 with Python bindings via Nanobind. The system implements a Capacitated VRP (CVRP) solver with Time Windows (VRPTW) support using a Nearest Neighbor heuristic.

The design prioritizes:
- **High performance**: Precomputed distance matrices, efficient data structures, minimal allocations
- **Future extensibility**: Architecture supports future refactoring to Data-Oriented Design (SoA) and custom allocators
- **Python interoperability**: Clean Nanobind bindings for seamless Python integration
- **Simplicity**: Straightforward implementation suitable as a foundation for future optimizations

## Architecture

The system follows a layered architecture:

```
┌─────────────────────────────────────┐
│      Python Application Layer       │
│         (test_solver.py)            │
└─────────────────────────────────────┘
                 │
                 │ import vrp_core
                 ▼
┌─────────────────────────────────────┐
│     Nanobind Binding Layer          │
│       (bindings.cpp)                │
└─────────────────────────────────────┘
                 │
                 │ exposes
                 ▼
┌─────────────────────────────────────┐
│      C++ Core Layer                 │
│  ┌─────────────────────────────┐   │
│  │   VRPSolver                 │   │
│  │   - solve()                 │   │
│  │   - buildDistanceMatrix()   │   │
│  │   - nearestNeighbor()       │   │
│  └─────────────────────────────┘   │
│  ┌─────────────────────────────┐   │
│  │   Data Structures           │   │
│  │   - Location                │   │
│  │   - Customer                │   │
│  │   - Route                   │   │
│  └─────────────────────────────┘   │
└─────────────────────────────────────┘
```

### Key Architectural Decisions

1. **Separation of Concerns**: Data structures (Location, Customer) are separate from solver logic (VRPSolver)
2. **Precomputation Strategy**: Distance matrix is computed once per solve() call and reused throughout route construction
3. **Greedy Heuristic**: Nearest Neighbor provides O(n²) time complexity for initial solution
4. **Binding Layer Isolation**: Nanobind bindings are in a separate compilation unit, keeping core logic independent
5. **Future-Proof Design**: Struct-based design can be refactored to SoA layout without changing public API

## Components and Interfaces

### 1. Location Struct

Represents a geographic coordinate.

```cpp
struct Location {
    double latitude;
    double longitude;
    
    Location(double lat, double lon);
    
    bool operator==(const Location& other) const;
};
```

**Responsibilities:**
- Store geographic coordinates
- Support equality comparison

**Design Notes:**
- Simple POD-like struct for cache efficiency
- Future refactor: Can be converted to parallel arrays (lat[], lon[]) for SIMD operations

### 2. Customer Struct

Represents a delivery customer with demand and time window constraints.

```cpp
struct Customer {
    int id;
    Location location;
    double demand;
    double start_window;
    double end_window;
    
    Customer(int id, Location loc, double demand, 
             double start_w, double end_w);
};
```

**Responsibilities:**
- Store customer attributes
- Encapsulate location, demand, and time window data

**Design Notes:**
- Includes Location by value for locality
- Time windows represented as doubles (hours or timestamps)
- Future refactor: Can be converted to SoA layout for vectorization

### 3. Route Type

Represents a vehicle route as a sequence of customer IDs.

```cpp
using Route = std::vector<int>;
```

**Responsibilities:**
- Store ordered sequence of customer visits
- Support dynamic growth during route construction

**Design Notes:**
- Simple type alias for clarity
- Customer IDs rather than pointers for Python interoperability
- Depot (customer 0) is implicit start/end point

### 4. VRPSolver Class

Core solver implementing the Nearest Neighbor heuristic.

```cpp
class VRPSolver {
public:
    VRPSolver();
    
    std::vector<Route> solve(
        const std::vector<Customer>& customers,
        double vehicle_capacity
    );

private:
    std::vector<std::vector<double>> distance_matrix_;
    
    void buildDistanceMatrix(const std::vector<Customer>& customers);
    
    double haversineDistance(const Location& loc1, const Location& loc2);
    
    std::vector<Route> nearestNeighborHeuristic(
        const std::vector<Customer>& customers,
        double vehicle_capacity
    );
    
    bool canAddToRoute(
        const Route& route,
        int customer_idx,
        const std::vector<Customer>& customers,
        double vehicle_capacity,
        double current_time
    );
    
    double calculateRouteLoad(
        const Route& route,
        const std::vector<Customer>& customers
    );
};
```

**Public Interface:**
- `solve()`: Main entry point, returns list of routes

**Private Methods:**
- `buildDistanceMatrix()`: Precomputes all pairwise distances using Haversine formula
- `haversineDistance()`: Calculates great-circle distance between two locations
- `nearestNeighborHeuristic()`: Constructs routes using greedy nearest neighbor approach
- `canAddToRoute()`: Validates capacity and time window constraints
- `calculateRouteLoad()`: Sums demand for customers in a route

**Design Notes:**
- Distance matrix stored as member variable, reused across route construction
- Stateless design: solve() can be called multiple times
- Future refactor: Can accept custom allocator template parameter

### 5. Nanobind Binding Module

Exposes C++ classes to Python.

```cpp
#include <nanobind/nanobind.h>
#include <nanobind/stl/vector.h>

namespace nb = nanobind;

NB_MODULE(vrp_core, m) {
    nb::class_<Location>(m, "Location")
        .def(nb::init<double, double>())
        .def_rw("latitude", &Location::latitude)
        .def_rw("longitude", &Location::longitude);
    
    nb::class_<Customer>(m, "Customer")
        .def(nb::init<int, Location, double, double, double>())
        .def_rw("id", &Customer::id)
        .def_rw("location", &Customer::location)
        .def_rw("demand", &Customer::demand)
        .def_rw("start_window", &Customer::start_window)
        .def_rw("end_window", &Customer::end_window);
    
    nb::class_<VRPSolver>(m, "VRPSolver")
        .def(nb::init<>())
        .def("solve", &VRPSolver::solve);
}
```

**Responsibilities:**
- Define Python-visible classes and methods
- Handle type conversions between Python and C++
- Expose module as `vrp_core`

**Design Notes:**
- Uses Nanobind's automatic STL container conversion for vectors
- Read-write properties for all struct fields
- Minimal binding code for maintainability

## Data Models

### Distance Matrix

The distance matrix is a 2D vector storing precomputed distances:

```cpp
std::vector<std::vector<double>> distance_matrix_;
// distance_matrix_[i][j] = distance from customer i to customer j
```

**Properties:**
- Symmetric: `distance_matrix_[i][j] == distance_matrix_[j][i]`
- Diagonal is zero: `distance_matrix_[i][i] == 0`
- Size: `n × n` where `n` is number of customers (including depot)

**Computation:**
- Built once per solve() invocation
- Uses Haversine formula for great-circle distance
- Stored in kilometers

### Haversine Distance Formula

The Haversine formula calculates the great-circle distance between two points on a sphere:

```
a = sin²(Δlat/2) + cos(lat1) × cos(lat2) × sin²(Δlon/2)
c = 2 × atan2(√a, √(1-a))
distance = R × c
```

Where:
- `R` = Earth's radius (6371 km)
- `lat1, lon1` = coordinates of first location (in radians)
- `lat2, lon2` = coordinates of second location (in radians)
- `Δlat = lat2 - lat1`
- `Δlon = lon2 - lon1`

**Implementation Notes:**
- Convert degrees to radians: `radians = degrees × π / 180`
- Use `std::sin`, `std::cos`, `std::atan2` from `<cmath>`
- Result is in kilometers

### Route Construction State

During Nearest Neighbor heuristic execution, the algorithm maintains:

```cpp
struct RouteState {
    std::vector<bool> visited;      // visited[i] = true if customer i is in a route
    std::vector<Route> routes;      // completed and in-progress routes
    Route current_route;            // route being constructed
    double current_load;            // total demand in current_route
    double current_time;            // current time (for time window validation)
    int current_location;           // last customer added to current_route
};
```

**State Transitions:**
1. Initialize: All customers unvisited, start at depot (customer 0)
2. Select: Find nearest unvisited customer that satisfies constraints
3. Add: Add customer to current route, update load and time
4. Complete: When no feasible customer exists, finalize route and start new one
5. Terminate: When all customers visited or no more feasible routes

## Algorithms

### Nearest Neighbor Heuristic

**Algorithm:**

```
function nearestNeighborHeuristic(customers, vehicle_capacity):
    visited = [false] * len(customers)
    routes = []
    
    visited[0] = true  // depot is always "visited"
    
    while any unvisited customers exist:
        current_route = [0]  // start at depot
        current_load = 0
        current_time = 0
        current_location = 0
        
        while true:
            best_customer = null
            best_distance = infinity
            
            for each unvisited customer c:
                if canAddToRoute(current_route, c, vehicle_capacity, current_time):
                    distance = distance_matrix[current_location][c.id]
                    if distance < best_distance:
                        best_distance = distance
                        best_customer = c
            
            if best_customer is null:
                break  // no feasible customer, complete route
            
            // Add customer to route
            current_route.append(best_customer.id)
            visited[best_customer.id] = true
            current_load += best_customer.demand
            current_time += distance_matrix[current_location][best_customer.id]
            current_location = best_customer.id
        
        current_route.append(0)  // return to depot
        routes.append(current_route)
        
        if all customers visited:
            break
    
    return routes
```

**Complexity:**
- Time: O(n² × m) where n = customers, m = routes (typically m << n)
- Space: O(n²) for distance matrix + O(n) for visited array

**Constraint Validation:**

```
function canAddToRoute(route, customer, capacity, current_time):
    // Check capacity constraint
    route_load = sum of demands in route
    if route_load + customer.demand > capacity:
        return false
    
    // Check time window constraint
    arrival_time = current_time + travel_time_to_customer
    if arrival_time > customer.end_window:
        return false  // too late
    
    // If arrive early, wait until start_window
    service_time = max(arrival_time, customer.start_window)
    
    return true
```

### Distance Matrix Construction

**Algorithm:**

```
function buildDistanceMatrix(customers):
    n = len(customers)
    distance_matrix = n × n matrix
    
    for i in 0..n-1:
        for j in 0..n-1:
            if i == j:
                distance_matrix[i][j] = 0
            else:
                distance_matrix[i][j] = haversineDistance(
                    customers[i].location,
                    customers[j].location
                )
    
    return distance_matrix
```

**Optimization Opportunities:**
- Symmetry: Only compute upper triangle, mirror to lower triangle
- Parallelization: Distance calculations are independent (future optimization)
- SIMD: Vectorize Haversine calculations (future optimization with SoA layout)

## Build System

### CMakeLists.txt Structure

```cmake
cmake_minimum_required(VERSION 3.15)
project(vrp_solver CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find Python and Nanobind
find_package(Python COMPONENTS Interpreter Development REQUIRED)
find_package(nanobind CONFIG REQUIRED)

# Core library (optional, for testing C++ directly)
add_library(vrp_solver_core STATIC
    src/solver.cpp
)
target_include_directories(vrp_solver_core PUBLIC include)

# Python extension module
nanobind_add_module(vrp_core
    src/bindings.cpp
    src/solver.cpp
)
target_include_directories(vrp_core PRIVATE include)

# Enable optimizations
if(CMAKE_BUILD_TYPE STREQUAL "Release")
    target_compile_options(vrp_core PRIVATE -O3 -march=native)
endif()
```

**Key Features:**
- C++20 standard enforcement
- Nanobind integration via `nanobind_add_module`
- Separate core library for potential C++ testing
- Release mode optimizations (-O3, -march=native)

### Project Structure

```
cpp-vrp-solver-foundation/
├── CMakeLists.txt
├── include/
│   └── solver.h          # VRPSolver class and data structures
├── src/
│   ├── solver.cpp        # VRPSolver implementation
│   ├── bindings.cpp      # Nanobind bindings
│   └── main.cpp          # Optional C++ entry point
└── tests/
    └── test_solver.py    # Python tests
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Location Value Preservation

*For any* valid latitude and longitude values, creating a Location and reading back its coordinates should return the exact same values that were provided.

**Validates: Requirements 2.1, 2.3**

### Property 2: Customer Value Preservation

*For any* valid customer parameters (id, location, demand, start_window, end_window), creating a Customer and reading back its fields should return the exact same values that were provided.

**Validates: Requirements 2.2, 2.4**

### Property 3: Location Equality Reflexivity

*For any* Location instance, comparing it to itself should return true, and comparing it to a Location with different coordinates should return false.

**Validates: Requirements 2.5**

### Property 4: Distance Matrix Symmetry

*For any* set of customers, the computed distance matrix should be symmetric: the distance from customer i to customer j should equal the distance from customer j to customer i.

**Validates: Requirements 3.1, 3.4**

### Property 5: Distance Matrix Completeness

*For any* set of n customers, the distance matrix should have dimensions n × n, and all entries should be non-negative finite values.

**Validates: Requirements 3.3**

### Property 6: Route Capacity Constraint

*For any* route generated by the solver, the sum of customer demands in that route should not exceed the specified vehicle capacity.

**Validates: Requirements 4.4, 7.4**

### Property 7: Route Time Window Constraint

*For any* route generated by the solver, each customer should be visited within their time window (arrival time ≤ end_window), accounting for travel time and waiting if arriving before start_window.

**Validates: Requirements 4.5, 7.5**

### Property 8: Routes Start at Depot

*For any* route generated by the Nearest Neighbor heuristic, the first customer in the route should be the depot (customer 0).

**Validates: Requirements 5.1**

### Property 9: Greedy Nearest Selection

*For any* step in route construction where a customer is added, that customer should be the nearest unvisited customer (by distance) that satisfies capacity and time window constraints from the current location.

**Validates: Requirements 5.2**

### Property 10: All Customers Visited or Identified as Unserved

*For any* problem instance, the union of all customers in all routes plus any explicitly unserved customers should equal the complete set of input customers (excluding depot).

**Validates: Requirements 4.6**

**Note on Examples vs Properties:**

The following are specific examples that validate integration points and should be tested with unit tests rather than property-based tests:

- **Module Import Test**: Verify `import vrp_core` succeeds (Requirements 1.3, 1.5, 6.6, 7.2)
- **Haversine Known Distance**: Verify Haversine calculation for known coordinates (e.g., NYC to LA) returns expected distance in kilometers (Requirements 3.2)
- **Solve Returns Routes**: Verify solve() returns a list of routes (list of list of ints) (Requirements 4.2)
- **Python Binding Attributes**: Verify Location, Customer, and VRPSolver are accessible from Python with correct attributes (Requirements 6.1, 6.2, 6.3, 6.4, 6.5)
- **Infeasible Problem Handling**: Create a problem where capacity is too small to serve any customer, verify partial solution is returned (Requirements 4.6)

## Error Handling

### Build-Time Errors

**Missing Nanobind:**
- **Condition**: Nanobind not found by CMake
- **Handling**: CMake configuration fails with clear error message
- **User Action**: Install Nanobind via pip or system package manager

**C++20 Not Supported:**
- **Condition**: Compiler doesn't support C++20
- **Handling**: CMake configuration fails with compiler version error
- **User Action**: Upgrade compiler (GCC 10+, Clang 10+, MSVC 19.29+)

### Runtime Errors

**Empty Customer List:**
- **Condition**: solve() called with empty customer vector
- **Handling**: Return empty route list
- **Rationale**: Valid edge case, no work to do

**Invalid Capacity:**
- **Condition**: vehicle_capacity ≤ 0
- **Handling**: Throw `std::invalid_argument` exception
- **Rationale**: Negative or zero capacity is nonsensical

**Invalid Time Windows:**
- **Condition**: Customer with start_window > end_window
- **Handling**: Treat as infeasible customer, exclude from routes
- **Rationale**: Impossible to satisfy, solver should handle gracefully

**Infeasible Problem:**
- **Condition**: No customer can fit in vehicle (demand > capacity)
- **Handling**: Return empty routes or partial solution
- **Rationale**: Solver should not crash, return best effort

**Numerical Issues:**
- **Condition**: Extreme coordinate values causing overflow in Haversine
- **Handling**: Clamp coordinates to valid ranges (lat: [-90, 90], lon: [-180, 180])
- **Rationale**: Prevent undefined behavior from invalid geographic data

### Python Binding Errors

**Type Mismatch:**
- **Condition**: Python code passes wrong types to solve()
- **Handling**: Nanobind raises TypeError with descriptive message
- **Rationale**: Nanobind handles type checking automatically

**Memory Issues:**
- **Condition**: Very large problem instances
- **Handling**: C++ may throw std::bad_alloc, propagated to Python as MemoryError
- **Rationale**: Let Python handle memory errors in standard way

## Testing Strategy

### Dual Testing Approach

This project uses both **unit tests** and **property-based tests** to ensure comprehensive correctness:

- **Unit tests**: Verify specific examples, edge cases, error conditions, and integration points
- **Property tests**: Verify universal properties across all inputs through randomized testing

Both approaches are complementary and necessary. Unit tests catch concrete bugs and validate specific scenarios, while property tests verify general correctness across a wide input space.

### Unit Testing

**Framework**: Python's `pytest` framework

**Test Categories:**

1. **Integration Tests** (Python bindings):
   - Module import succeeds
   - Location, Customer, VRPSolver classes are accessible
   - Attributes are readable/writable from Python
   - solve() accepts correct parameter types

2. **Known Example Tests**:
   - Haversine distance for known city pairs (e.g., NYC to LA ≈ 3936 km)
   - Small problem instances with hand-verified optimal solutions
   - Edge cases: empty customer list, single customer, depot only

3. **Error Condition Tests**:
   - Invalid capacity (≤ 0) raises exception
   - Infeasible problems return partial solutions
   - Invalid time windows are handled gracefully

**Test File**: `tests/test_solver.py`

### Property-Based Testing

**Framework**: Python's `hypothesis` library

**Configuration:**
- Minimum 100 iterations per property test
- Each test tagged with comment referencing design property
- Tag format: `# Feature: cpp-vrp-solver-foundation, Property N: <property text>`

**Property Test Implementation:**

Each correctness property (Properties 1-10) should be implemented as a single property-based test:

```python
from hypothesis import given, strategies as st
import vrp_core

# Feature: cpp-vrp-solver-foundation, Property 1: Location Value Preservation
@given(lat=st.floats(min_value=-90, max_value=90, allow_nan=False),
       lon=st.floats(min_value=-180, max_value=180, allow_nan=False))
def test_location_value_preservation(lat, lon):
    loc = vrp_core.Location(lat, lon)
    assert loc.latitude == lat
    assert loc.longitude == lon
```

**Generator Strategies:**

- **Locations**: Latitude in [-90, 90], longitude in [-180, 180]
- **Customers**: Random IDs, random locations, demand in [0.1, 100], valid time windows
- **Time Windows**: start_window in [0, 24], end_window in [start_window, 48]
- **Capacity**: Positive values in [10, 1000]
- **Problem Instances**: 5-50 customers with varied demands and time windows

**Edge Cases Handled by Generators:**
- Self-distance (same location) → should return 0
- Empty customer lists → should return empty routes
- Single customer → should return one route with depot and customer
- Tight time windows → may result in infeasible customers

### Test Execution

**Running Tests:**

```bash
# Build the project
mkdir build && cd build
cmake ..
make

# Run Python tests
cd ..
python -m pytest tests/ -v

# Run property tests with more iterations
python -m pytest tests/ -v --hypothesis-profile=thorough
```

**Continuous Integration:**
- All tests must pass before merging
- Property tests run with default 100 iterations in CI
- Developers can run with more iterations locally for thorough validation

### Coverage Goals

- **Unit Test Coverage**: All public API methods, all error conditions
- **Property Test Coverage**: All 10 correctness properties implemented
- **Integration Coverage**: All Python bindings validated

### Future Testing Enhancements

- **Performance Benchmarks**: Track solve() time for standard problem sizes
- **Comparison Tests**: Compare Nearest Neighbor results with optimal solutions for small instances
- **Stress Tests**: Large problem instances (1000+ customers) to validate scalability
- **Memory Profiling**: Verify no memory leaks in Python-C++ boundary
