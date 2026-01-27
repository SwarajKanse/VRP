# Requirements Document: 3D Load Optimization (Bin Packing)

## Introduction

This feature adds a 3D visualization and validation layer to the VRP solver that ensures assigned packages physically fit inside vehicle cargo bays. The system converts abstract demand units into physical boxes with dimensions, applies a First-Fit Decreasing packing algorithm, and provides interactive 3D visualization of the loading plan. This enables fleet managers to validate not just weight capacity constraints, but also physical space constraints in their routing solutions.

## Glossary

- **Cargo_Bay**: The usable 3D space (Length × Width × Height in meters) inside a specific vehicle type
- **Package**: A physical box with 3D dimensions (length, width, height) corresponding to 1 unit of demand
- **Packing_Engine**: The algorithmic logic that determines (x, y, z) coordinates for each package within the cargo bay
- **First_Fit_Decreasing**: A heuristic algorithm that sorts items by volume (largest first) and places each item in the first available position
- **Overflow**: A condition where a package cannot be physically placed in the cargo bay despite meeting weight capacity constraints
- **Vehicle_Profile**: A configuration defining a vehicle type's characteristics including cargo bay dimensions and weight capacity
- **Demand_Unit**: An abstract quantity representing customer requirements, where 1 unit equals 1 physical package

## Requirements

### Requirement 1: Vehicle Cargo Bay Dimensions

**User Story:** As a fleet manager, I want to define the physical cargo bay dimensions of my vehicle types, so that I can validate whether packages will physically fit inside my trucks.

#### Acceptance Criteria

1. WHEN a user configures a vehicle profile in the Fleet Composer, THE System SHALL accept three dimensional inputs: Length (meters), Width (meters), and Height (meters)
2. WHEN dimensional inputs are not provided for a vehicle profile, THE System SHALL apply default dimensions based on vehicle type (e.g., Tempo = 2.5m × 1.5m × 1.5m)
3. WHEN dimensional inputs are provided, THE System SHALL validate that all values are positive numbers greater than zero
4. THE System SHALL store cargo bay dimensions as part of the vehicle profile configuration
5. WHEN a vehicle profile is saved, THE System SHALL persist the cargo bay dimensions for future routing sessions

### Requirement 2: Package Dimension Generation

**User Story:** As a system, I need to convert abstract demand units into physical packages with realistic dimensions, so that I can perform 3D packing validation.

#### Acceptance Criteria

1. THE System SHALL treat 1 demand unit as equivalent to 1 physical package
2. WHEN generating package dimensions, THE System SHALL create random dimensions within a configurable range (default: 0.3m to 0.8m per side)
3. WHEN generating package dimensions, THE System SHALL ensure each package has three dimensions: length, width, and height
4. THE System SHALL assign a unique color identifier to packages based on their destination customer ID
5. WHEN multiple packages share the same destination, THE System SHALL assign them the same color for visual grouping
6. THE System SHALL generate package dimensions deterministically when given the same random seed for reproducibility

### Requirement 3: First-Fit Decreasing Packing Algorithm

**User Story:** As a user, I want the system to efficiently pack boxes into the cargo bay using a proven algorithm, so that I can maximize space utilization and identify overflow conditions.

#### Acceptance Criteria

1. WHEN packing packages into a cargo bay, THE Packing_Engine SHALL sort packages by volume in descending order (largest first)
2. WHEN placing a package, THE Packing_Engine SHALL attempt to position it at the first available space starting from coordinates (0, 0, 0)
3. THE Packing_Engine SHALL ensure no two packages overlap in 3D space
4. WHEN a package cannot fit in the cargo bay, THE Packing_Engine SHALL mark it as "Overflow" status
5. THE Packing_Engine SHALL validate that each placed package remains fully within the cargo bay boundaries
6. WHEN calculating available space, THE Packing_Engine SHALL consider all previously placed packages
7. THE Packing_Engine SHALL assign (x, y, z) coordinates to each successfully placed package representing its bottom-front-left corner

### Requirement 4: 3D Visualization Interface

**User Story:** As a user, I want to view and interact with a 3D representation of the cargo loading plan, so that I can visually verify the packing solution and identify potential issues.

#### Acceptance Criteria

1. THE Dashboard SHALL provide a new section titled "📦 Cargo Loading Plan" for 3D visualization
2. WHEN rendering the cargo loading plan, THE System SHALL use Plotly graph_objects to create the 3D scene
3. THE Visualization SHALL display a wireframe box representing the vehicle's cargo bay boundaries
4. THE Visualization SHALL display solid cubes representing each placed package with their assigned colors
5. WHEN multiple vehicles exist in the solution, THE System SHALL provide a selector to toggle between different vehicles (e.g., "View Tempo #1", "View Tempo #2")
6. THE Visualization SHALL support interactive rotation, zoom, and pan controls via Plotly's default camera controls
7. WHEN a package is marked as "Overflow", THE Visualization SHALL display it in a distinct manner (e.g., red color, separate section)
8. THE Visualization SHALL display package dimensions and destination information on hover

### Requirement 5: Packing Validation and Reporting

**User Story:** As a fleet manager, I want to receive clear feedback about packing feasibility, so that I can identify routes that exceed physical capacity constraints.

#### Acceptance Criteria

1. WHEN a route is solved, THE System SHALL validate that all packages can physically fit in the assigned vehicle's cargo bay
2. WHEN overflow occurs, THE System SHALL report the number of packages that could not be packed
3. THE System SHALL calculate and display the cargo bay utilization percentage (used volume / total volume)
4. WHEN displaying route information, THE System SHALL indicate both weight capacity usage and volume capacity usage
5. THE System SHALL provide a summary showing: total packages assigned, packages successfully packed, overflow packages, and utilization percentage

### Requirement 6: Integration with Existing VRP Solver

**User Story:** As a developer, I want the 3D packing feature to integrate seamlessly with the existing VRP solver, so that routing and packing validation work together cohesively.

#### Acceptance Criteria

1. THE System SHALL perform 3D packing validation after route generation is complete
2. WHEN the VRP solver assigns customers to routes, THE System SHALL automatically trigger packing validation for each route
3. THE System SHALL maintain the existing VRP solver interface and behavior for users who do not enable 3D visualization
4. THE System SHALL allow users to enable or disable 3D packing validation via a configuration option
5. WHEN 3D packing is disabled, THE System SHALL fall back to weight-only capacity validation
