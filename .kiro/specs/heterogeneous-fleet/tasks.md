# Implementation Plan: Heterogeneous Fleet

## Overview

This implementation plan converts the heterogeneous fleet design into discrete coding tasks. The approach follows a bottom-up strategy: first updating the C++ core solver, then the Python bindings, and finally the Dashboard UI. Each task builds incrementally, with property-based tests integrated alongside implementation to catch errors early.

## Tasks

- [x] 1. Update C++ VRPSolver signature and core logic
  - [x] 1.1 Modify `solve()` method signature in `include/solver.h`
    - Change parameter from `double vehicle_capacity` to `const std::vector<double>& vehicle_capacities`
    - Update method documentation
    - _Requirements: 2.1_
  
  - [x] 1.2 Update `nearestNeighborHeuristic()` method signature in `include/solver.h` and `src/solver.cpp`
    - Change parameter from `double vehicle_capacity` to `const std::vector<double>& vehicle_capacities`
    - Update method to iterate through vehicle capacity vector
    - Use `vehicle_capacities[vehicle_idx]` for each route's capacity constraint
    - Stop creating routes when `vehicle_idx >= vehicle_capacities.size()`
    - _Requirements: 2.1, 2.2, 2.4_
  
  - [x] 1.3 Update `solve()` method implementation in `src/solver.cpp`
    - Add input validation: throw `std::invalid_argument` if `vehicle_capacities` is empty
    - Add input validation: throw `std::invalid_argument` if any capacity is non-positive
    - Pass `vehicle_capacities` to `nearestNeighborHeuristic()`
    - _Requirements: 2.1_
  
  - [ ]* 1.4 Write property test for route capacity constraint
    - **Property 5: Route Capacity Constraint**
    - **Validates: Requirements 2.2, 2.3**
  
  - [ ]* 1.5 Write property test for maximum routes constraint
    - **Property 6: Maximum Routes Constraint**
    - **Validates: Requirements 2.4**

- [x] 2. Update Python bindings
  - [x] 2.1 Modify `solve()` binding in `src/bindings.cpp`
    - Change `nb::arg("vehicle_capacity")` to `nb::arg("vehicle_capacities")`
    - Update docstring to reflect new parameter
    - Verify Nanobind automatically converts Python `list[float]` to C++ `std::vector<double>`
    - _Requirements: 3.1, 3.2, 3.3, 3.4_
  
  - [x] 2.2 Rebuild C++ extension module
    - Run `cmake --build build/` to compile changes
    - Verify no compilation errors
    - _Requirements: 3.3_
  
  - [ ]* 2.3 Write property test for Python-to-C++ data flow
    - **Property 8: Python to C++ Data Flow**
    - **Validates: Requirements 3.2, 3.4**

- [x] 3. Checkpoint - Verify C++ core and bindings work
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Implement Dashboard fleet configuration logic
  - [x] 4.1 Create `flatten_and_sort_fleet()` function in `dashboard/app.py`
    - Accept list of vehicle profile dicts (keys: name, capacity, quantity)
    - Flatten profiles into list of vehicle dicts with instance numbers
    - Sort by capacity in descending order
    - Return tuple of (vehicle_capacities list, vehicle_map list)
    - _Requirements: 1.5, 1.6_
  
  - [x] 4.2 Create input validation function for vehicle profiles
    - Validate capacity is positive number
    - Validate quantity is positive integer
    - Return validation errors if any
    - _Requirements: 1.2, 1.3_
  
  - [ ]* 4.3 Write property test for fleet flattening correctness
    - **Property 3: Fleet Flattening Correctness**
    - **Validates: Requirements 1.5**
  
  - [ ]* 4.4 Write property test for capacity list sorting
    - **Property 4: Capacity List Sorting**
    - **Validates: Requirements 1.6**
  
  - [ ]* 4.5 Write property test for fleet size calculation
    - **Property 2: Fleet Size Calculation**
    - **Validates: Requirements 1.4**
  
  - [ ]* 4.6 Write property test for input validation
    - **Property 1: Fleet Configuration Input Validation**
    - **Validates: Requirements 1.2, 1.3**

- [x] 5. Implement Dashboard fleet configuration UI
  - [x] 5.1 Create Fleet Configuration section in Streamlit UI
    - Replace "Number of Vehicles" slider with Fleet Configuration section
    - Add UI for adding vehicle profiles (name, capacity, quantity inputs)
    - Add "Add Vehicle" button
    - Add ability to remove vehicle profiles
    - Display current fleet composition
    - _Requirements: 1.1, 1.2_
  
  - [x] 5.2 Integrate fleet configuration with solver invocation
    - Call `flatten_and_sort_fleet()` to convert profiles to capacity list
    - Pass `vehicle_capacities` list to `solver.solve()` instead of single capacity
    - Store `vehicle_map` in session state for visualization
    - _Requirements: 1.5, 1.6_
  
  - [x] 5.3 Add error handling for invalid fleet configurations
    - Display validation errors from input validation function
    - Prevent solver invocation if validation fails
    - Show warning if fleet configuration is empty
    - _Requirements: 1.3_

- [x] 6. Update Dashboard route visualization
  - [x] 6.1 Create `display_route_with_vehicle()` function
    - Accept route index, route data, and vehicle_map
    - Return formatted string with vehicle name, instance, and capacity
    - Format: "Route {i} ({VehicleName} #{instance} - Cap {capacity})"
    - _Requirements: 4.2, 4.3, 4.4_
  
  - [x] 6.2 Update route details table to include vehicle assignment column
    - Add "Vehicle" column to route details table
    - Use `display_route_with_vehicle()` to populate column
    - _Requirements: 4.1, 4.2_
  
  - [x] 6.3 Add fleet utilization display
    - Calculate total fleet capacity from vehicle_map
    - Calculate total demand served from routes
    - Display utilization percentage: (demand / capacity) × 100
    - _Requirements: 4.5_
  
  - [ ]* 6.4 Write property test for vehicle assignment display
    - **Property 9: Vehicle Assignment Display**
    - **Validates: Requirements 4.1, 4.2**
  
  - [ ]* 6.5 Write property test for route-to-vehicle mapping
    - **Property 11: Route-to-Vehicle Mapping**
    - **Validates: Requirements 4.4**
  
  - [ ]* 6.6 Write property test for fleet utilization calculation
    - **Property 12: Fleet Utilization Calculation**
    - **Validates: Requirements 4.5**

- [x] 7. Handle unassigned customers scenario
  - [x] 7.1 Add logic to detect unassigned customers
    - Compare total customers with customers in routes
    - Identify customer IDs not present in any route
    - _Requirements: 2.5_
  
  - [x] 7.2 Display warning for unassigned customers
    - Show warning message if unassigned customers exist
    - Display count of unassigned customers
    - Suggest adding more vehicles or increasing capacities
    - _Requirements: 2.5_
  
  - [ ]* 7.3 Write property test for unassigned customer tracking
    - **Property 7: Unassigned Customer Tracking**
    - **Validates: Requirements 2.5**

- [-] 8. Update existing tests and documentation
  - [x] 8.1 Update existing unit tests in `tests/test_solver.py`
    - Modify tests that call `solve()` to use vehicle_capacities list
    - Update test cases to use heterogeneous fleet scenarios
    - _Requirements: 2.1, 3.1_
  
  - [x] 8.2 Add integration tests for complete workflow
    - Test Dashboard → Bindings → Solver → Dashboard flow
    - Test with various fleet configurations (homogeneous, heterogeneous, edge cases)
    - _Requirements: 5.4_
  
  - [ ]* 8.3 Write property test for complete route information
    - **Property 13: Complete Route Information**
    - **Validates: Requirements 5.2, 5.4**
  
  - [x] 8.4 Update README and documentation
    - Document new fleet configuration feature
    - Add examples of heterogeneous fleet usage
    - Update API documentation for `solve()` method
    - _Requirements: All_

- [x] 9. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- The DLL loading configuration in `dashboard/app.py` must be preserved (see DLL Issue.md steering file)
