# Requirements Document

## Introduction

This document specifies the requirements for a high-performance Vehicle Routing Problem (VRP) solver foundation built in C++20 with Python bindings. The system is designed for high-frequency trading style performance, implementing basic Capacitated VRP (CVRP) and VRP with Time Windows (VRPTW) capabilities. This is the foundational task that establishes the project structure, core data models, a Nearest Neighbor heuristic solver, and Nanobind integration for Python interoperability.

## Glossary

- **VRP_Solver**: The C++ class responsible for solving vehicle routing problems
- **Nanobind_Module**: The Python extension module named `vrp_core` that exposes C++ functionality
- **Location**: A geographic coordinate represented by latitude and longitude
- **Customer**: An entity with delivery demand and time window constraints
- **Route**: An ordered sequence of customer visits for a single vehicle
- **Distance_Matrix**: A precomputed matrix of distances between all locations
- **Haversine_Distance**: A formula for calculating great-circle distance between two points on a sphere
- **Nearest_Neighbor_Heuristic**: A greedy algorithm that constructs routes by repeatedly visiting the closest unvisited customer
- **Build_System**: The CMake-based compilation and linking infrastructure
- **Time_Window**: A start and end time constraint for customer service

## Requirements

### Requirement 1: Project Build Infrastructure

**User Story:** As a developer, I want a CMake-based C++20 build system with Nanobind integration, so that I can compile the VRP solver and create Python bindings.

#### Acceptance Criteria

1. THE Build_System SHALL compile all C++ source files using the C++20 standard
2. WHEN CMake is invoked, THE Build_System SHALL locate and link the Nanobind library
3. WHEN the build completes successfully, THE Build_System SHALL produce a Python extension module named `vrp_core`
4. THE Build_System SHALL support compilation on standard development environments with CMake 3.15 or higher
5. WHEN the Python extension is built, THE Nanobind_Module SHALL be importable from Python

### Requirement 2: Core Data Structures

**User Story:** As a developer, I want well-defined data structures for locations and customers, so that I can represent VRP problem instances.

#### Acceptance Criteria

1. THE Location SHALL store latitude and longitude as floating-point coordinates
2. THE Customer SHALL store an integer identifier, a demand value, and time window bounds (start_window, end_window)
3. WHEN a Location is created with valid coordinates, THE Location SHALL preserve those coordinate values
4. WHEN a Customer is created with valid parameters, THE Customer SHALL preserve the identifier, demand, and time window values
5. THE Location SHALL support equality comparison between two Location instances

**Note:** While we strictly use a Customer struct for Phase 1, the architecture must allow for a future refactor to Data-Oriented Design (Struct of Arrays) for SIMD optimization.

### Requirement 3: Distance Calculation

**User Story:** As a developer, I want to calculate distances between locations using the Haversine formula, so that I can build a distance matrix for routing decisions.

#### Acceptance Criteria

1. WHEN two Location instances are provided, THE VRP_Solver SHALL calculate the great-circle distance using the Haversine formula
2. THE Haversine_Distance calculation SHALL return distance in kilometers
3. WHEN the Distance_Matrix is computed, THE VRP_Solver SHALL store distances between all customer locations
4. THE Distance_Matrix SHALL be symmetric (distance from A to B equals distance from B to A)
5. WHEN a location is compared to itself, THE Haversine_Distance SHALL return zero

### Requirement 4: VRP Solver Implementation

**User Story:** As a user, I want to solve vehicle routing problems with capacity and time window constraints, so that I can generate efficient delivery routes.

#### Acceptance Criteria

1. THE VRP_Solver SHALL accept a list of Customer instances and a vehicle capacity parameter
2. WHEN the solve method is invoked, THE VRP_Solver SHALL return a list of Route instances
3. THE VRP_Solver SHALL use the Nearest Neighbor heuristic to construct initial routes
4. WHEN constructing routes, THE VRP_Solver SHALL respect vehicle capacity constraints (sum of customer demands does not exceed capacity)
5. WHEN constructing routes, THE VRP_Solver SHALL respect customer time window constraints
6. WHEN all customers cannot be served, THE VRP_Solver SHALL return a partial solution with unserved customers identified
7. THE VRP_Solver SHALL compute the Distance_Matrix before route construction

### Requirement 5: Nearest Neighbor Heuristic

**User Story:** As a developer, I want a Nearest Neighbor heuristic implementation, so that I can quickly generate feasible initial solutions.

#### Acceptance Criteria

1. WHEN starting a new route, THE Nearest_Neighbor_Heuristic SHALL begin from a depot location (customer 0)
2. WHEN selecting the next customer, THE Nearest_Neighbor_Heuristic SHALL choose the closest unvisited customer that satisfies capacity and time window constraints
3. WHEN no feasible customer can be added to the current route, THE Nearest_Neighbor_Heuristic SHALL start a new route
4. WHEN all customers are visited or no more feasible routes exist, THE Nearest_Neighbor_Heuristic SHALL terminate
5. THE Nearest_Neighbor_Heuristic SHALL return routes in the order they were constructed

### Requirement 6: Python Bindings via Nanobind

**User Story:** As a Python developer, I want to use the VRP solver from Python, so that I can integrate it into Python-based applications.

#### Acceptance Criteria

1. THE Nanobind_Module SHALL expose the Location struct to Python with readable latitude and longitude attributes
2. THE Nanobind_Module SHALL expose the Customer struct to Python with readable id, demand, start_window, and end_window attributes
3. THE Nanobind_Module SHALL expose the VRP_Solver class to Python with a callable solve method
4. WHEN Python code calls VRP_Solver.solve(), THE Nanobind_Module SHALL accept a Python list of Customer objects and an integer capacity
5. WHEN VRP_Solver.solve() completes, THE Nanobind_Module SHALL return a Python list of routes (each route is a list of customer IDs)
6. THE Nanobind_Module SHALL be named `vrp_core` and importable via `import vrp_core`

### Requirement 7: Testing Infrastructure

**User Story:** As a developer, I want automated tests for the VRP solver, so that I can verify correctness and prevent regressions.

#### Acceptance Criteria

1. THE Build_System SHALL support running Python-based tests
2. WHEN tests are executed, THE Build_System SHALL verify that the vrp_core module can be imported
3. WHEN tests are executed, THE Build_System SHALL verify that VRP_Solver.solve() returns valid routes
4. WHEN tests are executed, THE Build_System SHALL verify that capacity constraints are respected
5. WHEN tests are executed, THE Build_System SHALL verify that time window constraints are respected

### Requirement 8: Performance Considerations

**User Story:** As a system architect, I want the solver to be designed for high-performance execution, so that it can handle large-scale routing problems efficiently.

#### Acceptance Criteria

1. THE VRP_Solver SHALL precompute the Distance_Matrix once per solve invocation
2. THE VRP_Solver SHALL use efficient data structures for customer lookup and route construction
3. THE VRP_Solver SHALL minimize memory allocations during route construction
4. WHEN using Nanobind bindings, THE VRP_Solver SHALL minimize Python-C++ boundary crossings
5. THE VRP_Solver SHALL be structured to allow replacing standard memory allocators with a Linear/Arena allocator in future iterations
