# Implementation Plan: cpp-vrp-solver-foundation

## Overview

This implementation plan breaks down the VRP solver foundation into incremental coding tasks. The approach follows a bottom-up strategy: first establishing the build system and data structures, then implementing core algorithms, followed by Python bindings, and finally comprehensive testing. Each task builds on previous work to ensure continuous integration and validation.

## Tasks

- [x] 1. Set up project structure and CMake build system
  - Create directory structure: `include/`, `src/`, `tests/`
  - Write `CMakeLists.txt` with C++20 standard, Nanobind integration, and module definition
  - Create placeholder files: `include/solver.h`, `src/solver.cpp`, `src/bindings.cpp`, `src/main.cpp`
  - Verify CMake configuration succeeds and finds Nanobind
  - _Requirements: 1.1, 1.2, 1.4_

- [x] 2. Implement core data structures
  - [x] 2.1 Implement Location struct in `include/solver.h`
    - Define struct with latitude and longitude fields
    - Implement constructor and equality operator
    - _Requirements: 2.1, 2.5_
  
  - [ ]* 2.2 Write property test for Location value preservation
    - **Property 1: Location Value Preservation**
    - **Validates: Requirements 2.1, 2.3**
  
  - [ ]* 2.3 Write property test for Location equality
    - **Property 3: Location Equality Reflexivity**
    - **Validates: Requirements 2.5**
  
  - [x] 2.4 Implement Customer struct in `include/solver.h`
    - Define struct with id, location, demand, start_window, end_window fields
    - Implement constructor
    - _Requirements: 2.2_
  
  - [ ]* 2.5 Write property test for Customer value preservation
    - **Property 2: Customer Value Preservation**
    - **Validates: Requirements 2.2, 2.4**

- [x] 3. Implement Haversine distance calculation
  - [x] 3.1 Implement haversineDistance() method in VRPSolver class
    - Convert degrees to radians
    - Apply Haversine formula: a = sin²(Δlat/2) + cos(lat1) × cos(lat2) × sin²(Δlon/2)
    - Calculate c = 2 × atan2(√a, √(1-a))
    - Return distance = R × c (R = 6371 km)
    - _Requirements: 3.1, 3.2_
  
  - [ ]* 3.2 Write unit test for known distance calculation
    - Test NYC to LA distance (≈ 3936 km)
    - Test self-distance returns zero
    - _Requirements: 3.2, 3.5_
  
  - [x] 3.3 Implement buildDistanceMatrix() method
    - Allocate n × n matrix
    - Compute distances for all customer pairs using haversineDistance()
    - Set diagonal to zero
    - _Requirements: 3.3_
  
  - [ ]* 3.4 Write property test for distance matrix symmetry
    - **Property 4: Distance Matrix Symmetry**
    - **Validates: Requirements 3.1, 3.4**
  
  - [ ]* 3.5 Write property test for distance matrix completeness
    - **Property 5: Distance Matrix Completeness**
    - **Validates: Requirements 3.3**

- [x] 4. Checkpoint - Verify distance calculations
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement constraint validation helpers
  - [x] 5.1 Implement calculateRouteLoad() method
    - Sum demands for all customers in a route
    - Return total load
    - _Requirements: 4.4_
  
  - [x] 5.2 Implement canAddToRoute() method
    - Check capacity constraint: route_load + customer.demand ≤ capacity
    - Calculate arrival time: current_time + travel_time
    - Check time window: arrival_time ≤ customer.end_window
    - Return true if all constraints satisfied
    - _Requirements: 4.4, 4.5_

- [x] 6. Implement Nearest Neighbor heuristic
  - [x] 6.1 Implement nearestNeighborHeuristic() method
    - Initialize visited array (all false except depot)
    - While unvisited customers exist:
      - Start new route at depot (customer 0)
      - Greedily add nearest feasible customer
      - Update current location, load, and time
      - When no feasible customer, finalize route
    - Return list of routes
    - _Requirements: 4.3, 5.1, 5.2, 5.3, 5.4, 5.5_
  
  - [ ]* 6.2 Write property test for routes start at depot
    - **Property 8: Routes Start at Depot**
    - **Validates: Requirements 5.1**
  
  - [ ]* 6.3 Write property test for greedy nearest selection
    - **Property 9: Greedy Nearest Selection**
    - **Validates: Requirements 5.2**

- [x] 7. Implement VRPSolver::solve() method
  - [x] 7.1 Implement solve() public method
    - Validate inputs (capacity > 0, customers not empty)
    - Call buildDistanceMatrix()
    - Call nearestNeighborHeuristic()
    - Return routes
    - _Requirements: 4.1, 4.2, 4.7_
  
  - [ ]* 7.2 Write property test for capacity constraints
    - **Property 6: Route Capacity Constraint**
    - **Validates: Requirements 4.4, 7.4**
  
  - [ ]* 7.3 Write property test for time window constraints
    - **Property 7: Route Time Window Constraint**
    - **Validates: Requirements 4.5, 7.5**
  
  - [ ]* 7.4 Write property test for all customers visited or identified
    - **Property 10: All Customers Visited or Identified as Unserved**
    - **Validates: Requirements 4.6**
  
  - [ ]* 7.5 Write unit test for error conditions
    - Test invalid capacity (≤ 0) raises exception
    - Test empty customer list returns empty routes
    - Test infeasible problem returns partial solution
    - _Requirements: 4.6_

- [x] 8. Checkpoint - Verify core solver logic
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Implement Nanobind Python bindings
  - [x] 9.1 Write bindings.cpp with Nanobind module definition
    - Define NB_MODULE(vrp_core, m)
    - Bind Location class with constructor and read-write properties
    - Bind Customer class with constructor and read-write properties
    - Bind VRPSolver class with constructor and solve method
    - Include necessary Nanobind headers (nanobind.h, stl/vector.h)
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_
  
  - [ ]* 9.2 Write unit test for module import
    - Test `import vrp_core` succeeds
    - _Requirements: 1.3, 1.5, 6.6, 7.2_
  
  - [ ]* 9.3 Write unit test for Python binding attributes
    - Test Location attributes accessible from Python
    - Test Customer attributes accessible from Python
    - Test VRPSolver.solve() callable from Python
    - Test solve() accepts list of Customers and capacity
    - Test solve() returns list of routes (list of list of ints)
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 10. Build and verify Python extension module
  - [x] 10.1 Update CMakeLists.txt to build vrp_core module
    - Use nanobind_add_module() to create Python extension
    - Link solver.cpp and bindings.cpp
    - Set include directories
    - Add Release mode optimizations (-O3, -march=native)
    - _Requirements: 1.2, 1.3_
  
  - [x] 10.2 Build project and verify module is created
    - Run cmake and make
    - Verify vrp_core module file exists (.so or .pyd)
    - _Requirements: 1.3_

- [x] 11. Create comprehensive test suite
  - [x] 11.1 Write tests/test_solver.py with pytest
    - Import vrp_core module
    - Create test fixtures for sample customers
    - Implement all unit tests (module import, known distances, error conditions)
    - Implement all property tests (Properties 1-10) using hypothesis
    - Configure hypothesis with minimum 100 iterations
    - Tag each property test with feature and property number
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_
  
  - [ ]* 11.2 Run full test suite and verify all tests pass
    - Execute pytest with verbose output
    - Verify all unit tests pass
    - Verify all property tests pass with 100+ iterations
    - _Requirements: 7.2, 7.3, 7.4, 7.5_

- [x] 12. Create optional C++ main entry point
  - [x] 12.1 Write src/main.cpp with example usage
    - Create sample customers
    - Instantiate VRPSolver
    - Call solve() and print routes
    - Demonstrate C++ API usage
    - _Requirements: 1.1_

- [x] 13. Final checkpoint - Complete integration verification
  - Ensure all tests pass, ask the user if questions arise.
  - Verify project compiles successfully
  - Verify Python can import vrp_core module
  - Verify VRPSolver.solve() returns valid routes
  - Verify all property tests pass

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at key milestones
- Property tests validate universal correctness properties with 100+ iterations
- Unit tests validate specific examples, edge cases, and integration points
- Build system must be configured before implementing bindings
- Core C++ logic should be tested before adding Python layer
