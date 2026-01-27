# Design Document: Time Window Constraint Enforcement

## Overview

This design document describes the implementation of time window constraint enforcement in the VRP solver using a matrix-based approach for travel times. The system will accept a pre-computed travel time matrix from the frontend, enabling integration with real-world routing services (OSRM, Valhalla, Google Maps) while maintaining backward compatibility with the existing Haversine-based distance calculation.

The implementation involves three main components:
1. **C++ Core**: Add service_time field to Customer struct, modify solve() to accept time_matrix, update constraint validation
2. **Python Bindings**: Expose service_time field and time_matrix parameter to Python
3. **Dashboard**: Generate travel time matrix and display arrival/waiting times

## Architecture

### High-Level Data Flow

```
Dashboard (Python)
    ↓
1. Generate Travel Time Matrix (Haversine / 40 km/h in Phase 1)
    ↓
2. Pass customers + time_matrix to solver
    ↓
VRPSolver (C++)
    ↓
3. Use time_matrix for travel time lookups
    ↓
4. Enforce time windows during route construction
    ↓
5. Return routes with timing information
    ↓
Dashboard (Python)
    ↓
6. Display routes with arrival times and waiting times
```

### Component Interaction

```
┌─────────────────────────────────────────────────────────────┐
│                        Dashboard (Python)                    │
│  - Generate time_matrix from Haversine distances            │
│  - Call solver.solve(customers, capacity, time_matrix)      │
│  - Display arrival times and waiting times                  │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Python Bindings (Nanobind)               │
│  - Convert Python list/numpy array to vector<vector<double>>│
│  - Validate time_matrix dimensions                          │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      VRPSolver (C++)                        │
│  - Store time_matrix as member variable                     │
│  - Use time_matrix[i][j] for travel time lookups           │
│  - Track current_time during route construction            │
│  - Validate time windows in canAddToRoute()                │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. Customer Struct Extension

**File**: `include/solver.h`

Add `service_time` field to the Customer struct:

```cpp
struct Customer {
    int id;
    Location location;
    double demand;
    double start_window;
    double end_window;
    double service_time;  // NEW: Service duration in minutes
    
    // Updated constructor with service_time (default = 0)
    Customer(int id, Location loc, double demand, 
             double start_w, double end_w, double service_t = 0.0);
};
```

**Design Rationale**:
- Default value of 0.0 maintains backward compatibility
- Placed at end of struct to minimize memory layout changes
- Type is `double` to match other time-related fields

### 2. VRPSolver Interface Changes

**File**: `include/solver.h`

Update the `solve()` method signature:

```cpp
class VRPSolver {
public:
    // Updated solve() method with optional time_matrix
    std::vector<Route> solve(
        const std::vector<Customer>& customers,
        double vehicle_capacity,
        bool use_simd = true,
        const std::vector<std::vector<double>>& time_matrix = {}
    );
    
private:
    std::vector<std::vector<double>> distance_matrix_;
    std::vector<std::vector<double>> time_matrix_;  // NEW: Travel time matrix
    bool use_time_matrix_;  // NEW: Flag to indicate if time_matrix is provided
    
    // Updated method signatures
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
    
    // NEW: Helper method to get travel time between two customers
    double getTravelTime(int from_idx, int to_idx) const;
};
```

**Design Rationale**:
- `time_matrix` parameter is optional (empty vector by default) for backward compatibility
- `use_time_matrix_` flag avoids checking if vector is empty repeatedly
- `getTravelTime()` encapsulates the logic of choosing between time_matrix and distance_matrix

### 3. Travel Time Lookup Logic

**File**: `src/solver.cpp`

Implement `getTravelTime()` method:

```cpp
double VRPSolver::getTravelTime(int from_idx, int to_idx) const {
    if (use_time_matrix_) {
        // Use provided time matrix (already in minutes)
        return time_matrix_[from_idx][to_idx];
    } else {
        // Fallback: Use distance matrix (in km)
        // Assume 40 km/h = 0.666... km/min
        // travel_time = distance / speed = distance / (40/60) = distance * 1.5
        return distance_matrix_[from_idx][to_idx] * 1.5;
    }
}
```

**Design Rationale**:
- Centralized logic for travel time calculation
- Clear separation between time_matrix mode and fallback mode
- Fallback uses 40 km/h as specified in requirements (distance * 1.5 = distance / (40/60))

### 4. Time Window Validation in canAddToRoute()

**File**: `src/solver.cpp`

Update `canAddToRoute()` to enforce time windows:

```cpp
bool VRPSolver::canAddToRoute(
    const Route& route,
    int customer_idx,
    const std::vector<Customer>& customers,
    double vehicle_capacity,
    double current_time
) {
    // Validate customer index
    if (customer_idx < 0 || customer_idx >= static_cast<int>(customers.size())) {
        return false;
    }
    
    const Customer& customer = customers[customer_idx];
    
    // Check capacity constraint
    double route_load = calculateRouteLoad(route, customers);
    if (route_load + customer.demand > vehicle_capacity) {
        return false;
    }
    
    // Check time window constraint
    int current_location = route.empty() ? 0 : route.back();
    double travel_time = getTravelTime(current_location, customer_idx);
    double arrival_time = current_time + travel_time;
    
    // Reject if arriving after end_window
    if (arrival_time > customer.end_window) {
        return false;
    }
    
    // All constraints satisfied
    return true;
}
```

**Design Rationale**:
- Time window check added after capacity check (fail fast on capacity)
- Uses `getTravelTime()` for consistent travel time calculation
- Allows early arrival (waiting is handled in route construction)

### 5. Time Tracking in nearestNeighborHeuristic()

**File**: `src/solver.cpp`

Update route construction to track time:

```cpp
std::vector<Route> VRPSolver::nearestNeighborHeuristic(
    const std::vector<Customer>& customers,
    double vehicle_capacity
) {
    size_t n = customers.size();
    std::vector<bool> visited(n, false);
    visited[0] = true;  // depot
    
    std::vector<Route> routes;
    
    auto countUnvisited = [&visited]() {
        int count = 0;
        for (size_t i = 1; i < visited.size(); ++i) {
            if (!visited[i]) count++;
        }
        return count;
    };
    
    while (countUnvisited() > 0) {
        Route current_route;
        current_route.push_back(0);  // Start at depot
        
        double current_load = 0.0;
        double current_time = 0.0;  // NEW: Track time
        int current_location = 0;
        
        while (true) {
            int best_customer = -1;
            double best_distance = std::numeric_limits<double>::infinity();
            
            // Find nearest feasible customer
            for (size_t i = 1; i < n; ++i) {
                if (!visited[i]) {
                    if (canAddToRoute(current_route, i, customers, 
                                     vehicle_capacity, current_time)) {
                        double distance = distance_matrix_[current_location][i];
                        if (distance < best_distance) {
                            best_distance = distance;
                            best_customer = i;
                        }
                    }
                }
            }
            
            if (best_customer == -1) {
                break;  // No feasible customer
            }
            
            // Add customer to route
            current_route.push_back(best_customer);
            visited[best_customer] = true;
            
            const Customer& customer = customers[best_customer];
            current_load += customer.demand;
            
            // NEW: Update time tracking
            double travel_time = getTravelTime(current_location, best_customer);
            double arrival_time = current_time + travel_time;
            double waiting_time = std::max(0.0, customer.start_window - arrival_time);
            current_time = arrival_time + waiting_time + customer.service_time;
            
            current_location = best_customer;
        }
        
        if (current_route.size() == 1) {
            break;  // Cannot serve remaining customers
        }
        
        current_route.push_back(0);  // Return to depot
        routes.push_back(current_route);
    }
    
    return routes;
}
```

**Design Rationale**:
- `current_time` tracks cumulative time for the vehicle
- Waiting time calculated as `max(0, start_window - arrival_time)`
- Time updated as: `arrival_time + waiting_time + service_time`
- This represents the departure time from the customer

### 6. solve() Method Updates

**File**: `src/solver.cpp`

Update `solve()` to handle time_matrix:

```cpp
std::vector<Route> VRPSolver::solve(
    const std::vector<Customer>& customers,
    double vehicle_capacity,
    bool use_simd,
    const std::vector<std::vector<double>>& time_matrix
) {
    // Validate inputs
    if (vehicle_capacity <= 0) {
        throw std::invalid_argument("Vehicle capacity must be positive");
    }
    
    if (customers.empty() || customers.size() == 1) {
        return std::vector<Route>();
    }
    
    // Store time matrix and set flag
    if (!time_matrix.empty()) {
        // Validate dimensions
        size_t n = customers.size();
        if (time_matrix.size() != n) {
            throw std::invalid_argument(
                "Time matrix dimensions must match number of customers");
        }
        for (size_t i = 0; i < n; ++i) {
            if (time_matrix[i].size() != n) {
                throw std::invalid_argument(
                    "Time matrix must be square (N×N)");
            }
        }
        
        time_matrix_ = time_matrix;
        use_time_matrix_ = true;
    } else {
        use_time_matrix_ = false;
    }
    
    // Build distance matrix (still needed for nearest neighbor selection)
    buildDistanceMatrix(customers, use_simd);
    
    // Call nearest neighbor heuristic
    return nearestNeighborHeuristic(customers, vehicle_capacity);
}
```

**Design Rationale**:
- Validates time_matrix dimensions before use
- Still builds distance_matrix for nearest neighbor selection (spatial proximity)
- Sets `use_time_matrix_` flag for getTravelTime() logic

## Data Models

### Customer Data Model

```cpp
struct Customer {
    int id;                  // Unique identifier (0 = depot)
    Location location;       // Geographic coordinates
    double demand;           // Delivery demand (units)
    double start_window;     // Earliest service time (minutes from start)
    double end_window;       // Latest service time (minutes from start)
    double service_time;     // Service duration (minutes)
};
```

### Time Matrix Data Model

```cpp
// N×N matrix where time_matrix[i][j] = travel time from customer i to j
std::vector<std::vector<double>> time_matrix;

// Example for 3 customers (depot + 2 customers):
// time_matrix[0][1] = 15.5  // Depot to Customer 1: 15.5 minutes
// time_matrix[1][2] = 8.2   // Customer 1 to Customer 2: 8.2 minutes
// time_matrix[2][0] = 12.0  // Customer 2 to Depot: 12.0 minutes
```

### Route Timing Information

During route construction, the solver tracks:

```cpp
struct RouteState {
    double current_time;      // Cumulative time (minutes from start)
    double current_load;      // Cumulative load (units)
    int current_location;     // Current customer ID
};

// For each customer visit:
double arrival_time = current_time + travel_time;
double waiting_time = max(0.0, start_window - arrival_time);
double departure_time = arrival_time + waiting_time + service_time;
current_time = departure_time;
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*


### Property 1: Time Matrix Usage

*For any* valid time matrix and customer pair (i, j), when the solver calculates travel time from customer i to customer j, the returned value should equal time_matrix[i][j].

**Validates: Requirements 2.2, 2.3**

### Property 2: Late Arrival Rejection

*For any* customer with time window [start_window, end_window], if arrival_time > end_window, then the solver should reject adding that customer to the route.

**Validates: Requirements 3.2**

### Property 3: Early Arrival Waiting

*For any* customer where arrival_time < start_window, when the customer is added to a route, the waiting_time should equal (start_window - arrival_time) and the departure time should be (start_window + service_time).

**Validates: Requirements 3.3, 4.2**

### Property 4: On-Time Arrival No Waiting

*For any* customer where start_window ≤ arrival_time ≤ end_window, when the customer is added to a route, the waiting_time should be 0 and the departure time should be (arrival_time + service_time).

**Validates: Requirements 3.4, 4.2**

### Property 5: Time Progression Consistency

*For any* sequence of customers in a route, the arrival_time at customer N+1 should equal the departure_time from customer N plus the travel time from N to N+1.

**Validates: Requirements 4.3, 4.5**

### Property 6: Matrix Dimension Validation

*For any* time matrix provided to the solver, if the matrix dimensions do not match N×N (where N is the number of customers), the solver should reject the matrix with an error.

**Validates: Requirements 2.5, 7.4**

### Property 7: Service Time Default

*For any* Customer object created without specifying service_time, the service_time field should equal 0.

**Validates: Requirements 1.3**

### Property 8: Dashboard Time Matrix Calculation

*For any* pair of customers with Haversine distance D kilometers, the Dashboard-generated time matrix entry should equal D / (40/60) = D * 1.5 minutes.

**Validates: Requirements 5.2**

### Property 9: Backward Compatibility

*For any* valid customer list and capacity, calling solve() without a time_matrix parameter should produce valid routes using the Haversine-based fallback.

**Validates: Requirements 2.4, 7.2, 7.3**

## Error Handling

### Input Validation Errors

1. **Invalid Vehicle Capacity**
   - Condition: `vehicle_capacity <= 0`
   - Action: Throw `std::invalid_argument` with message "Vehicle capacity must be positive"

2. **Empty Customer List**
   - Condition: `customers.empty() || customers.size() == 1`
   - Action: Return empty route vector (no error)

3. **Invalid Time Matrix Dimensions**
   - Condition: `time_matrix.size() != customers.size()` or any row size mismatch
   - Action: Throw `std::invalid_argument` with message "Time matrix dimensions must match number of customers"

4. **Non-Square Time Matrix**
   - Condition: `time_matrix[i].size() != customers.size()` for any row i
   - Action: Throw `std::invalid_argument` with message "Time matrix must be square (N×N)"

### Runtime Errors

1. **Invalid Customer Index**
   - Condition: Customer index out of bounds in `canAddToRoute()`
   - Action: Return `false` (reject customer)

2. **No Feasible Routes**
   - Condition: No customers can be added to any route due to constraints
   - Action: Return partial solution (routes constructed so far)

### Python Binding Errors

1. **Type Conversion Failure**
   - Condition: Python time_matrix cannot be converted to `vector<vector<double>>`
   - Action: Nanobind throws `TypeError` automatically

2. **Missing Required Parameters**
   - Condition: Required parameters (customers, capacity) not provided
   - Action: Nanobind throws `TypeError` automatically

## Testing Strategy

This feature will be tested using a dual approach combining unit tests and property-based tests.

### Unit Testing

Unit tests will focus on specific examples, edge cases, and integration points:

**C++ Unit Tests**:
- Test Customer constructor with and without service_time parameter
- Test solve() with valid time_matrix
- Test solve() without time_matrix (backward compatibility)
- Test time window validation with specific scenarios (early, on-time, late)
- Test matrix dimension validation with invalid matrices
- Test getTravelTime() with both time_matrix and fallback modes

**Python Unit Tests**:
- Test Python bindings expose service_time field
- Test solve() accepts time_matrix as named argument
- Test time_matrix parameter is optional
- Test type conversion from Python list to C++ vector
- Test Dashboard generates time_matrix correctly
- Test Dashboard displays arrival times and waiting times

### Property-Based Testing

Property tests will verify universal properties across randomized inputs using Hypothesis (Python):

**Configuration**:
- Minimum 100 iterations per property test
- Each test tagged with: **Feature: time-window-enforcement, Property N: [property text]**

**Property Tests**:

1. **Property 1: Time Matrix Usage**
   - Generate: Random time matrices and customer pairs
   - Verify: getTravelTime(i, j) == time_matrix[i][j]
   - Tag: **Feature: time-window-enforcement, Property 1: Time Matrix Usage**

2. **Property 2: Late Arrival Rejection**
   - Generate: Random customers with arrival_time > end_window
   - Verify: canAddToRoute() returns false
   - Tag: **Feature: time-window-enforcement, Property 2: Late Arrival Rejection**

3. **Property 3: Early Arrival Waiting**
   - Generate: Random customers with arrival_time < start_window
   - Verify: Waiting time and departure time calculated correctly
   - Tag: **Feature: time-window-enforcement, Property 3: Early Arrival Waiting**

4. **Property 4: On-Time Arrival No Waiting**
   - Generate: Random customers with start_window ≤ arrival_time ≤ end_window
   - Verify: No waiting time, correct departure time
   - Tag: **Feature: time-window-enforcement, Property 4: On-Time Arrival No Waiting**

5. **Property 5: Time Progression Consistency**
   - Generate: Random routes with multiple customers
   - Verify: Arrival times follow time progression formula
   - Tag: **Feature: time-window-enforcement, Property 5: Time Progression Consistency**

6. **Property 6: Matrix Dimension Validation**
   - Generate: Random matrices with incorrect dimensions
   - Verify: Solver rejects with appropriate error
   - Tag: **Feature: time-window-enforcement, Property 6: Matrix Dimension Validation**

7. **Property 7: Service Time Default**
   - Generate: Random customers without service_time
   - Verify: service_time == 0
   - Tag: **Feature: time-window-enforcement, Property 7: Service Time Default**

8. **Property 8: Dashboard Time Matrix Calculation**
   - Generate: Random customer locations
   - Verify: time_matrix[i][j] == haversine_distance(i, j) * 1.5
   - Tag: **Feature: time-window-enforcement, Property 8: Dashboard Time Matrix Calculation**

9. **Property 9: Backward Compatibility**
   - Generate: Random customer lists
   - Verify: solve() without time_matrix produces valid routes
   - Tag: **Feature: time-window-enforcement, Property 9: Backward Compatibility**

### Integration Testing

- Test end-to-end flow: Dashboard → Solver → Results
- Test with real-world-like scenarios (Mumbai delivery routes)
- Test with edge cases (tight time windows, long service times)
- Verify Dashboard displays match solver output

### Performance Testing

- Benchmark solve() with and without time_matrix
- Verify no performance regression in fallback mode
- Test with large customer counts (100+, 500+, 1000+)

## Implementation Notes

### Phase 1: MVP Implementation

1. Add service_time field to Customer struct
2. Update solve() to accept time_matrix parameter
3. Implement getTravelTime() with fallback logic
4. Update canAddToRoute() for time window validation
5. Update nearestNeighborHeuristic() for time tracking
6. Update Python bindings to expose new parameters
7. Update Dashboard to generate time_matrix using Haversine / 40 km/h
8. Update Dashboard to display arrival times and waiting times

### Phase 2: Real Routing Integration (Future)

1. Add OSRM/Valhalla API integration to Dashboard
2. Replace Haversine-based time_matrix generation with API calls
3. Add caching layer for time_matrix to avoid repeated API calls
4. Add configuration for choosing routing service
5. No C++ code changes required (architecture is extensible)

### Backward Compatibility Considerations

- Existing code calling solve(customers, capacity) continues to work
- Existing Customer constructor calls work (service_time defaults to 0)
- Existing tests pass without modification
- New functionality is opt-in via time_matrix parameter

### Memory Considerations

- Time matrix is N×N doubles = 8N² bytes
- For 100 customers: ~80 KB
- For 500 customers: ~2 MB
- For 1000 customers: ~8 MB
- Acceptable for in-memory storage

### Performance Considerations

- getTravelTime() is O(1) lookup (no computation)
- Time window validation adds minimal overhead to canAddToRoute()
- Overall algorithm complexity remains O(N²) for Nearest Neighbor
- SIMD optimizations still apply to distance_matrix construction
