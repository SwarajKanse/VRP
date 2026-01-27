# Implementation Plan: AVX2 Distance Optimization

## Overview

This implementation plan breaks down the AVX2 SIMD optimization into incremental steps, starting with the foundational Euclidean distance function, then adding SIMD infrastructure, and finally integrating everything with comprehensive testing. Each task builds on previous work to ensure continuous validation.

## Tasks

- [x] 1. Add Euclidean distance function and update scalar path
  - [x] 1.1 Implement euclideanDistance() method in VRPSolver
    - Add private method `double euclideanDistance(double lat1, double lon1, double lat2, double lon2) const`
    - Implement formula: `sqrt((lat2-lat1)^2 + (lon2-lon1)^2)`
    - _Requirements: 2.3, 3.2_
  
  - [x] 1.2 Update buildDistanceMatrix to use Euclidean distance
    - Modify existing scalar loop to call euclideanDistance instead of haversineDistance
    - Keep haversineDistance method for backward compatibility
    - _Requirements: 3.3_
  
  - [ ]* 1.3 Write unit test for Euclidean distance calculation
    - Test known coordinate pairs produce expected distances
    - Test edge cases (same point, antipodal points)
    - _Requirements: 2.3_

- [x] 2. Implement coordinate extraction (SoA transformation)
  - [x] 2.1 Add extractCoordinates() method
    - Add private method `void extractCoordinates(const std::vector<Customer>&, std::vector<double>& lats, std::vector<double>& lons)`
    - Implement extraction loop that preserves customer ordering
    - _Requirements: 1.1, 1.2, 1.3_
  
  - [ ]* 2.2 Write property test for coordinate extraction
    - **Property 1: Coordinate Extraction Preserves Data**
    - **Validates: Requirements 1.1, 1.2, 1.3**
    - Generate random customer lists, verify extracted arrays match original data
    - _Requirements: 1.1, 1.2, 1.3_
  
  - [ ]* 2.3 Write property test for input immutability
    - **Property 2: Input Immutability**
    - **Validates: Requirements 1.4**
    - Verify customer vector unchanged after extraction
    - _Requirements: 1.4_


- [x] 3. Implement CPU feature detection
  - [x] 3.1 Add hasAVX2Support() method
    - Add private method `bool hasAVX2Support() const`
    - Implement compile-time detection using `#if defined(__AVX2__)`
    - Add conditional include for `<immintrin.h>` with AVX2 guard
    - _Requirements: 6.1, 6.3, 2.7_
  
  - [ ]* 3.2 Write unit test for CPU detection
    - Test that hasAVX2Support() returns a boolean value
    - Test behavior on current platform
    - _Requirements: 6.1_

- [x] 4. Implement AVX2 batch distance computation
  - [x] 4.1 Add computeBatchDistancesAVX2() method
    - Add private method `void computeBatchDistancesAVX2(const std::vector<double>& lats, const std::vector<double>& lons, size_t from_idx, size_t to_idx)`
    - Implement AVX2 intrinsics for loading 4 coordinates at a time
    - Use `_mm256_loadu_pd` for unaligned loads from std::vector
    - Compute Euclidean distance: delta, square, sum, sqrt using AVX2 operations
    - Store results in distance matrix (both [i][j] and [j][i] for symmetry)
    - Implement scalar fallback for remainder customers (when count not divisible by 4)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_
  
  - [ ]* 4.2 Write property test for non-divisible-by-4 correctness
    - **Property 6: Non-Divisible-by-4 Correctness**
    - **Validates: Requirements 2.6**
    - Test customer counts 1, 2, 3, 5, 6, 7, 10, 11 produce correct results
    - _Requirements: 2.6_

- [x] 5. Update buildDistanceMatrix with SIMD path selection
  - [x] 5.1 Add use_simd parameter to buildDistanceMatrix
    - Modify signature: `void buildDistanceMatrix(const std::vector<Customer>&, bool use_simd)`
    - Implement conditional logic: if (use_simd && hasAVX2Support()) use SIMD path, else scalar
    - SIMD path: call extractCoordinates, then loop calling computeBatchDistancesAVX2
    - Scalar path: existing loop with euclideanDistance
    - _Requirements: 4.1, 4.2, 4.3, 6.2_
  
  - [ ]* 5.2 Write property test for distance matrix symmetry
    - **Property 4: Distance Matrix Symmetry**
    - **Validates: Requirements 3.5**
    - Verify distance[i][j] == distance[j][i] for all i, j
    - _Requirements: 3.5_

- [x] 6. Update VRPSolver::solve() public API
  - [x] 6.1 Add use_simd parameter to solve() method
    - Modify signature in include/solver.h: `std::vector<Route> solve(const std::vector<Customer>&, double capacity, bool use_simd = true)`
    - Pass use_simd to buildDistanceMatrix call
    - Update implementation in src/solver.cpp
    - _Requirements: 4.1_
  
  - [ ]* 6.2 Write unit test for API backward compatibility
    - Test calling solve() without use_simd parameter (should default to true)
    - Test calling solve() with use_simd=false explicitly
    - _Requirements: 4.1, 5.4_


- [x] 7. Update Python bindings
  - [x] 7.1 Expose use_simd parameter in bindings.cpp
    - Modify VRPSolver.solve() binding to include `nb::arg("use_simd") = true`
    - Update binding signature to match C++ API
    - _Requirements: 5.1, 5.2, 5.3_
  
  - [ ]* 7.2 Write unit test for Python API
    - Test calling solve() from Python without use_simd (should work)
    - Test calling solve() from Python with use_simd=True
    - Test calling solve() from Python with use_simd=False
    - _Requirements: 5.1, 5.4_

- [x] 8. Checkpoint - Core SIMD implementation complete
  - Ensure all tests pass with both SIMD and scalar paths
  - Verify compilation on systems with and without AVX2
  - Ask the user if questions arise

- [ ] 9. Implement comprehensive correctness validation
  - [ ]* 9.1 Write property test for SIMD/scalar equivalence
    - **Property 3: SIMD and Scalar Path Equivalence**
    - **Validates: Requirements 3.1**
    - Generate random customer lists, solve with both paths
    - Compare distance matrices within 0.01% tolerance
    - _Requirements: 3.1, 3.4_
  
  - [ ]* 9.2 Write property test for route equivalence
    - **Property 5: Route Equivalence Across Paths**
    - **Validates: Requirements 4.5**
    - Generate random customer lists and capacities
    - Solve with use_simd=true and use_simd=false
    - Compare total route distances within 0.1% tolerance
    - _Requirements: 4.5_
  
  - [ ]* 9.3 Write unit test for AVX2 fallback behavior
    - Test that use_simd=true on non-AVX2 system falls back gracefully
    - Verify no crashes or errors when AVX2 unavailable
    - _Requirements: 4.4, 6.2, 6.4_

- [ ] 10. Add performance benchmarking tests
  - [ ]* 10.1 Create benchmark test file
    - Create tests/test_avx2_benchmarks.py
    - Implement benchmark for 100 customers comparing SIMD vs scalar
    - Implement benchmark for 1000 customers comparing SIMD vs scalar
    - Print speedup ratios (informational, not assertions)
    - _Requirements: 7.1, 7.2, 7.3_

- [x] 11. Final checkpoint and documentation
  - [x] 11.1 Verify all existing tests still pass
    - Run tests/test_solver.py to ensure no regressions
    - Run tests/test_fixes.py to ensure backward compatibility
    - _Requirements: 7.4_
  
  - [x] 11.2 Add code comments for SIMD operations
    - Document AVX2 intrinsics with explanatory comments
    - Add function-level documentation for new methods
    - _Requirements: 8.1, 8.2_
  
  - [x] 11.3 Final checkpoint
    - Ensure all property tests pass with 100+ iterations
    - Verify compilation with CMake in Release mode
    - Ask the user if questions arise

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property tests validate universal correctness across randomized inputs
- Unit tests validate specific examples and API behavior
- Checkpoints ensure incremental validation at key milestones
- The SIMD implementation maintains backward compatibility with existing code
- Performance benchmarks are informational and should not block CI/CD
