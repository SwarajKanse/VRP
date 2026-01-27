# Implementation Plan: VRP Dashboard

## Overview

This implementation plan breaks down the VRP Dashboard into discrete coding tasks. The dashboard is a Streamlit application that integrates with the existing vrp_core C++ solver module. Tasks are organized to build incrementally: first the core structure and data handling, then solver integration, followed by visualization, and finally testing.

## Tasks

- [x] 1. Set up project structure and dependencies
  - Create `dashboard/` directory
  - Create `dashboard/app.py` as main entry point
  - Create `dashboard/requirements.txt` with dependencies: streamlit, pydeck, pandas, numpy
  - Add Windows DLL path fix at the top of app.py before vrp_core import
  - _Requirements: 1.1, 2.1, 2.2, 2.3, 9.1-9.5_

- [x] 2. Implement data management module
  - [x] 2.1 Create demo dataset generation function
    - Write `generate_demo_data()` function that returns DataFrame
    - Generate 5-10 random customers in Mumbai/Bandra area (lat: 19.05-19.08, lon: 72.82-72.85)
    - Include depot at (19.065, 72.835) as customer 0
    - Generate random demand (1-10), start_window (0-480), end_window (start + 60-120)
    - _Requirements: 4.2, 4.3, 4.4_
  
  - [ ]* 2.2 Write property test for demo dataset geographic bounds
    - **Property 1: Demo Dataset Geographic Bounds**
    - **Validates: Requirements 4.3**
  
  - [ ]* 2.3 Write property test for demo dataset validity
    - **Property 2: Demo Dataset Validity**
    - **Validates: Requirements 4.4**
  
  - [x] 2.4 Create CSV loading and validation function
    - Write `load_customer_csv(uploaded_file)` function
    - Parse CSV to DataFrame
    - Validate required columns: id, lat, lon, demand, start_window, end_window
    - Raise ValueError with descriptive message if columns missing
    - _Requirements: 4.5, 4.6_
  
  - [ ]* 2.5 Write property test for CSV column validation
    - **Property 3: CSV Column Validation**
    - **Validates: Requirements 4.6**
  
  - [x] 2.6 Create DataFrame to Customer conversion function
    - Write `dataframe_to_customers(df)` function
    - Convert each DataFrame row to vrp_core.Customer object
    - Map fields: id, lat, lon, demand, start_window, end_window
    - Return List[vrp_core.Customer]
    - _Requirements: 5.2, 8.1_
  
  - [ ]* 2.7 Write property test for data conversion preservation
    - **Property 4: DataFrame to Customer Conversion Preserves Data**
    - **Validates: Requirements 5.2, 8.1, 8.4**

- [x] 3. Implement solver integration module
  - [x] 3.1 Create solve_routing function
    - Write `solve_routing(customers, capacity, num_vehicles)` function
    - Create VRPSolver instance with capacity and num_vehicles
    - Measure execution time using time.perf_counter()
    - Call solver.solve(customers)
    - Return tuple: (routes, execution_time_ms)
    - Handle exceptions and return error message if solver fails
    - _Requirements: 5.3, 5.4, 5.5, 5.6_
  
  - [ ]* 3.2 Write property test for execution time measurement
    - **Property 5: Solver Execution Returns Positive Time**
    - **Validates: Requirements 5.5**
  
  - [x] 3.3 Create route to coordinates conversion function
    - Write `routes_to_coordinates(routes, df)` function
    - For each route, map customer IDs to lat/lon coordinates
    - Assign color from ROUTE_COLORS palette (Cyan, Magenta, Yellow, Green, Orange, Purple)
    - Return list of dicts with: route_id, path (list of [lon, lat]), color (RGB)
    - _Requirements: 8.2, 8.3_
  
  - [ ]* 3.4 Write property test for route coordinate conversion
    - **Property 10: Route Coordinate Conversion Completeness**
    - **Validates: Requirements 8.2, 8.3**

- [x] 4. Checkpoint - Verify data flow
  - Ensure all data conversion functions work correctly
  - Test with demo data and sample solver calls
  - Ask the user if questions arise

- [x] 5. Implement visualization module
  - [x] 5.1 Create customer scatter layer function
    - Write `create_customer_layer(df)` function
    - Create pydeck ScatterplotLayer with customer coordinates
    - Set color to red [255, 0, 0]
    - Set radius proportional to demand (e.g., demand * 50)
    - Return pdk.Layer object
    - _Requirements: 6.2, 6.3, 6.4_
  
  - [ ]* 5.2 Write property test for customer layer completeness
    - **Property 6: Customer Layer Contains All Customers**
    - **Validates: Requirements 6.2**
  
  - [ ]* 5.3 Write property test for marker size correlation
    - **Property 7: Marker Size Correlates with Demand**
    - **Validates: Requirements 6.3**
  
  - [x] 5.4 Create route path layers function
    - Write `create_route_layers(route_data)` function
    - For each route in route_data, create PathLayer or ArcLayer
    - Use route color from route_data
    - Set line width (e.g., 3-5 pixels)
    - Return list of pdk.Layer objects
    - _Requirements: 6.5, 6.6_
  
  - [ ]* 5.5 Write property test for route color uniqueness
    - **Property 8: Route Color Uniqueness**
    - **Validates: Requirements 6.6**
  
  - [x] 5.6 Create map rendering function
    - Write `render_map(customer_layer, route_layers, df)` function
    - Calculate viewport center from customer coordinates
    - Set initial zoom level (e.g., 12-14 for city view)
    - Use dark map style (e.g., 'mapbox://styles/mapbox/dark-v10')
    - Combine all layers and render with st.pydeck_chart()
    - _Requirements: 6.1, 6.7, 6.8_
  
  - [ ]* 5.7 Write property test for map viewport centering
    - **Property 9: Map Viewport Centers on Data**
    - **Validates: Requirements 6.8**

- [-] 6. Implement UI components module
  - [x] 6.1 Create sidebar rendering function
    - Write `render_sidebar()` function
    - Add number input for vehicle capacity (min=1, default=20)
    - Add number input for number of vehicles (min=1, default=3)
    - Add file uploader for CSV (accept .csv files)
    - Add "Run Solver" button
    - Return dict with: capacity, num_vehicles, uploaded_file, run_solver (button state)
    - _Requirements: 3.1, 3.2, 4.1, 5.1_
  
  - [x] 6.2 Create metrics display function
    - Write `render_metrics(execution_time_ms)` function
    - Use st.metric() to display execution time
    - Format time with 2 decimal places
    - Add label "Solver Execution Time (ms)"
    - _Requirements: 7.1, 7.3, 7.4_

- [x] 7. Implement main application orchestration
  - [x] 7.1 Set up Streamlit page configuration
    - Call st.set_page_config() with wide layout and dark theme
    - Set page title to "High-Frequency Logistics Dashboard"
    - _Requirements: 1.2, 1.3, 10.1_
  
  - [x] 7.2 Implement main application flow
    - Create main() function as entry point
    - Display title and branding
    - Call render_sidebar() to get user inputs
    - Load data: use uploaded CSV if provided, else use demo data
    - If "Run Solver" clicked: convert data, call solve_routing(), display metrics
    - Create visualization layers and render map
    - Handle errors with st.error() messages
    - _Requirements: 1.5, 5.6, 10.4_
  
  - [x] 7.3 Add error handling for DLL loading
    - Wrap vrp_core import in try-except
    - Check if build/Release directory exists before adding to DLL path
    - Display helpful error message if import fails
    - _Requirements: 2.4, 5.6_

- [x] 8. Checkpoint - End-to-end integration test
  - Run dashboard with demo data
  - Test CSV upload functionality
  - Verify solver execution and visualization
  - Ensure all tests pass
  - Ask the user if questions arise

- [ ]* 9. Write unit tests for edge cases
  - Test empty DataFrame handling
  - Test single customer scenario
  - Test CSV with missing columns
  - Test solver exception handling
  - Test color cycling when vehicles > available colors
  - _Requirements: 4.6, 5.6_

- [ ]* 10. Write integration tests
  - Test complete flow: demo data → solver → visualization
  - Test complete flow: CSV upload → solver → visualization
  - Test error scenarios: invalid CSV, solver failure
  - Mock vrp_core for isolated testing
  - _Requirements: All requirements_

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at key milestones
- Property tests validate universal correctness properties (minimum 100 iterations each)
- Unit tests validate specific examples and edge cases
- The Windows DLL path fix is critical and must be implemented first
- All property tests should be tagged with: `# Feature: vrp-dashboard, Property N: [property text]`
