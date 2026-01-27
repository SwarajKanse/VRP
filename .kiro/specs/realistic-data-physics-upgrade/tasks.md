# Implementation Plan: Realistic Data & Physics Upgrade

## Overview

This implementation adds professional logistics capabilities to the VRP solver system. The work is organized into five phases: CSV parsing with validation, vehicle-specific fuel economics, LIFO packing with physics constraints, driver manifest generation, and dashboard integration. Each phase builds incrementally with testing to ensure correctness before proceeding.

## Tasks

- [x] 1. Set up project structure and dependencies
  - Create `dashboard/csv_parser.py` module
  - Create `dashboard/fleet_composer.py` module
  - Create `dashboard/financial_engine.py` module
  - Create `dashboard/manifest_builder.py` module
  - Add new dependencies to requirements: `pandas`, `reportlab`, `hypothesis`
  - Create `tests/test_csv_parser.py` for parser tests
  - Create `tests/test_financial_engine.py` for financial tests
  - Create `tests/test_packing_lifo.py` for packing tests
  - Create `tests/test_manifest_builder.py` for manifest tests
  - _Requirements: All requirements (foundation)_

- [x] 2. Implement CSV Parser with validation
  - [x] 2.1 Create Package and Destination dataclasses
    - Define `Package` dataclass with all fields (order_id, source_name, destination_name, coordinates, dimensions, weight, constraints)
    - Define `Destination` dataclass with aggregated data
    - Add volume calculation property to Package
    - _Requirements: 1.1_
  
  - [x] 2.2 Implement core CSV parsing logic
    - Write `parse_manifest()` method using pandas
    - Implement column validation (check for required columns)
    - Implement dimension conversion from cm to meters
    - Implement boolean parsing for Fragile and This Side Up columns
    - Handle missing optional columns with defaults
    - _Requirements: 1.1, 1.6, 1.7, 1.8, 1.9, 1.10_
  
  - [x] 2.3 Implement coordinate validation
    - Write `_validate_coordinates()` method
    - Check latitude range [-90, 90]
    - Check longitude range [-180, 180]
    - Return descriptive error messages with row numbers
    - _Requirements: 1.2, 1.3_
  
  - [x] 2.4 Implement dimension and weight validation
    - Write `_validate_dimensions()` method
    - Check all dimensions are positive and greater than zero
    - Check weight is positive and greater than zero
    - Return descriptive error messages with row numbers and field names
    - _Requirements: 1.4, 1.5, 1.12_
  
  - [x] 2.5 Implement destination aggregation
    - Group packages by destination name
    - Sum weights per destination for VRP solver
    - Preserve individual package details for packing engine
    - _Requirements: 1.13, 1.14_
  
  - [ ]* 2.6 Write property test for coordinate validation
    - **Property 2: Geographic coordinate validation**
    - **Validates: Requirements 1.2, 1.3**
    - Generate random coordinates inside and outside valid ranges
    - Verify parser accepts valid coordinates and rejects invalid ones
  
  - [ ]* 2.7 Write property test for dimension validation
    - **Property 3: Positive numeric validation**
    - **Validates: Requirements 1.4, 1.5**
    - Generate random positive and non-positive values
    - Verify parser rejects non-positive values with descriptive errors
  
  - [ ]* 2.8 Write property test for dimension conversion
    - **Property 4: Dimension conversion**
    - **Validates: Requirements 1.6**
    - Generate random dimension values in cm
    - Verify output values are correctly divided by 100
  
  - [ ]* 2.9 Write property test for weight aggregation
    - **Property 8: Weight aggregation by destination**
    - **Validates: Requirements 1.13**
    - Generate random packages with same destination
    - Verify aggregated weight equals sum of individual weights
  
  - [ ]* 2.10 Write unit tests for CSV parser edge cases
    - Test missing required columns error reporting
    - Test missing optional columns default to "No"
    - Test case-insensitive boolean parsing
    - Test invalid numeric values error reporting

- [x] 3. Checkpoint - CSV Parser validation
  - Run all CSV parser tests
  - Verify parser handles valid and invalid CSV files correctly
  - Ensure all tests pass, ask the user if questions arise

- [x] 4. Implement Fleet Composer with fuel efficiency
  - [x] 4.1 Create VehicleType dataclass with fuel efficiency
    - Define `VehicleType` dataclass
    - Add `fuel_efficiency_km_per_L` field
    - Preserve existing fields (capacity, dimensions, count)
    - _Requirements: 2.1_
  
  - [x] 4.2 Implement FleetComposer class
    - Write `add_vehicle_type()` method
    - Write `get_vehicle_by_name()` method
    - Store vehicle types in list
    - _Requirements: 2.1_
  
  - [ ]* 4.3 Write property test for vehicle storage
    - **Property 1: Valid column acceptance** (adapted for fleet)
    - **Validates: Requirements 2.1**
    - Generate random vehicle types with fuel efficiency
    - Verify all fields are stored and retrievable correctly

- [x] 5. Implement Financial Engine with vehicle-specific costs
  - [x] 5.1 Create RouteCost dataclass
    - Define `RouteCost` with all cost components
    - Include fuel_consumed_L, fuel_cost, labor_cost, total_cost
    - _Requirements: 2.2, 2.3, 2.4_
  
  - [x] 5.2 Implement cost calculation methods
    - Write `calculate_route_cost()` method
    - Implement fuel cost formula: (distance / efficiency) * price
    - Implement labor cost formula: time * wage
    - Implement total cost: fuel_cost + labor_cost
    - _Requirements: 2.2, 2.3, 2.4, 2.5_
  
  - [x] 5.3 Implement cost reporting
    - Write `generate_cost_summary()` method
    - Include fuel consumption in liters for each route
    - Include fuel efficiency breakdown per vehicle type
    - _Requirements: 2.6, 2.7, 2.8_
  
  - [ ]* 5.4 Write property test for fuel cost calculation
    - **Property 10: Fuel cost calculation**
    - **Validates: Requirements 2.2**
    - Generate random distance, efficiency, and price values
    - Verify formula: (distance / efficiency) * price
  
  - [ ]* 5.5 Write property test for labor cost calculation
    - **Property 11: Labor cost calculation**
    - **Validates: Requirements 2.3**
    - Generate random time and wage values
    - Verify formula: time * wage
  
  - [ ]* 5.6 Write property test for total cost composition
    - **Property 12: Total cost composition**
    - **Validates: Requirements 2.4**
    - Generate random route costs
    - Verify total equals fuel_cost + labor_cost
  
  - [ ]* 5.7 Write unit tests for financial engine edge cases
    - Test zero distance handling
    - Test very high fuel efficiency
    - Test cost summary with multiple vehicle types

- [x] 6. Checkpoint - Financial Engine validation
  - Run all financial engine tests
  - Verify cost calculations are accurate
  - Ensure all tests pass, ask the user if questions arise

- [x] 7. Implement LIFO Packing Engine with physics constraints
  - [x] 7.1 Create PlacedPackage and PackingResult dataclasses
    - Define `PlacedPackage` with position and dimensions
    - Define `PackingResult` with placed/failed packages and utilization
    - _Requirements: 3.1_
  
  - [x] 7.2 Implement LIFO sorting algorithm
    - Write `_sort_packages_lifo()` method
    - Primary sort: reverse stop order (last delivery first)
    - Secondary sort: volume descending within same stop
    - _Requirements: 3.2, 3.3_
  
  - [x] 7.3 Implement placement position finder
    - Write `_find_placement_position()` method
    - Search from X=0 (back) toward X=max (door)
    - Try different positions and orientations
    - Return first valid position or None
    - _Requirements: 3.4_
  
  - [x] 7.4 Implement fragile constraint checker
    - Write `_check_fragile_constraint()` method
    - Verify no packages placed on top of fragile items
    - Check Z-axis overlap and XY footprint overlap
    - _Requirements: 3.5_
  
  - [x] 7.5 Implement orientation lock checker
    - Write `_can_rotate()` method
    - Return False if package has this_side_up=True
    - Prevent X/Y dimension swapping for locked packages
    - _Requirements: 3.6_
  
  - [x] 7.6 Implement stability checker
    - Write `_check_stability()` method
    - Verify package is on floor (Z=0) or on other packages
    - Calculate base area overlap with supporting packages
    - Verify at least 60% base area support
    - _Requirements: 3.7, 3.8_
  
  - [x] 7.7 Implement main packing algorithm
    - Write `pack_route()` method
    - Sort packages using LIFO strategy
    - Iterate through packages and find valid positions
    - Track placed and failed packages
    - Calculate utilization percentage
    - _Requirements: 3.1, 3.2, 3.3, 3.4_
  
  - [ ]* 7.8 Write property test for LIFO sorting
    - **Property 17: Primary sort by reverse stop order**
    - **Property 18: Secondary sort by volume**
    - **Validates: Requirements 3.2, 3.3**
    - Generate random packages with stop numbers and volumes
    - Verify sorting order matches LIFO priority
  
  - [ ]* 7.9 Write property test for fragile constraint
    - **Property 20: Fragile stacking constraint**
    - **Validates: Requirements 3.5**
    - Generate random packing scenarios with fragile packages
    - Verify no packages placed on top of fragile items
  
  - [ ]* 7.10 Write property test for orientation lock
    - **Property 21: Orientation lock constraint**
    - **Validates: Requirements 3.6**
    - Generate random packages with this_side_up=True
    - Verify dimensions not swapped in X/Y
  
  - [ ]* 7.11 Write property test for stability
    - **Property 23: Stability percentage requirement**
    - **Validates: Requirements 3.8**
    - Generate random packing scenarios
    - Verify all placed packages have 60% base support
  
  - [ ]* 7.12 Write unit tests for packing edge cases
    - Test single package packing
    - Test all fragile packages
    - Test all orientation-locked packages
    - Test packages that don't fit

- [x] 8. Checkpoint - LIFO Packing validation
  - Run all packing engine tests
  - Verify LIFO ordering and constraint satisfaction
  - Ensure all tests pass, ask the user if questions arise

- [x] 9. Implement Driver Manifest Builder
  - [x] 9.1 Implement CSV manifest generation
    - Write `generate_csv()` method
    - Create columns: Stop, Source Name, Destination Name, Order ID, Dimensions, Weight, Special Handling
    - Format dimensions as "LxWxH cm"
    - Add special handling icons for fragile and this_side_up
    - Default missing source names to "Depot"
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 4.12_
  
  - [x] 9.2 Implement special handling formatter
    - Write `_format_special_handling()` method
    - Return "⚠️ FRAGILE" for fragile packages
    - Return "⬆️ THIS SIDE UP" for orientation-locked packages
    - Combine both if both constraints apply
    - _Requirements: 4.7, 4.8_
  
  - [x] 9.3 Implement PDF manifest generation
    - Write `generate_pdf()` method using reportlab
    - Create header with route info, vehicle name, total cost
    - Create table with stop-by-stop instructions
    - Include source and destination names prominently
    - Include package details and special handling icons
    - Create footer with summary statistics
    - _Requirements: 4.1, 4.2, 4.3, 4.5, 4.6, 4.7, 4.8, 4.10_
  
  - [ ]* 9.4 Write property test for route order preservation
    - **Property 25: Route order preservation**
    - **Validates: Requirements 4.1**
    - Generate random routes with stop sequences
    - Verify manifest lists stops in correct order
  
  - [ ]* 9.5 Write property test for complete package information
    - **Property 26: Complete package information**
    - **Validates: Requirements 4.2, 4.3, 4.5, 4.6**
    - Generate random packages
    - Verify manifest includes all required fields
  
  - [ ]* 9.6 Write property test for special handling indicators
    - **Property 27: Conditional special handling indicators**
    - **Validates: Requirements 4.7, 4.8**
    - Generate packages with various constraint combinations
    - Verify correct icons appear in manifest
  
  - [ ]* 9.7 Write unit tests for manifest edge cases
    - Test empty route handling
    - Test missing source name defaults to "Depot"
    - Test PDF file validity (check PDF header)
    - Test CSV parseability

- [x] 10. Checkpoint - Manifest Builder validation
  - Run all manifest builder tests
  - Verify CSV and PDF generation work correctly
  - Ensure all tests pass, ask the user if questions arise

- [x] 11. Integrate components into Streamlit dashboard
  - [x] 11.1 Add CSV upload widget to dashboard
    - Add file uploader for CSV manifests
    - Call CSV parser on upload
    - Display validation errors if parsing fails
    - Display success message and package count if parsing succeeds
    - Preserve DLL loading configuration in dashboard/app.py
    - _Requirements: 1.1, 1.11, 1.12_
  
  - [x] 11.2 Update fleet configuration UI
    - Add "Fuel Efficiency (km/L)" input field for each vehicle type
    - Update FleetComposer calls to include fuel efficiency
    - Display fuel efficiency in vehicle summary table
    - _Requirements: 2.1_
  
  - [x] 11.3 Update route display with financial details
    - Display fuel consumed (liters) for each route
    - Display fuel cost breakdown
    - Display labor cost breakdown
    - Display total cost per route
    - Add financial summary section with vehicle-specific efficiency
    - _Requirements: 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8_
  
  - [x] 11.4 Replace existing packing with LIFO packing engine
    - Replace current packing logic with LIFOPackingEngine
    - Pass route stop order to packing engine
    - Display packing results with utilization percentage
    - Show failed packages if any cannot be placed
    - Update 3D visualization to show LIFO ordering (back to door)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.10_
  
  - [x] 11.5 Add manifest download buttons
    - Add "Download CSV Manifest" button for each route
    - Add "Download PDF Manifest" button for each route
    - Wire buttons to ManifestBuilder methods
    - Handle download errors gracefully
    - _Requirements: 4.9, 4.10_
  
  - [ ]* 11.6 Write integration tests for end-to-end workflow
    - Test CSV upload → Parse → Solve → Pack → Manifest flow
    - Test with small dataset (5 packages, 3 destinations)
    - Test with medium dataset (50 packages, 10 destinations)
    - Verify all components work together correctly

- [x] 12. Final checkpoint and documentation
  - Run complete test suite (unit + property tests)
  - Verify all 29 correctness properties pass
  - Test dashboard with sample CSV files
  - Verify CSV and PDF manifests download correctly
  - Update README with new feature documentation
  - Ensure all tests pass, ask the user if questions arise

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation throughout implementation
- Property tests validate universal correctness properties with 100+ iterations
- Unit tests validate specific examples and edge cases
- The DLL loading configuration in `dashboard/app.py` must be preserved when modifying that file
- All new Python test files that import `vrp_core` must include the DLL directory setup
