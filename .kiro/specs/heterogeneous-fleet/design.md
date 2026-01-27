# Design Document: Heterogeneous Fleet

## Overview

This design extends the VRP Solver to support heterogeneous fleets where vehicles have different capacity constraints. The current implementation assumes all vehicles are identical (homogeneous fleet), which limits real-world applicability. This feature enables users to define a mixed fleet (e.g., 2 Trucks at 50 capacity, 2 Vans at 20 capacity, 1 Bike at 10 capacity) and have the solver generate routes that respect each vehicle's individual capacity.

The key architectural change is replacing the scalar `vehicle_capacity` and `num_vehicles` parameters with a vector of capacities `std::vector<double> vehicle_capacities`, where each element represents a specific vehicle's capacity. The solver will assign routes to vehicles in order, using larger vehicles first (by sorting capacities in descending order) to optimize fleet utilization.

## Architecture

### Current Architecture (Homogeneous Fleet)

```
Dashboard (Python)
    ↓ (capacity: double, num_vehicles: int)
Python Bindings (Nanobind)
    ↓ (capacity: double)
VRPSolver::solve()
    ↓ (creates num_vehicles routes, all with same capacity)
nearestNeighborHeuristic()
```

### New Architecture (Heterogeneous Fleet)

```
Dashboard (Python)
    ↓ Fleet Configuration UI
    ↓ (vehicle_profiles: List[{name, capacity, quantity}])
    ↓ Flatten & Sort (descending by capacity)
    ↓ (vehicle_capacities: List[double])
Python Bindings (Nanobind)
    ↓ (vehicle_capacities: std::vector<double>)
VRPSolver::solve()
    ↓ (creates len(vehicle_capacities) routes, each with specific capacity)
nearestNeighborHeuristic()
    ↓ (uses vehicle_capacities[route_index] for each route)
```

### Key Architectural Decisions

1. **Capacity Vector Ordering**: The Dashboard sorts vehicle capacities in descending order before passing to the solver. This ensures larger vehicles are used first, maximizing load efficiency and minimizing the number of routes needed.

2. **No Backward Compatibility**: The old `solve(capacity, num_vehicles)` signature will be completely replaced. This simplifies the implementation and avoids maintaining two code paths.

3. **Vehicle Mapping in Dashboard**: The Dashboard maintains a mapping from route index to vehicle profile (name, capacity, instance number) for visualization purposes. The C++ solver only works with capacity values.

4. **Unassigned Customers**: If all vehicles are exhausted and customers remain, the solver stops and returns the partial solution. The Dashboard can display unassigned customers as a warning.

## Components and Interfaces

### Component 1: Fleet Configuration UI (Dashboard)

**Location**: `dashboard/app.py`

**Responsibilities**:
- Provide UI for adding/removing vehicle profiles
- Validate input (positive capacities and quantities)
- Flatten profiles into capacity list
- Sort capacities in descending order
- Maintain vehicle mapping for visualization

**Interface**:

```python
# Input: User-defined vehicle profiles
vehicle_profiles = [
    {"name": "Truck", "capacity": 50.0, "quantity": 2},
    {"name": "Van", "capacity": 20.0, "quantity": 2},
    {"name": "Bike", "capacity": 10.0, "quantity": 1}
]

# Output: Sorted capacity list
vehicle_capacities = [50.0, 50.0, 20.0, 20.0, 10.0]

# Output: Vehicle mapping for visualization
vehicle_map = [
    {"name": "Truck", "instance": 1, "capacity": 50.0},
    {"name": "Truck", "instance": 2, "capacity": 50.0},
    {"name": "Van", "instance": 1, "capacity": 20.0},
    {"name": "Van", "instance": 2, "capacity": 20.0},
    {"name": "Bike", "instance": 1, "capacity": 10.0}
]
```

**Algorithm**:

```python
def flatten_and_sort_fleet(vehicle_profiles):
    """
    Convert vehicle profiles to sorted capacity list and vehicle map
    
    Args:
        vehicle_profiles: List of dicts with keys: name, capacity, quantity
    
    Returns:
        Tuple of (vehicle_capacities, vehicle_map)
    """
    # Step 1: Flatten profiles into list of (name, capacity) tuples
    vehicles = []
    for profile in vehicle_profiles:
        for i in range(profile["quantity"]):
            vehicles.append({
                "name": profile["name"],
                "capacity": profile["capacity"],
                "instance": i + 1
            })
    
    # Step 2: Sort by capacity (descending)
    vehicles.sort(key=lambda v: v["capacity"], reverse=True)
    
    # Step 3: Extract capacity list
    vehicle_capacities = [v["capacity"] for v in vehicles]
    
    # Step 4: Create vehicle map
    vehicle_map = vehicles
    
    return vehicle_capacities, vehicle_map
```

### Component 2: VRPSolver Core (C++)

**Location**: `include/solver.h`, `src/solver.cpp`

**Responsibilities**:
- Accept vector of vehicle capacities
- Generate routes respecting individual vehicle capacities
- Stop when all vehicles are assigned or no more customers can be served

**Interface Changes**:

```cpp
// OLD SIGNATURE (to be removed)
std::vector<Route> solve(
    const std::vector<Customer>& customers,
    double vehicle_capacity,  // Single capacity for all vehicles
    bool use_simd = true,
    const std::vector<std::vector<double>>& time_matrix = {}
);

// NEW SIGNATURE
std::vector<Route> solve(
    const std::vector<Customer>& customers,
    const std::vector<double>& vehicle_capacities,  // Individual capacities
    bool use_simd = true,
    const std::vector<std::vector<double>>& time_matrix = {}
);
```

**Algorithm Changes**:

The `nearestNeighborHeuristic` method needs to be updated to accept and use the capacity vector:

```cpp
std::vector<Route> nearestNeighborHeuristic(
    const std::vector<Customer>& customers,
    const std::vector<double>& vehicle_capacities  // Changed from single double
) {
    size_t n = customers.size();
    size_t num_vehicles = vehicle_capacities.size();
    
    // Initialize visited array
    std::vector<bool> visited(n, false);
    visited[0] = true;  // depot
    
    std::vector<Route> routes;
    
    // Create routes up to num_vehicles
    for (size_t vehicle_idx = 0; vehicle_idx < num_vehicles; ++vehicle_idx) {
        // Check if any unvisited customers remain
        if (countUnvisited(visited) == 0) {
            break;  // All customers served
        }
        
        // Get capacity for this specific vehicle
        double current_vehicle_capacity = vehicle_capacities[vehicle_idx];
        
        // Start new route at depot
        Route current_route;
        current_route.push_back(0);
        
        double current_load = 0.0;
        double current_time = 0.0;
        int current_location = 0;
        
        // Greedily add nearest feasible customer
        while (true) {
            int best_customer = -1;
            double best_distance = std::numeric_limits<double>::infinity();
            
            // Find nearest unvisited customer that satisfies constraints
            for (size_t i = 1; i < n; ++i) {
                if (!visited[i]) {
                    // Use current_vehicle_capacity instead of global capacity
                    if (canAddToRoute(current_route, i, customers, 
                                     current_vehicle_capacity, current_time)) {
                        double distance = distance_matrix_[current_location][i];
                        if (distance < best_distance) {
                            best_distance = distance;
                            best_customer = i;
                        }
                    }
                }
            }
            
            // No feasible customer found
            if (best_customer == -1) {
                break;
            }
            
            // Add customer to route
            current_route.push_back(best_customer);
            visited[best_customer] = true;
            
            // Update state
            const Customer& customer = customers[best_customer];
            current_load += customer.demand;
            double travel_time = getTravelTime(current_location, best_customer);
            double arrival_time = current_time + travel_time;
            double waiting_time = std::max(0.0, customer.start_window - arrival_time);
            current_time = arrival_time + waiting_time + customer.service_time;
            current_location = best_customer;
        }
        
        // If route only contains depot, no customers could be added
        if (current_route.size() == 1) {
            break;  // Stop creating routes
        }
        
        // Return to depot
        current_route.push_back(0);
        routes.push_back(current_route);
    }
    
    return routes;
}
```

### Component 3: Python Bindings (Nanobind)

**Location**: `src/bindings.cpp`

**Responsibilities**:
- Expose new `solve` signature to Python
- Convert Python list to C++ `std::vector<double>`

**Interface Changes**:

```cpp
nb::class_<VRPSolver>(m, "VRPSolver")
    .def(nb::init<>())
    .def("solve", &VRPSolver::solve,
         nb::arg("customers"),
         nb::arg("vehicle_capacities"),  // Changed from vehicle_capacity
         nb::arg("use_simd") = true,
         nb::arg("time_matrix") = std::vector<std::vector<double>>(),
         "Solve VRP with heterogeneous fleet");
```

Nanobind automatically handles conversion from Python `list[float]` to C++ `std::vector<double>`, so no additional conversion code is needed.

### Component 4: Route Visualization (Dashboard)

**Location**: `dashboard/app.py`

**Responsibilities**:
- Display vehicle assignment for each route
- Show vehicle name, instance number, and capacity
- Calculate and display fleet utilization

**Interface**:

```python
def display_route_with_vehicle(route_idx, route, vehicle_map):
    """
    Display route with vehicle assignment
    
    Args:
        route_idx: Index of route (0, 1, 2, ...)
        route: List of customer IDs
        vehicle_map: List of vehicle info dicts
    
    Returns:
        Formatted string like "Route 1 (Truck #1 - Cap 50)"
    """
    vehicle = vehicle_map[route_idx]
    return f"Route {route_idx + 1} ({vehicle['name']} #{vehicle['instance']} - Cap {vehicle['capacity']})"
```

## Data Models

### Vehicle Profile (Python)

```python
@dataclass
class VehicleProfile:
    name: str          # e.g., "Truck", "Van", "Bike"
    capacity: float    # e.g., 50.0, 20.0, 10.0
    quantity: int      # e.g., 2, 2, 1
```

### Vehicle Map Entry (Python)

```python
@dataclass
class VehicleMapEntry:
    name: str          # e.g., "Truck"
    instance: int      # e.g., 1, 2 (for multiple vehicles of same type)
    capacity: float    # e.g., 50.0
```

### No C++ Data Model Changes

The C++ solver only works with `std::vector<double>` for capacities. No new C++ data structures are needed.

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*


### Property 1: Fleet Configuration Input Validation

*For any* vehicle profile with capacity and quantity values, the system should accept the profile if and only if capacity is a positive number and quantity is a positive integer.

**Validates: Requirements 1.2, 1.3**

### Property 2: Fleet Size Calculation

*For any* list of vehicle profiles, the total fleet size should equal the sum of all vehicle quantities.

**Validates: Requirements 1.4**

### Property 3: Fleet Flattening Correctness

*For any* list of vehicle profiles, the flattened capacity list should have length equal to the sum of quantities, and should contain each vehicle's capacity repeated by its quantity.

**Validates: Requirements 1.5**

### Property 4: Capacity List Sorting

*For any* capacity list, after sorting in descending order, each element should be greater than or equal to the next element (monotonically non-increasing).

**Validates: Requirements 1.6**

### Property 5: Route Capacity Constraint

*For any* route i generated by the solver, the total demand of customers in that route should not exceed vehicle_capacities[i].

**Validates: Requirements 2.2, 2.3**

### Property 6: Maximum Routes Constraint

*For any* solver execution with N vehicles, the number of routes generated should be at most N.

**Validates: Requirements 2.4**

### Property 7: Unassigned Customer Tracking

*For any* problem instance where total customer demand exceeds total fleet capacity, the solver should identify and track customers that could not be assigned to any route.

**Validates: Requirements 2.5**

### Property 8: Python to C++ Data Flow

*For any* list of vehicle capacities passed from Python, the C++ solver should receive and use the exact same capacity values in the same order.

**Validates: Requirements 3.2, 3.4**

### Property 9: Vehicle Assignment Display

*For any* route, the rendered output should include the vehicle name, instance number, and capacity.

**Validates: Requirements 4.1, 4.2**

### Property 10: Vehicle Instance Uniqueness

*For any* set of vehicles where multiple vehicles share the same type name, each vehicle should have a unique instance number within that type.

**Validates: Requirements 4.3**

### Property 11: Route-to-Vehicle Mapping

*For any* route index i, the vehicle mapping should return the vehicle information corresponding to the i-th element in the sorted capacity list.

**Validates: Requirements 4.4**

### Property 12: Fleet Utilization Calculation

*For any* set of routes, the fleet utilization percentage should equal (total demand served / total fleet capacity) × 100.

**Validates: Requirements 4.5**

### Property 13: Complete Route Information

*For any* solver execution, the Dashboard should receive both the route sequences and the vehicle assignments for all routes.

**Validates: Requirements 5.2, 5.4**

## Error Handling

### Input Validation Errors

**Error**: Invalid vehicle profile (negative capacity or quantity)
**Handling**: Dashboard displays error message and prevents solver invocation
**User Action**: Correct the vehicle profile values

**Error**: Empty fleet configuration (no vehicles defined)
**Handling**: Dashboard displays warning and uses default single vehicle
**User Action**: Define at least one vehicle profile

### Solver Errors

**Error**: Insufficient fleet capacity (customers remain unassigned)
**Handling**: Solver returns partial solution with unassigned customer list
**Dashboard Action**: Display warning with count of unassigned customers
**User Action**: Add more vehicles or increase vehicle capacities

**Error**: Invalid capacity vector (empty or contains non-positive values)
**Handling**: C++ solver throws `std::invalid_argument` exception
**Python Handling**: Catch exception and display error message
**User Action**: Fix fleet configuration

### Binding Errors

**Error**: Type conversion failure (non-numeric values in capacity list)
**Handling**: Nanobind throws type error
**Python Handling**: Catch exception and display error message
**User Action**: Ensure all capacities are numeric

## Testing Strategy

### Dual Testing Approach

This feature requires both unit tests and property-based tests:

- **Unit tests**: Verify specific examples, edge cases, and error conditions
- **Property tests**: Verify universal properties across all inputs
- Both are complementary and necessary for comprehensive coverage

### Unit Testing Focus

Unit tests should focus on:
- Specific examples demonstrating correct behavior (e.g., 2 trucks + 1 van scenario)
- Edge cases (empty fleet, single vehicle, all vehicles same capacity)
- Error conditions (negative capacity, zero quantity, insufficient capacity)
- Integration between Dashboard and solver

### Property-Based Testing Focus

Property tests should focus on:
- Universal properties that hold for all inputs
- Comprehensive input coverage through randomization
- Invariants that must be maintained (capacity constraints, sorting order)

### Property Test Configuration

- **Library**: Hypothesis (Python property-based testing library)
- **Minimum iterations**: 100 per property test
- **Test tagging**: Each property test must reference its design document property
- **Tag format**: `# Feature: heterogeneous-fleet, Property {number}: {property_text}`

### Test Coverage Requirements

Each correctness property must be implemented by a single property-based test:

1. **Property 1** (Input Validation): Generate random vehicle profiles with valid and invalid values, verify validation logic
2. **Property 2** (Fleet Size): Generate random profiles, verify sum of quantities
3. **Property 3** (Flattening): Generate random profiles, verify flattened list correctness
4. **Property 4** (Sorting): Generate random capacity lists, verify descending order
5. **Property 5** (Capacity Constraint): Generate random problems, verify no route exceeds its vehicle capacity
6. **Property 6** (Max Routes): Generate random problems with N vehicles, verify at most N routes
7. **Property 7** (Unassigned Tracking): Generate problems with insufficient capacity, verify unassigned customers tracked
8. **Property 8** (Data Flow): Generate random capacity lists, verify Python→C++ transfer
9. **Property 9** (Display): Generate random routes, verify vehicle info in output
10. **Property 10** (Uniqueness): Generate fleets with duplicate types, verify unique instance numbers
11. **Property 11** (Mapping): Generate random fleets, verify route index maps to correct vehicle
12. **Property 12** (Utilization): Generate random routes, verify utilization calculation
13. **Property 13** (Complete Info): Generate random problems, verify Dashboard receives all data

### Example Property Test

```python
from hypothesis import given, strategies as st
import vrp_core

# Feature: heterogeneous-fleet, Property 5: Route Capacity Constraint
@given(
    vehicle_capacities=st.lists(
        st.floats(min_value=1.0, max_value=100.0),
        min_size=1,
        max_size=10
    ),
    customers=st.lists(
        st.tuples(
            st.floats(min_value=0.0, max_value=50.0),  # demand
            st.floats(min_value=19.0, max_value=19.1),  # lat
            st.floats(min_value=72.0, max_value=72.1)   # lon
        ),
        min_size=1,
        max_size=20
    )
)
def test_route_capacity_constraint(vehicle_capacities, customers):
    """
    Property: For any route i, total demand ≤ vehicle_capacities[i]
    """
    # Convert to Customer objects
    customer_objs = [
        vrp_core.Customer(
            0, vrp_core.Location(19.065, 72.835), 0.0, 0.0, 600.0, 0.0
        )  # depot
    ]
    for i, (demand, lat, lon) in enumerate(customers, start=1):
        customer_objs.append(
            vrp_core.Customer(
                i, vrp_core.Location(lat, lon), demand, 0.0, 600.0, 10.0
            )
        )
    
    # Solve
    solver = vrp_core.VRPSolver()
    routes = solver.solve(customer_objs, vehicle_capacities)
    
    # Verify property
    for route_idx, route in enumerate(routes):
        total_demand = sum(
            customer_objs[cust_id].demand 
            for cust_id in route 
            if cust_id != 0  # exclude depot
        )
        assert total_demand <= vehicle_capacities[route_idx], \
            f"Route {route_idx} demand {total_demand} exceeds capacity {vehicle_capacities[route_idx]}"
```

## Implementation Notes

### Migration Path

1. **Phase 1**: Update C++ solver signature and implementation
2. **Phase 2**: Update Python bindings
3. **Phase 3**: Update Dashboard UI and logic
4. **Phase 4**: Update tests and documentation

### Performance Considerations

- Sorting the capacity list is O(N log N) where N is the number of vehicles, which is negligible for typical fleet sizes (< 100 vehicles)
- The solver's time complexity remains unchanged: O(V × C²) where V is the number of vehicles and C is the number of customers
- No additional memory overhead beyond storing the capacity vector

### Future Enhancements

This design provides a foundation for future heterogeneous fleet features:

- **Vehicle-specific costs**: Different fuel consumption rates per vehicle type
- **Vehicle-specific speeds**: Different travel times based on vehicle type
- **Vehicle-specific time windows**: Some vehicles only available during certain hours
- **Vehicle-customer compatibility**: Some customers can only be served by certain vehicle types
