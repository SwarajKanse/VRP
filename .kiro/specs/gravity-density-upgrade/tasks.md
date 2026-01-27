# Implementation Plan: Gravity & Density Upgrade

## Overview

This implementation plan breaks down the DBL (Deepest-Bottom-Left) packing engine into discrete, testable components. The approach follows an incremental development strategy: build core data structures first, implement the DBL algorithm with contact point generation, add constraint validation (support and weight), integrate with existing LIFO sorting, and finally add comprehensive testing and error handling.

Each task builds on previous work, with checkpoints to ensure correctness before proceeding. Property-based tests are integrated throughout to validate universal correctness properties.

## Tasks

- [x] 1. Set up core data structures and test infrastructure
  - Create `dashboard/packing_engine_dbl.py` with Package, ContactPoint, PlacedPackage, and PackingResult dataclasses
  - Implement helper methods: `overlaps_xy()`, `get_support_area()`, property accessors
  - Set up pytest test file `tests/test_packing_dbl.py` with hypothesis configuration
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.3, 2.4, 2.5, 2.6, 3.1, 3.2, 3.3, 3.5, 4.1, 4.2, 4.3, 4.4, 5.3, 5.4_

- [x] 2. Implement contact point generation and management
  - [x] 2.1 Implement `_euclidean_distance()` method for distance calculation
    - Calculate √(x² + y² + z²) for any 3D point
    - _Requirements: 2.3_
  
  - [ ]* 2.2 Write property test for Euclidean distance calculation
    - **Property 4: Euclidean Distance Calculation**
    - **Validates: Requirements 2.3**
  
  - [x] 2.3 Implement `_update_contact_points()` method
    - Generate three contact points from placed package (right, front, top)
    - Filter out points outside vehicle boundaries
    - Filter out points occupied by existing packages
    - _Requirements: 4.2, 4.3, 4.4_
  
  - [ ]* 2.4 Write property test for contact point generation
    - **Property 12: Contact Point Generation from Placed Package**
    - **Validates: Requirements 4.2**
  
  - [ ]* 2.5 Write property test for boundary filtering
    - **Property 13: Boundary Filtering**
    - **Validates: Requirements 4.3**
  
  - [ ]* 2.6 Write property test for occupancy filtering
    - **Property 14: Occupancy Filtering**
    - **Validates: Requirements 4.4**
  
  - [x] 2.7 Implement ContactPoint sorting with tie-breaker logic
    - Sort by distance, then Z, then X, then Y
    - Implement `__lt__` method on ContactPoint class
    - _Requirements: 2.4, 2.5_
  
  - [ ]* 2.8 Write property test for distance tie-breaking
    - **Property 6: Distance Tie-Breaking**
    - **Validates: Requirements 2.5**

- [x] 3. Implement placement validation constraints
  - [x] 3.1 Implement `_check_boundaries()` method
    - Verify package fits within vehicle dimensions
    - _Requirements: 5.1, 5.2_
  
  - [x] 3.2 Implement `_check_overlap()` and `_packages_overlap_3d()` methods
    - Detect 3D intersection between packages
    - _Requirements: 5.1, 5.2_
  
  - [x] 3.3 Implement `_check_support()` method with 80% support rule
    - Calculate total support area from packages below
    - Compare against 80% threshold
    - Handle floor placement (z = 0) exemption
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_
  
  - [ ]* 3.4 Write property test for 80% support threshold
    - **Property 1: 80% Support Threshold**
    - **Validates: Requirements 1.1, 1.2**
  
  - [ ]* 3.5 Write property test for floor placement exemption
    - **Property 2: Floor Placement Exemption**
    - **Validates: Requirements 1.3**
  
  - [ ]* 3.6 Write property test for bridge support calculation
    - **Property 3: Bridge Support Calculation**
    - **Validates: Requirements 1.4, 1.5**
  
  - [x] 3.7 Implement `_check_weight_constraint()` method
    - Verify weight ratio ≤ 1.5x for all supporting packages
    - Handle floor placement (no weight constraint)
    - Handle bridge support (check all supports)
    - _Requirements: 3.3, 3.5_
  
  - [ ]* 3.8 Write property test for weight ratio constraint
    - **Property 10: Weight Ratio Constraint**
    - **Validates: Requirements 3.3, 3.5**
  
  - [x] 3.9 Implement `_can_place_at()` method integrating all constraints
    - Call boundary, overlap, support, and weight checks in sequence
    - Return true only if all constraints pass
    - _Requirements: 5.1, 5.2_

- [x] 4. Checkpoint - Ensure constraint validation tests pass
  - Run all property tests for contact points and constraints
  - Verify support calculation accuracy with known configurations
  - Ensure all tests pass, ask the user if questions arise

- [x] 5. Implement LIFO sorting and DBL placement algorithm
  - [x] 5.1 Implement `_sort_packages_lifo()` method
    - Primary sort: Reverse stop order (descending stop number)
    - Secondary sort: Weight descending within same stop
    - _Requirements: 3.1, 3.2_
  
  - [ ]* 5.2 Write property test for primary sort by reverse stop order
    - **Property 8: Primary Sort by Reverse Stop Order**
    - **Validates: Requirements 3.1**
  
  - [ ]* 5.3 Write property test for secondary sort by weight
    - **Property 9: Secondary Sort by Weight**
    - **Validates: Requirements 3.2**
  
  - [x] 5.4 Implement `_try_place_package()` method
    - Sort contact points by DBL heuristic
    - Try each contact point until valid placement found
    - Return true if placed, false if all attempts fail
    - _Requirements: 2.1, 2.2, 2.4, 2.5, 2.6_
  
  - [ ]* 5.5 Write property test for minimum distance selection
    - **Property 5: Minimum Distance Selection**
    - **Validates: Requirements 2.4**
  
  - [x] 5.6 Implement `_place_package_at()` method
    - Create PlacedPackage and add to placed list
    - _Requirements: 2.1_
  
  - [x] 5.7 Implement main `pack_route()` method
    - Sort packages using LIFO strategy
    - Initialize contact points with origin (0,0,0)
    - Loop through packages, trying to place each
    - Collect failed packages with reasons
    - Calculate utilization and total weight
    - Return PackingResult
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.3, 2.4, 2.5, 2.6, 3.1, 3.2, 3.3, 3.5, 4.1, 4.2, 4.3, 4.4_
  
  - [ ]* 5.8 Write property test for initial contact point
    - **Property 11: Initial Contact Point**
    - **Validates: Requirements 4.1**
  
  - [ ]* 5.9 Write property test for placement failure reporting
    - **Property 7: Placement Failure Reporting**
    - **Validates: Requirements 2.6**

- [x] 6. Implement error handling and failure diagnostics
  - [x] 6.1 Implement `_get_failure_reason()` method
    - Diagnose why package couldn't be placed
    - Distinguish between size overflow and stability failure
    - Return descriptive error message
    - _Requirements: 5.3, 5.4_
  
  - [ ]* 6.2 Write property test for failure reason reporting
    - **Property 15: Failure Reason Reporting**
    - **Validates: Requirements 5.3**
  
  - [ ]* 6.3 Write property test for failure type categorization
    - **Property 16: Failure Type Categorization**
    - **Validates: Requirements 5.4**
  
  - [x] 6.4 Implement `_calculate_utilization()` method
    - Calculate volume utilization percentage
    - Handle edge case of empty vehicle
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_
  
  - [x] 6.5 Add input validation for package and vehicle data
    - Validate positive dimensions and weights
    - Validate valid stop numbers
    - Raise ValueError with descriptive messages for invalid inputs
    - _Requirements: 5.3, 5.4_

- [x] 7. Checkpoint - Ensure core algorithm tests pass
  - Run all property tests for LIFO sorting and DBL placement
  - Test with sample package sets (5, 10, 20 packages)
  - Verify LIFO ordering preserved in placement
  - Ensure all tests pass, ask the user if questions arise

- [x] 8. Integration and compatibility testing
  - [x] 8.1 Create integration test with existing CSV parser output
    - Load sample CSV from realistic-data-physics-upgrade
    - Parse packages and assign stop numbers
    - Run DBL packing engine
    - Verify results are valid
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.3, 2.4, 2.5, 2.6, 3.1, 3.2, 3.3, 3.5, 4.1, 4.2, 4.3, 4.4, 5.3, 5.4_
  
  - [x] 8.2 Create compatibility test with existing visualization system
    - Generate PlacedPackage objects from DBL engine
    - Verify coordinate system matches existing convention (X=0 is back)
    - Verify visualization can render DBL packing results
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_
  
  - [x] 8.3 Add configuration option to switch between LIFO and DBL engines
    - Create PackingConfig dataclass with engine selection
    - Update dashboard to allow engine selection
    - Run both engines in parallel for comparison
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.3, 2.4, 2.5, 2.6, 3.1, 3.2, 3.3, 3.5, 4.1, 4.2, 4.3, 4.4, 5.3, 5.4_
  
  - [ ]* 8.4 Write integration tests for end-to-end packing workflow
    - Test with multiple stops and mixed package sizes
    - Verify all placed packages satisfy constraints
    - Verify failed packages have valid reasons
    - Test utilization calculation accuracy
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.3, 2.4, 2.5, 2.6, 3.1, 3.2, 3.3, 3.5, 4.1, 4.2, 4.3, 4.4, 5.3, 5.4_

- [-] 9. Performance testing and optimization
  - [ ]* 9.1 Create performance benchmark tests
    - Test with 10, 50, 100 packages
    - Measure execution time
    - Verify sub-1-second performance for typical routes (20-50 packages)
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.3, 2.4, 2.5, 2.6, 3.1, 3.2, 3.3, 3.5, 4.1, 4.2, 4.3, 4.4_
  
  - [ ]* 9.2 Profile contact point generation overhead
    - Measure time spent generating and filtering contact points
    - Identify bottlenecks in placement validation
    - Document performance characteristics
    - _Requirements: 4.1, 4.2, 4.3, 4.4_
  
  - [x] 9.3 Add optional contact point limit for performance
    - Implement max_contact_points configuration option
    - Keep only top N contact points by distance
    - Test impact on packing quality vs. speed
    - _Requirements: 2.1, 2.4, 4.1, 4.2, 4.3, 4.4_

- [x] 10. Final checkpoint and documentation
  - Run complete test suite (unit + property + integration)
  - Verify all 16 correctness properties pass with 100+ iterations
  - Update dashboard documentation with DBL algorithm explanation
  - Create usage examples and comparison with LIFO engine
  - Ensure all tests pass, ask the user if questions arise

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- Integration tests ensure compatibility with existing system
- Performance tests verify acceptable execution speed
