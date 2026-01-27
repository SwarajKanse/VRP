# Implementation Plan: Time Window Constraint Enforcement

## Overview

This implementation plan breaks down the time window enforcement feature into discrete coding tasks. The approach follows an incremental strategy: first updating the C++ core data structures and solver logic, then updating Python bindings, and finally integrating with the Dashboard. Each task builds on previous work and includes testing to validate functionality early.

## Tasks

- [x] 1. Update Customer struct with service_time field
  - Add `service_time` field to Customer struct in `include/solver.h`
  - Update Customer constructor to accept service_time parameter with default value of 0.0
  - Update Customer constructor implementation in `src/solver.cpp`
  - _Requirements: 1.1, 1.2, 1.3_

- [ ]* 1.1 Write property test for service_time default value
  - **Property 7: Service Time Default**
  - **Validates: Requirements 1.3**

- [x] 2. Add time_matrix support to VRPSolver
  - [x] 2.1 Add time_matrix member variable and use_time_matrix flag to VRPSolver class
    - Add `std::vector<std::vector<double>> time_matrix_` private member
    - Add `bool use_time_matrix_` private member
    - Update `include/solver.h`
    - _Requirements: 2.1_
  
  - [x] 2.2 Update solve() method signature to accept time_matrix parameter
    - Add optional `time_matrix` parameter to solve() method
    - Add validation logic for time_matrix dimensions
    - Set use_time_matrix flag based on whether time_matrix is provided
    - Update `include/solver.h` and `src/solver.cpp`
    - _Requirements: 2.1, 2.5_
  
  - [ ]* 2.3 Write property test for matrix dimension validation
    - **Property 6: Matrix Dimension Validation**
    - **Validates: Requirements 2.5, 7.4**
  
  - [x] 2.4 Implement getTravelTime() helper method
    - Add private method `double getTravelTime(int from_idx, int to_idx) const`
    - Implement logic to use time_matrix when available, fallback to distance_matrix * 1.5
    - Update `include/solver.h` and `src/solver.cpp`
    - _Requirements: 2.2, 2.3, 2.4_
  
  - [ ]* 2.5 Write property test for time matrix usage
    - **Property 1: Time Matrix Usage**
    - **Validates: Requirements 2.2, 2.3**
  
  - [ ]* 2.6 Write unit test for backward compatibility
    - **Property 9: Backward Compatibility**
    - **Validates: Requirements 2.4, 7.2, 7.3**

- [x] 3. Checkpoint - Ensure time matrix integration tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Implement time window validation in canAddToRoute()
  - [x] 4.1 Update canAddToRoute() to calculate arrival_time
    - Get current location from route
    - Calculate travel_time using getTravelTime()
    - Calculate arrival_time as current_time + travel_time
    - Update `src/solver.cpp`
    - _Requirements: 3.1_
  
  - [x] 4.2 Add time window constraint check
    - Reject customer if arrival_time > end_window
    - Allow customer if arrival_time <= end_window
    - Update `src/solver.cpp`
    - _Requirements: 3.2, 3.3, 3.4_
  
  - [ ]* 4.3 Write property test for late arrival rejection
    - **Property 2: Late Arrival Rejection**
    - **Validates: Requirements 3.2**
  
  - [ ]* 4.4 Write property test for early arrival waiting
    - **Property 3: Early Arrival Waiting**
    - **Validates: Requirements 3.3, 4.2**
  
  - [ ]* 4.5 Write property test for on-time arrival
    - **Property 4: On-Time Arrival No Waiting**
    - **Validates: Requirements 3.4, 4.2**

- [x] 5. Implement time tracking in nearestNeighborHeuristic()
  - [x] 5.1 Add current_time tracking to route construction loop
    - Initialize current_time to 0.0 at start of each route
    - Pass current_time to canAddToRoute() when evaluating customers
    - Update `src/solver.cpp`
    - _Requirements: 4.1_
  
  - [x] 5.2 Update time after adding customer to route
    - Calculate arrival_time using getTravelTime()
    - Calculate waiting_time as max(0, start_window - arrival_time)
    - Update current_time as arrival_time + waiting_time + service_time
    - Update `src/solver.cpp`
    - _Requirements: 4.2, 4.3, 4.5_
  
  - [ ]* 5.3 Write property test for time progression consistency
    - **Property 5: Time Progression Consistency**
    - **Validates: Requirements 4.3, 4.5**

- [x] 6. Checkpoint - Ensure C++ solver tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Update Python bindings
  - [x] 7.1 Expose service_time field in Customer binding
    - Add `.def_rw("service_time", &Customer::service_time)` to Customer class binding
    - Update Customer constructor binding to accept service_time parameter
    - Update `src/bindings.cpp`
    - _Requirements: 1.4_
  
  - [x] 7.2 Add time_matrix parameter to solve() binding
    - Add `nb::arg("time_matrix") = std::vector<std::vector<double>>()` to solve() binding
    - Update `src/bindings.cpp`
    - _Requirements: 7.1, 7.2, 7.5_
  
  - [ ]* 7.3 Write unit tests for Python bindings
    - Test Customer creation with service_time
    - Test solve() with time_matrix parameter
    - Test solve() without time_matrix (backward compatibility)
    - Test type conversion from Python list to C++ vector
    - _Requirements: 1.4, 7.1, 7.2, 7.3, 7.5_

- [x] 8. Update Dashboard to generate time_matrix
  - [x] 8.1 Add generate_time_matrix() function
    - Create function that takes DataFrame of customers
    - Calculate Haversine distance for all customer pairs
    - Convert to travel time using distance * 1.5 (40 km/h)
    - Return N×N matrix as list of lists
    - Update `dashboard/app.py`
    - _Requirements: 5.1, 5.2, 5.3, 5.4_
  
  - [ ]* 8.2 Write property test for time matrix calculation
    - **Property 8: Dashboard Time Matrix Calculation**
    - **Validates: Requirements 5.2**
  
  - [x] 8.3 Update solve_routing() to pass time_matrix to solver
    - Call generate_time_matrix() before calling solver
    - Pass time_matrix as parameter to solver.solve()
    - Update `dashboard/app.py`
    - _Requirements: 5.1_

- [x] 9. Update Dashboard to display service_time
  - [x] 9.1 Add service_time column to demo data generation
    - Update generate_demo_data() to include service_time field (default 10 minutes)
    - Update `dashboard/app.py`
    - _Requirements: 6.1, 6.2_
  
  - [x] 9.2 Handle service_time in CSV loading
    - Update load_customer_csv() to read service_time if present
    - Use default value of 10 if service_time column is missing
    - Update `dashboard/app.py`
    - _Requirements: 6.3, 6.4_
  
  - [ ]* 9.3 Write unit tests for Dashboard data handling
    - Test demo data includes service_time
    - Test CSV loading with service_time column
    - Test CSV loading without service_time column (default)
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [x] 10. Update Dashboard to display arrival times
  - [x] 10.1 Calculate and display arrival times in route details
    - Add function to calculate arrival times for each customer in a route
    - Update route details display to show arrival_time for each customer
    - Format times as minutes from start of day
    - Update `dashboard/app.py`
    - _Requirements: 6.5_
  
  - [x] 10.2 Display waiting times when applicable
    - Calculate waiting_time for each customer
    - Display waiting_time when > 0
    - Add visual indicator (e.g., icon or color) for customers with waiting
    - Update `dashboard/app.py`
    - _Requirements: 6.6, 6.7_
  
  - [ ]* 10.3 Write unit tests for arrival time display
    - Test arrival time calculation
    - Test waiting time calculation
    - Test display formatting
    - _Requirements: 6.5, 6.6_

- [x] 11. Final checkpoint - Integration testing
  - [x] 11.1 Test end-to-end flow with Dashboard
    - Generate demo data with service times
    - Run solver with time_matrix
    - Verify routes respect time windows
    - Verify arrival times displayed correctly
    - _Requirements: All_
  
  - [ ]* 11.2 Write integration tests
    - Test complete flow from Dashboard to solver to results
    - Test with tight time windows
    - Test with long service times
    - Test with early arrivals (waiting scenarios)
    - _Requirements: All_

- [x] 12. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- The implementation maintains backward compatibility throughout
- CRITICAL: When modifying `dashboard/app.py`, preserve the DLL loading configuration at the top of the file
