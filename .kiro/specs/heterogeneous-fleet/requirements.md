# Requirements Document: Heterogeneous Fleet

## Introduction

This feature upgrades the VRP Solver from a homogeneous fleet model (all vehicles identical) to a heterogeneous fleet model (mixed vehicle types). Users can define a fleet composed of different vehicle classes (e.g., Bikes, Vans, Trucks), each with distinct capacity constraints. To ensure optimal routing, the system prioritizes filling larger vehicles first by sorting the fleet by capacity in descending order.

## Glossary

- **Heterogeneous_Fleet**: A collection of vehicles with varying capacity constraints
- **Vehicle_Profile**: A specification defining a vehicle type's characteristics (name, capacity, quantity)
- **Fleet_Composer**: The UI component enabling users to add, remove, and configure vehicle profiles
- **Vehicle_Map**: A data structure tracking which route index corresponds to which vehicle type and instance
- **VRPSolver**: The core C++ solver component that generates routes
- **Dashboard**: The Python-based Dash web interface for user interaction

## Requirements

### Requirement 1: Fleet Configuration Interface

**User Story:** As a fleet manager, I want to define multiple vehicle types with different capacities and quantities, so that the solver can generate routes that match my actual fleet composition.

#### Acceptance Criteria

1. THE Dashboard SHALL replace the "Number of Vehicles" slider with a Fleet Configuration section
2. WHEN a user adds a vehicle profile, THE Fleet_Composer SHALL accept three inputs: vehicle name (string), capacity (positive number), and quantity (positive integer)
3. WHEN a user submits vehicle profiles, THE Dashboard SHALL validate that all capacities are positive numbers and all quantities are positive integers
4. WHEN vehicle profiles are defined, THE Dashboard SHALL calculate the total fleet size as the sum of all vehicle quantities
5. WHEN the solver is invoked, THE Dashboard SHALL convert the vehicle profiles into a flat list of capacities (e.g., [50, 50, 20, 20, 10] for 2 Trucks at 50, 2 Vans at 20, 1 Bike at 10)
6. THE Dashboard SHALL sort the capacity list in descending order (largest capacity first) before passing it to the solver

### Requirement 2: Core Solver Modification

**User Story:** As a developer, I want the solver to respect individual vehicle capacity constraints, so that routes are feasible for the actual vehicles in the fleet.

#### Acceptance Criteria

1. THE VRPSolver SHALL accept a vector of vehicle capacities instead of a single capacity value and vehicle count
2. WHEN constructing route i, THE VRPSolver SHALL use vehicle_capacities[i] as the capacity constraint for that route
3. WHEN a route is assigned to a vehicle, THE VRPSolver SHALL enforce that route's total demand does not exceed that vehicle's capacity
4. IF the route index exceeds the size of the vehicle_capacities vector, THE VRPSolver SHALL stop creating new routes
5. IF customers remain unassigned after all vehicles are used, THE VRPSolver SHALL return those customers in an unassigned list

### Requirement 3: Python Binding Updates

**User Story:** As a developer, I want to pass vehicle capacity data from Python to C++, so that the Dashboard can communicate fleet configuration to the solver.

#### Acceptance Criteria

1. THE Python bindings SHALL accept a list of floating-point numbers representing vehicle capacities
2. WHEN the bindings receive the capacity list, THE bindings SHALL convert it to a C++ std::vector<double>
3. THE bindings SHALL replace the old solve method signature (backward compatibility is not required)
4. WHEN the solver is called from Python, THE bindings SHALL pass the vehicle capacities vector to the C++ solve method

### Requirement 4: Route Visualization Enhancement

**User Story:** As a user, I want to see which vehicle type is assigned to each route, so that I can understand the fleet utilization and plan operations accordingly.

#### Acceptance Criteria

1. WHEN routes are displayed, THE Dashboard SHALL show the vehicle type name and capacity for each route
2. WHEN the route details table is rendered, THE Dashboard SHALL include a column displaying vehicle assignment (e.g., "Truck #1 - Cap 50")
3. WHEN multiple vehicles of the same type exist, THE Dashboard SHALL distinguish them by index (e.g., "Truck #1 - Cap 50", "Truck #2 - Cap 50")
4. THE Dashboard SHALL derive the vehicle name by mapping the route index back to the sorted fleet list
5. THE Dashboard SHALL display total fleet utilization as a percentage of total capacity used

### Requirement 5: Data Model Extension

**User Story:** As a developer, I want the solver to return vehicle assignment information, so that the Dashboard can display which vehicle serves which route.

#### Acceptance Criteria

1. THE VRPSolver SHALL return vehicle assignment data alongside route information
2. WHEN a route is generated, THE VRPSolver SHALL record which vehicle index (from the capacity vector) was assigned to that route
3. THE Python bindings SHALL expose vehicle assignment data to Python code
4. WHEN the Dashboard receives solver results, THE Dashboard SHALL have access to both routes and their corresponding vehicle assignments
