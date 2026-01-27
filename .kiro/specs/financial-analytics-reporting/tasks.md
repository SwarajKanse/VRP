# Implementation Plan: Financial Analytics & Reporting

## Overview

This implementation plan adds financial analytics and reporting capabilities to the existing VRP Dashboard. The feature is implemented entirely in Python within the `dashboard/app.py` file, following the existing modular architecture pattern. All financial calculations derive from existing session state data (routes, time_matrix, customer data) without modifying the C++ solver.

The implementation follows a bottom-up approach: first building the calculation engine, then adding UI components, and finally integrating with the existing dashboard flow.

## Tasks

- [x] 1. Create financial calculation module with data structures
  - Add RouteMetrics and FleetMetrics dataclasses to dashboard/app.py
  - Implement calculate_route_distance() function
  - Implement calculate_route_duration() function
  - _Requirements: 1.1, 1.2, 5.1, 5.2_

- [ ]* 1.1 Write property tests for distance and duration calculations
  - **Property 1: Fleet Distance Aggregation**
  - **Property 2: Fleet Duration Aggregation**
  - **Property 11: Time Matrix Integration**
  - _Requirements: 1.1, 1.2, 6.1_

- [x] 2. Implement core financial calculation functions
  - Implement calculate_route_metrics() function
  - Implement calculate_fleet_metrics() function
  - Handle edge cases (empty routes, zero values)
  - _Requirements: 1.3, 1.4, 1.5, 4.1, 5.3, 5.4, 5.5, 5.6_

- [ ]* 2.1 Write property tests for cost calculations
  - **Property 3: Cost Calculation Formulas**
  - **Property 4: Route Metrics Calculation**
  - **Property 8: Cost Per Kilometer Calculation**
  - **Property 9: Cost Per Delivery Calculation**
  - **Property 12: Routes Integration**
  - _Requirements: 1.3, 1.4, 1.5, 4.1, 5.3, 5.4, 5.5, 5.6, 6.2_

- [ ]* 2.2 Write unit tests for edge cases
  - Test empty routes (length 1, only depot)
  - Test single customer routes
  - Test zero service time
  - Test division by zero handling
  - _Requirements: 1.3, 1.4, 1.5, 5.5, 5.6_

- [x] 3. Implement operations configuration UI component
  - Add render_operations_config() function to UI Components Module
  - Create sidebar expander with three number inputs (fuel_price, vehicle_mileage, driver_wage)
  - Set default values and validation (min_value > 0)
  - Return configuration dictionary
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.6_

- [ ]* 3.1 Write property tests for cost parameter validation
  - **Property 6: Positive Cost Parameter Validation**
  - _Requirements: 2.6_

- [ ]* 3.2 Write unit tests for configuration UI
  - Test default values are correct
  - Test configuration dictionary structure
  - _Requirements: 2.2, 2.3, 2.4_

- [x] 4. Implement financial overview UI component
  - Add render_financial_overview() function to UI Components Module
  - Display metrics in two rows using st.columns() and st.metric()
  - Row 1: Total Cost, Fuel Cost, Labor Cost
  - Row 2: Total Distance, Total Duration, Cost/km, Cost/Delivery
  - _Requirements: 1.6, 5.7_

- [ ]* 4.1 Write unit tests for financial overview rendering
  - Test with valid FleetMetrics data
  - Test metric formatting (currency, units)
  - _Requirements: 1.6, 5.7_

- [x] 5. Implement cost analysis chart component
  - Add render_cost_analysis_chart() function to UI Components Module
  - Create DataFrame from route_metrics list
  - Display stacked bar chart using st.bar_chart()
  - _Requirements: 4.2, 4.3, 4.4_

- [ ]* 5.1 Write unit tests for chart rendering
  - Test with multiple routes
  - Test with single route
  - Test with empty routes list
  - _Requirements: 4.2_

- [x] 6. Implement driver manifest export functionality
  - Add format_time() helper function
  - Add generate_driver_manifest() function to Export Module
  - Create DataFrame with columns: Route_ID, Stop_Number, Customer_ID, Arrival_Time, Action
  - Use existing calculate_route_timing() for arrival times
  - _Requirements: 3.1, 3.3, 3.4_

- [ ]* 6.1 Write property tests for manifest generation
  - **Property 7: Manifest Structure Completeness**
  - _Requirements: 3.1, 3.3, 3.4_

- [ ]* 6.2 Write unit tests for manifest export
  - Test format_time() with various minute values
  - Test manifest with single route
  - Test manifest with multiple routes
  - Test CSV serialization
  - _Requirements: 3.1, 3.3, 3.4_

- [x] 7. Implement download button UI component
  - Add render_download_button() function to UI Components Module
  - Call generate_driver_manifest() to create DataFrame
  - Convert DataFrame to CSV using to_csv()
  - Create st.download_button() with timestamp in filename
  - Disable button when routes is None or empty
  - _Requirements: 3.2, 3.5_

- [ ]* 7.1 Write unit tests for download button
  - Test button disabled state when no routes
  - Test CSV generation with valid routes
  - Test filename format with timestamp
  - _Requirements: 3.2, 3.5_

- [x] 8. Integrate financial features into main dashboard flow
  - Add render_operations_config() call in sidebar section (after chaos controls)
  - Add conditional check: if routes exist, calculate financial metrics
  - Add render_financial_overview() call after existing performance metrics
  - Add render_cost_analysis_chart() call after financial overview
  - Add render_download_button() call in sidebar (after operations config)
  - Preserve existing DLL loading configuration (do not modify)
  - _Requirements: 1.7, 4.5, 6.3_

- [ ]* 8.1 Write integration tests for dashboard flow
  - Test financial section appears when routes exist
  - Test financial section hidden when no routes
  - Test cost analysis chart appears when routes exist
  - Test download button disabled when no routes
  - _Requirements: 1.7, 3.5, 4.5_

- [x] 9. Implement reactive cost recalculation
  - Ensure calculate_fleet_metrics() is called with current cost parameters from render_operations_config()
  - Verify calculations update when cost parameters change (Streamlit handles reactivity automatically)
  - Test that changing parameters does not trigger solver re-run
  - _Requirements: 2.5_

- [ ]* 9.1 Write property tests for cost parameter independence
  - **Property 5: Cost Parameter Independence**
  - _Requirements: 2.5_

- [x] 10. Add chaos mode integration
  - Verify financial metrics recalculate when emergency orders are injected
  - Ensure updated routes from chaos mode are used in financial calculations
  - Test that costs reflect the new route structure after re-optimization
  - _Requirements: 6.4_

- [ ]* 10.1 Write property tests for chaos mode cost recalculation
  - **Property 10: Chaos Mode Cost Recalculation**
  - _Requirements: 6.4_

- [ ]* 10.2 Write integration tests for chaos mode
  - Test financial metrics before and after emergency order injection
  - Test that costs increase when routes become longer
  - _Requirements: 6.4_

- [x] 11. Add error handling and validation
  - Add try-except blocks around financial calculations
  - Display user-friendly error messages using st.error()
  - Handle missing data gracefully (None checks)
  - Add input validation for cost parameters
  - _Requirements: All requirements (error handling)_

- [ ]* 11.1 Write unit tests for error handling
  - Test with None routes
  - Test with None time_matrix
  - Test with missing customer data columns
  - Test with invalid cost parameters
  - _Requirements: All requirements (error handling)_

- [x] 12. Final integration testing and polish
  - Run full dashboard with demo data
  - Test CSV upload flow with financial features
  - Test chaos mode with financial features
  - Verify all UI components render correctly
  - Check responsive layout on different screen sizes
  - _Requirements: All requirements_

- [ ]* 12.1 Write end-to-end integration tests
  - Test complete workflow: upload CSV → run solver → view financial metrics → download manifest
  - Test demo data workflow
  - Test chaos mode workflow with financial updates
  - _Requirements: All requirements_

- [x] 13. Checkpoint - Ensure all tests pass
  - Run pytest on all new test files
  - Verify all property tests pass with 100+ iterations
  - Fix any failing tests
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- Integration tests verify seamless interaction with existing dashboard
- The implementation preserves the existing DLL loading configuration for Windows compatibility
- All financial calculations are pure functions that don't modify global state
- Streamlit's reactive model handles UI updates automatically when parameters change
