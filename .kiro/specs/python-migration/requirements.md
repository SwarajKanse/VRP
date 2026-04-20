# Requirements Document

## Introduction

This feature migrates the VRP (Vehicle Routing Problem) solver from a C++20/Nanobind architecture to a pure Python implementation. The current system has a C++ core (`solver.cpp`, `solver.h`, `bindings.cpp`) compiled into a platform-specific extension (`vrp_core.pyd`/`vrp_core.so`) and exposed to Python via Nanobind. The migration replaces all C/C++ code with a native Python module (`vrp_core.py`) that preserves the exact same public API, so the Streamlit dashboard and all existing Python tests continue to work without modification to their import statements or call sites.

After migration: no CMake, no Nanobind, no compiled extensions, no `.pyd`/`.so` files, and no C/C++ source files are required to run the solver or the dashboard.

## Glossary

- **VRP_Solver**: The Python class `VRPSolver` inside `vrp_core.py` that implements the nearest-neighbor heuristic for the Vehicle Routing Problem.
- **Location**: A Python dataclass representing a geographic coordinate pair (latitude, longitude).
- **Customer**: A Python dataclass representing a delivery stop with demand, time windows, and service time.
- **Route**: A Python `list[int]` of customer IDs representing a single vehicle's delivery sequence, starting and ending at the depot (ID 0).
- **Depot**: The starting and ending point for all routes, always represented as the customer with `id == 0`.
- **Distance_Matrix**: An N×N matrix of Euclidean distances between all customer pairs, computed in pure Python.
- **Time_Matrix**: An optional N×N matrix of travel times in minutes provided by the caller; when absent the solver derives travel time from the Distance_Matrix.
- **Nearest_Neighbor_Heuristic**: The greedy route-construction algorithm that repeatedly selects the closest feasible unvisited customer.
- **Haversine_Distance**: The great-circle distance formula used by the dashboard to build the Time_Matrix before calling the solver.
- **vrp_core**: The Python module (`vrp_core.py`) that replaces the compiled C++ extension and exposes `Location`, `Customer`, and `VRPSolver`.
- **Dashboard**: The Streamlit application in `dashboard/app.py` that imports `vrp_core` and drives the user interface.

---

## Requirements

### Requirement 1: Pure Python `vrp_core` Module

**User Story:** As a developer, I want a pure Python `vrp_core` module, so that the solver can be imported and used on any platform without compiling C++ code or installing build tools.

#### Acceptance Criteria

1. THE `vrp_core` module SHALL be implemented as a single Python file `vrp_core.py` located in the project root directory.
2. THE `vrp_core` module SHALL expose the classes `Location`, `Customer`, and `VRPSolver` at the module's top level.
3. WHEN `import vrp_core` is executed in any Python file, THE `vrp_core` module SHALL import successfully without requiring CMake, Nanobind, a C++ compiler, or any compiled extension file.
4. THE `vrp_core` module SHALL NOT import or depend on any C extension, `.pyd` file, or `.so` file.
5. WHERE the project previously required `nanobind>=1.0.0` in `requirements.txt`, THE `requirements.txt` file SHALL no longer list `nanobind` as a dependency.

---

### Requirement 2: `Location` Data Class

**User Story:** As a developer, I want a `Location` class with `latitude` and `longitude` attributes, so that geographic coordinates can be stored and compared using the same interface as before.

#### Acceptance Criteria

1. THE `Location` class SHALL accept two positional constructor arguments: `latitude` (float) and `longitude` (float).
2. THE `Location` class SHALL expose a readable and writable `latitude` attribute that returns the value passed to the constructor.
3. THE `Location` class SHALL expose a readable and writable `longitude` attribute that returns the value passed to the constructor.
4. WHEN two `Location` instances are compared with `==`, THE `Location` class SHALL return `True` if and only if both `latitude` and `longitude` are equal.
5. FOR ALL valid float values of `latitude` in `[-90.0, 90.0]` and `longitude` in `[-180.0, 180.0]`, creating a `Location` and reading back its attributes SHALL return the exact same values that were provided (value-preservation property).

---

### Requirement 3: `Customer` Data Class

**User Story:** As a developer, I want a `Customer` class with all delivery-stop attributes, so that customer data can be stored and passed to the solver using the same interface as before.

#### Acceptance Criteria

1. THE `Customer` class SHALL accept the following positional constructor arguments in order: `id` (int), `location` (Location), `demand` (float), `start_window` (float), `end_window` (float).
2. THE `Customer` class SHALL accept an optional sixth positional argument `service_time` (float) that defaults to `0.0` when omitted.
3. THE `Customer` class SHALL expose readable and writable attributes `id`, `location`, `demand`, `start_window`, `end_window`, and `service_time`.
4. FOR ALL valid constructor inputs, creating a `Customer` and reading back each attribute SHALL return the exact same value that was provided (value-preservation property).
5. WHEN a `Customer` is created without a `service_time` argument, THE `Customer` class SHALL set `service_time` to `0.0`.

---

### Requirement 4: `VRPSolver` Class Interface

**User Story:** As a developer, I want a `VRPSolver` class with a `solve()` method that accepts the same arguments as the C++ version, so that all existing call sites work without modification.

#### Acceptance Criteria

1. THE `VRPSolver` class SHALL be instantiable with no constructor arguments.
2. THE `VRPSolver.solve()` method SHALL accept the following arguments: `customers` (list of `Customer`), `vehicle_capacities` (list of float), `use_simd` (bool, default `True`), `time_matrix` (list of list of float, default empty list).
3. THE `VRPSolver.solve()` method SHALL return a `list` of `Route` objects, where each `Route` is a `list[int]`.
4. WHEN `vehicle_capacities` is an empty list, THE `VRPSolver.solve()` method SHALL raise a `ValueError`.
5. WHEN any value in `vehicle_capacities` is less than or equal to zero, THE `VRPSolver.solve()` method SHALL raise a `ValueError`.
6. WHEN `customers` is an empty list or contains only the depot, THE `VRPSolver.solve()` method SHALL return an empty list.
7. THE `use_simd` parameter SHALL be accepted and silently ignored, since pure Python has no SIMD paths; its presence preserves backward compatibility with existing call sites.

---

### Requirement 5: Distance Matrix Construction

**User Story:** As a developer, I want the solver to build an internal Euclidean distance matrix in pure Python, so that route distances can be computed without any compiled code.

#### Acceptance Criteria

1. THE `VRP_Solver` SHALL compute an N×N distance matrix before running the nearest-neighbor heuristic, where N is the number of customers including the depot.
2. WHEN computing the distance between customer `i` and customer `j`, THE `VRP_Solver` SHALL use the Euclidean formula: `sqrt((lat2 - lat1)^2 + (lon2 - lon1)^2)`.
3. THE `VRP_Solver` SHALL set all diagonal entries `distance_matrix[i][i]` to `0.0`.
4. THE Distance_Matrix SHALL be symmetric: `distance_matrix[i][j] == distance_matrix[j][i]` for all valid `i` and `j`.
5. FOR ALL pairs of customers with identical coordinates, THE `VRP_Solver` SHALL compute a distance of `0.0`.

---

### Requirement 6: Travel Time Calculation

**User Story:** As a developer, I want the solver to derive travel time from either a provided time matrix or the distance matrix, so that time-window constraints can be evaluated correctly.

#### Acceptance Criteria

1. WHEN a non-empty `time_matrix` is provided to `solve()`, THE `VRP_Solver` SHALL use `time_matrix[from_idx][to_idx]` as the travel time in minutes between any two customers.
2. WHEN `time_matrix` is empty or not provided, THE `VRP_Solver` SHALL compute travel time as `distance_matrix[from_idx][to_idx] * 1.5` (assuming 40 km/h average speed).
3. WHEN a non-empty `time_matrix` is provided, THE `VRP_Solver` SHALL validate that its dimensions are N×N, where N equals the number of customers; IF the dimensions do not match, THEN THE `VRP_Solver` SHALL raise a `ValueError`.

---

### Requirement 7: Nearest-Neighbor Heuristic

**User Story:** As a developer, I want the solver to implement the nearest-neighbor heuristic with capacity and time-window constraints, so that feasible delivery routes are generated for a heterogeneous fleet.

#### Acceptance Criteria

1. THE `VRP_Solver` SHALL construct routes by iteratively selecting the nearest unvisited customer that satisfies both the capacity constraint and the time-window constraint.
2. WHEN building a route, THE `VRP_Solver` SHALL start each route at the depot (customer index 0) and return to the depot after the last customer.
3. THE `VRP_Solver` SHALL assign routes to vehicles in the order they appear in `vehicle_capacities`; the first route uses `vehicle_capacities[0]`, the second uses `vehicle_capacities[1]`, and so on.
4. WHEN no feasible customer can be added to the current route, THE `VRP_Solver` SHALL close the current route and begin a new one with the next vehicle, if any remain.
5. WHEN all vehicles have been used or all customers have been assigned, THE `VRP_Solver` SHALL stop and return the completed routes.
6. THE number of routes returned SHALL NOT exceed the number of vehicles in `vehicle_capacities`.

---

### Requirement 8: Capacity Constraint Enforcement

**User Story:** As a developer, I want the solver to enforce vehicle capacity constraints on every route, so that no vehicle is overloaded.

#### Acceptance Criteria

1. WHEN evaluating whether a customer can be added to a route, THE `VRP_Solver` SHALL check that the sum of demands of all customers already in the route plus the candidate customer's demand does not exceed the vehicle's capacity.
2. FOR ALL routes returned by `solve()`, the sum of customer demands in each route SHALL NOT exceed the capacity of the vehicle assigned to that route.
3. THE `VRP_Solver` SHALL skip the depot (customer ID 0) when summing demands for a route.

---

### Requirement 9: Time-Window Constraint Enforcement

**User Story:** As a developer, I want the solver to enforce time-window constraints, so that no customer is visited after their delivery window closes.

#### Acceptance Criteria

1. WHEN evaluating whether a customer can be added to a route, THE `VRP_Solver` SHALL check that the computed arrival time at that customer does not exceed the customer's `end_window`.
2. WHEN the solver arrives at a customer before `start_window`, THE `VRP_Solver` SHALL add a waiting time equal to `start_window - arrival_time` before departing.
3. THE current time after visiting a customer SHALL be computed as: `arrival_time + max(0, start_window - arrival_time) + service_time`.
4. FOR ALL routes returned by `solve()`, the arrival time at each customer SHALL NOT exceed that customer's `end_window`.

---

### Requirement 10: Haversine Distance Utility

**User Story:** As a developer, I want a `haversine_distance` utility available in the codebase, so that the dashboard can compute geographic travel times for the time matrix without depending on the C++ solver.

#### Acceptance Criteria

1. THE `vrp_core` module SHALL expose a `haversine_distance(lat1, lon1, lat2, lon2)` function that returns the great-circle distance in kilometers.
2. WHEN `lat1 == lat2` and `lon1 == lon2`, THE `haversine_distance` function SHALL return `0.0`.
3. THE `haversine_distance` function SHALL use Earth's radius of `6371.0` km.
4. THE `haversine_distance` function SHALL use the formula: `2 * R * arctan2(sqrt(a), sqrt(1-a))` where `a = sin(dlat/2)^2 + cos(lat1) * cos(lat2) * sin(dlon/2)^2`.
5. FOR ALL valid coordinate pairs, `haversine_distance(lat1, lon1, lat2, lon2)` SHALL equal `haversine_distance(lat2, lon2, lat1, lon1)` (symmetry property).

---

### Requirement 11: Dashboard Compatibility

**User Story:** As a developer, I want the Streamlit dashboard to continue working after the migration, so that end users experience no change in functionality.

#### Acceptance Criteria

1. WHEN `dashboard/app.py` executes `import vrp_core`, THE import SHALL succeed using the new pure Python module.
2. THE `dashboard/app.py` file SHALL NOT require the Windows DLL path setup block (`os.add_dll_directory`) after migration, since no compiled extension is loaded.
3. THE `dashboard/app.py` SHALL continue to call `vrp_core.Location`, `vrp_core.Customer`, and `vrp_core.VRPSolver` with the same arguments as before the migration.
4. WHEN the dashboard calls `solver.solve(customers, vehicle_capacities, use_simd, time_matrix)`, THE `VRP_Solver` SHALL return routes in the same format as the C++ implementation.
5. THE `dataframe_to_customers()` function in `dashboard/app.py` SHALL continue to work without modification after the migration.
6. THE `dashboard/app.py` SHALL be able to call `vrp_core.haversine_distance()` to compute travel times for the time matrix generation.

---

### Requirement 12: Test Suite Compatibility

**User Story:** As a developer, I want all existing Python tests to pass after the migration, so that correctness is verified without rewriting the test suite.

#### Acceptance Criteria

1. WHEN `pytest tests/` is executed after migration, THE test suite SHALL pass all tests that previously passed when the C++ extension was available.
2. THE `tests/test_solver.py` file SHALL no longer require the `os.add_dll_directory` DLL-loading block, since no compiled extension is loaded.
3. WHEN `tests/test_solver.py` imports `vrp_core`, THE import SHALL succeed without the `pytest.skip` fallback that was previously needed when the `.pyd` file was missing.
4. THE property-based tests in `tests/test_solver.py` that use `hypothesis` SHALL continue to pass with the pure Python implementation.

---

### Requirement 13: Removal of C/C++ Build Artifacts

**User Story:** As a developer, I want all C/C++ source files, build configuration, and compiled artifacts removed from the project, so that the repository contains only Python code and no build toolchain is required.

#### Acceptance Criteria

1. THE `src/` directory containing `solver.cpp`, `bindings.cpp`, `main.cpp`, and all `test_*.cpp` files SHALL be removed from the project.
2. THE `include/` directory containing `solver.h` SHALL be removed from the project.
3. THE `CMakeLists.txt` file SHALL be removed from the project.
4. THE `setup.py` file SHALL be replaced with a simplified version that only installs Python dependencies (no CMake invocation, no C++ compilation step).
5. THE `build/` directory and any `.pyd` or `.so` compiled extension files SHALL be removed from the project.
6. THE `requirements.txt` file SHALL be updated to remove `nanobind` and retain only the Python-only dependencies: `pytest`, `hypothesis`, `streamlit`, `pandas`, `numpy`, `plotly`, `pydeck`, `requests`, and `reportlab`.
7. THE `.gitignore` file SHALL be updated to remove C++ build artifact patterns (`build/`, `*.pyd`, `*.so`, `*.o`, `*.obj`) since they are no longer relevant.

---

### Requirement 14: Parser and Serializer Round-Trip

**User Story:** As a developer, I want the CSV parsing and customer data conversion to be verifiable end-to-end, so that data integrity is maintained throughout the pipeline.

#### Acceptance Criteria

1. WHEN a `Customer` object is created from a DataFrame row by `dataframe_to_customers()`, THE resulting `Customer` SHALL have attribute values that exactly match the source row's numeric fields.
2. FOR ALL valid `Customer` objects created by `dataframe_to_customers()`, converting the same DataFrame row twice SHALL produce `Customer` objects with identical attribute values (idempotence property).
3. THE `CSVParser` in `dashboard/csv_parser.py` SHALL continue to parse manifest CSV files and return `Destination` objects without modification after the migration.

---

### Requirement 15: Documentation and Setup Script Updates

**User Story:** As a developer, I want all documentation and setup scripts updated to reflect the pure Python architecture, so that new users can get started without confusion about build requirements.

#### Acceptance Criteria

1. THE `README.md` file SHALL be updated to remove all references to CMake, C++ compilers, Nanobind, and build instructions.
2. THE `README.md` file SHALL document that the project is now pure Python and requires only `pip install -r requirements.txt` to set up.
3. THE `QUICKSTART.md` file SHALL be updated to remove build steps and simplify the getting started instructions to Python-only workflows.
4. THE `setup.bat` and `setup.sh` scripts SHALL be updated to remove CMake build commands and only install Python dependencies via pip.
5. WHERE documentation previously mentioned "C++ core" or "compiled extension", THE documentation SHALL be updated to refer to "Python implementation" or "pure Python solver".
6. THE `GETTING_STARTED.txt` file SHALL be updated to remove references to Visual C++ Redistributable, MinGW, or other C++ runtime requirements.

---

### Requirement 16: Workspace Configuration Updates

**User Story:** As a developer, I want workspace configuration files updated to reflect the new pure Python architecture, so that AI assistants and development tools have accurate context.

#### Acceptance Criteria

1. THE `.kiro/steering/tech.md` file SHALL be updated to remove references to C++20, CMake, Nanobind, and C++ build commands.
2. THE `.kiro/steering/tech.md` file SHALL document that the project uses pure Python 3.8+ with standard library and common packages.
3. THE `.kiro/steering/structure.md` file SHALL be updated to remove references to `include/`, `src/`, `build/`, and C++ source files.
4. THE `.kiro/steering/structure.md` file SHALL document the new structure with `vrp_core.py` in the project root.
5. THE `.kiro/steering/product.md` file SHALL be updated to remove references to "C++20", "Nanobind", and "high-performance" claims that were specific to the compiled implementation.
6. THE `.kiro/steering/DLL Issue.md` file SHALL be removed or marked as obsolete, since DLL loading is no longer relevant for pure Python.


---

### Requirement 17: Installation Verification Script Updates

**User Story:** As a developer, I want the installation verification script updated to test pure Python imports, so that users can verify their setup without build tools.

#### Acceptance Criteria

1. THE `test_installation.py` script SHALL be updated to remove all DLL loading code (`os.add_dll_directory` calls).
2. THE `test_installation.py` script SHALL verify that `import vrp_core` succeeds without requiring any build artifacts.
3. THE `test_installation.py` script SHALL test basic functionality by creating `Location`, `Customer`, and `VRPSolver` instances.
4. THE `test_installation.py` script SHALL remove troubleshooting messages about C++ compilers, Visual C++ Redistributable, and build directories.
5. WHEN `test_installation.py` runs successfully, THE script SHALL confirm that the pure Python implementation is working correctly.
