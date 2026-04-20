# Implementation Plan: Python Migration

## Overview

This plan migrates the VRP solver from C++20/Nanobind to pure Python by creating a new `vrp_core.py` module that replicates the exact API of the compiled extension. The migration eliminates all build complexity while maintaining full compatibility with the existing dashboard and test suite.

## Tasks

- [ ] 1. Create pure Python vrp_core module with data structures
  - Create `vrp_core.py` in project root
  - Implement `Location` dataclass with latitude/longitude attributes and validation
  - Implement `Customer` dataclass with id, location, demand, time windows, and service_time
  - Add `__post_init__` validation for coordinate ranges and constraint checks
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 3.3_

- [ ]* 1.1 Write property tests for Location and Customer dataclasses
  - **Property 1: Location value preservation** - For any valid lat/lon, Location round-trip preserves values
  - **Property 2: Customer value preservation** - For any valid customer data, Customer round-trip preserves values
  - **Property 3: Location equality reflexivity** - Location equals itself, different coordinates not equal
  - **Validates: Requirements 2.5, 3.4**

- [ ] 2. Implement VRPSolver class with distance matrix construction
  - Create `VRPSolver` class with `__init__()` method
  - Implement `solve()` method signature accepting customers, vehicle_capacities, use_simd, time_matrix
  - Implement `_build_distance_matrix()` private method using Euclidean formula
  - Implement `_euclidean_distance()` helper method
  - Add input validation for empty/invalid vehicle_capacities
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ]* 2.1 Write unit tests for distance matrix construction
  - Test symmetric matrix property
  - Test diagonal entries are zero
  - Test identical coordinates produce zero distance
  - _Requirements: 5.3, 5.4, 5.5_

- [ ] 3. Implement travel time calculation logic
  - Implement `_get_travel_time()` method with time_matrix prioritization
  - Add fallback to distance * 1.5 when time_matrix not provided
  - Add validation for time_matrix dimensions matching customer count
  - _Requirements: 6.1, 6.2, 6.3_

- [ ]* 3.1 Write unit tests for travel time calculation
  - Test time_matrix usage when provided
  - Test distance-based fallback calculation
  - Test dimension validation error handling
  - _Requirements: 6.1, 6.2, 6.3_

- [ ] 4. Checkpoint - Verify basic solver structure
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Implement constraint validation methods
  - Implement `_calculate_route_load()` method excluding depot from demand sum
  - Implement `_can_add_to_route()` method with capacity and time window checks
  - Add arrival time calculation with waiting time logic
  - _Requirements: 8.1, 8.2, 8.3, 9.1, 9.2, 9.3, 9.4_

- [ ]* 5.1 Write property test for capacity constraint enforcement
  - **Property 6: Route capacity constraint** - For any route, sum of demands ≤ vehicle capacity
  - **Validates: Requirements 8.2**

- [ ]* 5.2 Write unit tests for time window constraint enforcement
  - Test arrival time does not exceed end_window
  - Test waiting time calculation when arriving before start_window
  - Test current time update after service
  - _Requirements: 9.1, 9.2, 9.3, 9.4_

- [ ] 6. Implement nearest neighbor heuristic
  - Implement `_nearest_neighbor_heuristic()` method with greedy customer selection
  - Add visited tracking array initialization
  - Implement route construction loop with vehicle iteration
  - Add nearest feasible customer selection logic
  - Implement route state updates (load, time, location)
  - Add depot bookending (start and end at customer 0)
  - Handle early termination when no customers remain
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

- [ ]* 6.1 Write property tests for nearest neighbor heuristic
  - **Property 8: Routes start at depot** - For any route, first customer is depot (ID 0)
  - **Property 10: All customers visited or unserved** - No customer visited twice, all visited or explicitly unserved
  - **Validates: Requirements 7.2, 7.5**

- [ ]* 6.2 Write integration tests for complete solve() workflow
  - Test single vehicle scenario
  - Test multiple vehicles with different capacities
  - Test heterogeneous fleet routing
  - Test infeasible problem handling
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

- [ ] 7. Implement haversine distance utility function
  - Implement `haversine_distance(lat1, lon1, lat2, lon2)` function
  - Use Earth radius of 6371.0 km
  - Implement standard Haversine formula with arctan2
  - Add handling for identical coordinates (return 0.0)
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

- [ ]* 7.1 Write unit tests for haversine distance
  - Test self-distance is zero
  - Test symmetry property
  - Test known distance calculations
  - _Requirements: 10.2, 10.5_

- [ ] 8. Checkpoint - Verify complete vrp_core module functionality
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 9. Update dashboard for pure Python compatibility
  - Remove `os.add_dll_directory()` calls from `dashboard/app.py`
  - Remove Windows DLL path setup block
  - Verify `import vrp_core` works with pure Python module
  - Update `dataframe_to_customers()` to use `vrp_core.haversine_distance()` if needed
  - Remove DLL loading comments and Windows-specific workarounds
  - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6_

- [ ]* 9.1 Manually test dashboard functionality
  - Run dashboard and verify import succeeds
  - Test demo data loading
  - Test solve button functionality
  - Verify routes display on map
  - Verify financial metrics calculate correctly
  - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6_

- [ ] 10. Update test suite for pure Python compatibility
  - Remove `os.add_dll_directory()` calls from `tests/test_solver.py`
  - Remove `pytest.skip` fallback for missing .pyd file
  - Verify all existing unit tests pass with pure Python module
  - Verify all property-based tests pass with hypothesis
  - _Requirements: 12.1, 12.2, 12.3, 12.4_

- [ ] 11. Update test_installation.py script
  - Remove all DLL loading code (`os.add_dll_directory` calls)
  - Update to test pure Python import without build artifacts
  - Add basic functionality tests (Location, Customer, VRPSolver instantiation)
  - Remove troubleshooting messages about C++ compilers and build tools
  - Update success message to confirm pure Python implementation
  - _Requirements: 17.1, 17.2, 17.3, 17.4, 17.5_

- [ ] 12. Checkpoint - Verify all Python code updated and tests passing
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 13. Remove C++ source files and build artifacts
  - Delete `src/` directory (solver.cpp, bindings.cpp, main.cpp, test_*.cpp)
  - Delete `include/` directory (solver.h)
  - Delete `CMakeLists.txt`
  - Delete `build/` directory
  - Delete compiled extensions (vrp_core.pyd, vrp_core.so files)
  - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5_

- [ ] 14. Update build and dependency configuration
  - Update `requirements.txt` to remove nanobind dependency
  - Retain pytest, hypothesis, streamlit, pandas, numpy, plotly, pydeck, requests, reportlab
  - Update `setup.py` to remove CMake invocation and C++ compilation
  - Simplify `setup.py` to only install Python dependencies
  - Update `.gitignore` to remove C++ build artifact patterns (build/, *.pyd, *.so, *.o, *.obj)
  - _Requirements: 1.5, 13.6, 13.7_

- [ ] 15. Update setup scripts
  - Update `setup.bat` to remove CMake build commands
  - Update `setup.sh` to remove CMake build commands
  - Simplify both scripts to only run `pip install -r requirements.txt`
  - _Requirements: 15.4_

- [ ] 16. Update primary documentation files
  - Update `README.md` to remove CMake, C++ compiler, Nanobind references
  - Document pure Python architecture requiring only `pip install -r requirements.txt`
  - Update `QUICKSTART.md` to remove build steps and simplify to Python-only workflow
  - Update `GETTING_STARTED.txt` to remove Visual C++ Redistributable and MinGW references
  - Remove references to "C++ core" and "compiled extension", replace with "Python implementation"
  - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6_

- [ ] 17. Update workspace configuration files
  - Update `.kiro/steering/tech.md` to remove C++20, CMake, Nanobind references
  - Document pure Python 3.8+ with standard library in tech.md
  - Update `.kiro/steering/structure.md` to remove include/, src/, build/ references
  - Document new structure with vrp_core.py in project root in structure.md
  - Update `.kiro/steering/product.md` to remove C++20, Nanobind, and performance claims specific to compiled implementation
  - Remove or mark `.kiro/steering/DLL Issue.md` as obsolete
  - _Requirements: 16.1, 16.2, 16.3, 16.4, 16.5, 16.6_

- [ ] 18. Final verification and testing
  - Run `pytest tests/ -v` and verify all tests pass
  - Run `python dashboard/app.py` and verify dashboard works
  - Run `python test_installation.py` and verify installation check passes
  - Verify no import errors or missing dependencies
  - Verify CSV parsing and customer data conversion works end-to-end
  - _Requirements: 12.1, 12.2, 12.3, 12.4, 14.1, 14.2_

## Notes

- Tasks marked with `*` are optional testing tasks that can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at key milestones
- Property tests validate universal correctness properties from the design
- Unit tests validate specific examples and edge cases
- The migration prioritizes correctness and API compatibility over performance
- All existing dashboard and test code should work without modification after migration
