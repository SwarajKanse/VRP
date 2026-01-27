# Requirements Document: Realistic Data & Physics Upgrade

## Introduction

This feature transforms the VRP solver system into a professional logistics tool by adding realistic data ingestion, vehicle-specific fuel economics, physics-compliant LIFO packing, and comprehensive driver manifests. The system will handle detailed CSV manifests with package constraints, track precise fuel costs per vehicle type, implement Last-In-First-Out packing to ensure delivery accessibility, and generate professional driver instructions.

## Glossary

- **System**: The complete VRP solver application including C++ core and Python dashboard
- **CSV_Parser**: Component responsible for reading and validating CSV manifest files
- **Fleet_Composer**: Component that manages vehicle fleet configuration including fuel efficiency
- **Financial_Engine**: Component that calculates route costs including fuel and labor
- **Packing_Engine**: Component that arranges packages in vehicle cargo space
- **Driver_Manifest**: Document listing delivery instructions in route order
- **Fragile_Constraint**: A rule preventing other packages from being stacked on top of a package
- **Orientation_Lock**: A rule forcing a package to remain upright (Z-axis fixed)
- **LIFO_Loading**: Last-In-First-Out loading strategy where the last delivery is loaded first (at the back) and the first delivery is loaded last (at the door)
- **Depot**: The default pickup location when no source is specified

## Requirements

### Requirement 1: Professional CSV Manifest Ingestion

**User Story:** As a logistics planner, I want to upload detailed order data including handling constraints, so that I can plan routes with complete package information.

#### Acceptance Criteria

1. THE CSV_Parser SHALL accept columns: `Order ID`, `Source Name`, `Destination Name`, `Latitude`, `Longitude`, `Length (cm)`, `Width (cm)`, `Height (cm)`, `Weight (kg)`, `Fragile`, `This Side Up`
2. THE CSV_Parser SHALL validate that `Latitude` values are between -90 and 90 degrees
3. THE CSV_Parser SHALL validate that `Longitude` values are between -180 and 180 degrees
4. THE CSV_Parser SHALL validate that `Length (cm)`, `Width (cm)`, `Height (cm)` are positive numbers greater than zero
5. THE CSV_Parser SHALL validate that `Weight (kg)` is a positive number greater than zero
6. THE CSV_Parser SHALL convert dimension values from centimeters to meters
7. THE CSV_Parser SHALL accept `Fragile` column values as "Yes" or "No" (case-insensitive)
8. THE CSV_Parser SHALL accept `This Side Up` column values as "Yes" or "No" (case-insensitive)
9. WHEN `Fragile` column is missing, THE CSV_Parser SHALL default the value to "No"
10. WHEN `This Side Up` column is missing, THE CSV_Parser SHALL default the value to "No"
11. WHEN required columns are missing, THE CSV_Parser SHALL return a descriptive error message listing the missing columns
12. WHEN a CSV row contains invalid numeric values, THE CSV_Parser SHALL return an error identifying the row number and invalid field
13. THE System SHALL aggregate package weights per destination for the VRP Solver
14. THE System SHALL preserve individual package details for the Packing_Engine

### Requirement 2: Vehicle-Specific Fuel Economics

**User Story:** As a fleet owner, I want precise cost tracking per vehicle type, so that I can accurately calculate operational expenses.

#### Acceptance Criteria

1. THE Fleet_Composer SHALL accept "Fuel Efficiency (km/L)" as a parameter for each vehicle type
2. THE Financial_Engine SHALL calculate fuel cost using the formula: (route_distance_km / vehicle_fuel_efficiency_km_per_L) * fuel_price_per_L
3. THE Financial_Engine SHALL calculate labor cost using the formula: route_time_hours * driver_hourly_wage
4. THE Financial_Engine SHALL calculate total route cost as: fuel_cost + labor_cost
5. THE Financial_Engine SHALL use the specific fuel efficiency of the assigned vehicle for each route calculation
6. WHEN displaying route costs, THE Financial_Engine SHALL show vehicle-specific fuel consumption in liters
7. WHEN generating financial reports, THE System SHALL include a breakdown showing fuel efficiency per vehicle type
8. THE Dashboard SHALL display calculated "Fuel Consumed (Liters)" for each route

### Requirement 3: Physics-Compliant LIFO Packing

**User Story:** As a delivery driver, I want the first delivery to be accessible near the door, so that I don't have to unload and reload packages to reach it.

#### Acceptance Criteria

1. THE Packing_Engine SHALL use coordinate system where (0,0,0) is the back-bottom-left corner and the door is at maximum X
2. THE Packing_Engine SHALL sort packages by reverse stop order as primary sort (last delivery first)
3. THE Packing_Engine SHALL sort packages by volume (largest to smallest) as secondary sort within the same stop
4. THE Packing_Engine SHALL place packages from minimum X (back) toward maximum X (door)
5. WHEN a package has `Fragile=Yes`, THE Packing_Engine SHALL NOT place any other package on top of it
6. WHEN a package has `This Side Up=Yes`, THE Packing_Engine SHALL NOT rotate the package in X or Y dimensions
7. THE Packing_Engine SHALL ensure packages are placed on stable surfaces (floor or other packages)
8. THE Packing_Engine SHALL verify that a package is placed on a solid surface covering at least 60% of its base area
9. WHEN a fragile package cannot be placed without violating stacking constraints, THE Packing_Engine SHALL attempt alternative positions before rejecting the placement
10. THE Visualization SHALL render the back wall of the truck at X=0 and display packages growing toward the door (increasing X)

### Requirement 4: Comprehensive Driver Manifest

**User Story:** As a delivery driver, I want clear delivery instructions with handling requirements, so that I can execute the route efficiently and safely.

#### Acceptance Criteria

1. THE System SHALL generate a Driver_Manifest listing stops in route order (1, 2, 3...)
2. THE Driver_Manifest SHALL display `Source Name` (pickup location) for every package
3. THE Driver_Manifest SHALL display `Destination Name` (delivery location) for every stop
4. WHEN no `Source Name` is specified in the input CSV, THE System SHALL default to "Depot" in the manifest
5. THE Driver_Manifest SHALL include package dimensions (length, width, height) for each item
6. THE Driver_Manifest SHALL include package weight for each item
7. WHEN a package is marked `Fragile=Yes`, THE Driver_Manifest SHALL display "⚠️ FRAGILE" next to the item
8. WHEN a package is marked `This Side Up=Yes`, THE Driver_Manifest SHALL display "⬆️ THIS SIDE UP" next to the item
9. THE System SHALL generate downloadable Driver_Manifest in CSV format
10. THE System SHALL generate downloadable Driver_Manifest in PDF format
11. WHEN exporting to PDF format, THE Driver_Manifest SHALL display pickup and destination locations prominently for each stop
12. WHEN exporting to CSV format, THE Driver_Manifest SHALL include `Source Name` and `Destination Name` as dedicated columns