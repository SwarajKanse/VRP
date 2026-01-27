# Implementation Plan: Dynamic Event Injection (Chaos Mode)

## Overview

This implementation plan breaks down the chaos mode feature into discrete, incremental coding tasks. Each task builds on previous work, with testing integrated throughout to validate functionality early. The implementation focuses on extending the existing Streamlit dashboard without modifying the core C++ solver.

## Tasks

- [x] 1. Set up session state management for chaos mode
  - Initialize session state variables in `dashboard/app.py`
  - Add `original_customers`, `dynamic_customers`, `chaos_mode_active`, `current_time` to session state
  - Create `initialize_chaos_state()` function to handle initialization
  - Create `get_current_customers()` function to merge original and dynamic customers
  - **CRITICAL**: Preserve existing DLL loading configuration at top of file
  - _Requirements: 4.1_

- [ ]* 1.1 Write property test for session state initialization
  - **Property 9: Session State Persistence**
  - **Validates: Requirements 4.1, 4.2**
  - Test that session state variables are properly initialized and persist across interactions

- [x] 2. Implement emergency order generator
  - [x] 2.1 Create `generate_emergency_order()` function in `dashboard/app.py`
    - Accept `existing_df` (DataFrame) and `current_time` (float) as parameters
    - Calculate bounding box from existing customer coordinates
    - Generate random location within bounds using `random.uniform()`
    - Generate random demand (1-5) using `random.randint()`
    - Set time window: start = current_time, end = current_time + 30
    - Set service_time = 5 (priority handling)
    - Assign unique ID: max(existing_df['id']) + 1
    - Return single-row DataFrame with new customer
    - Handle edge case: if only depot exists, use default Mumbai bounds
    - _Requirements: 1.2_

  - [ ]* 2.2 Write property test for valid emergency order generation
    - **Property 1: Valid Emergency Order Generation**
    - **Validates: Requirements 1.2**
    - Use hypothesis to generate random customer datasets and current times
    - Verify location within bounds, demand 1-5, time windows, service time = 5

  - [ ]* 2.3 Write unit tests for emergency order edge cases
    - Test with only depot (single customer)
    - Test with customers at boundary coordinates
    - Test with current_time near end of day
    - _Requirements: 1.2_

- [x] 3. Implement chaos mode UI components
  - [x] 3.1 Create `render_chaos_controls()` function in `dashboard/app.py`
    - Add sidebar header "🚨 Chaos Mode"
    - Create "🚨 Inject Emergency Order" button with secondary type
    - Create "🔄 Reset Simulation" button with secondary type
    - Add help text to buttons
    - Return tuple of (inject_button, reset_button) states
    - _Requirements: 1.1, 4.3_

  - [x] 3.2 Create `show_reoptimization_toast()` function
    - Accept execution_time_ms as parameter
    - Display toast with format: "⚡ Fleet Re-routed in {time}ms!"
    - Use ⚡ icon for visual distinction
    - _Requirements: 2.1_

  - [ ]* 3.3 Write unit tests for UI component rendering
    - Test that chaos controls render without errors
    - Test that buttons have correct labels
    - Test toast notification format
    - _Requirements: 1.1, 2.1, 4.3_

- [x] 4. Integrate emergency order injection into main flow
  - [x] 4.1 Modify `main()` function to handle injection button
    - Call `initialize_chaos_state()` at start of main()
    - Store initial customer data in `st.session_state.original_customers` on first load
    - Call `render_chaos_controls()` after sidebar configuration
    - Handle inject_button click:
      - Get current customers using `get_current_customers()`
      - Generate new order using `generate_emergency_order()`
      - Append to `st.session_state.dynamic_customers`
      - Set `st.session_state.chaos_mode_active = True`
      - Merge customers and convert to Customer objects
      - Call `solve_routing()` with updated customer list
      - Measure execution time
      - Call `show_reoptimization_toast()` with execution time
      - Update session state with new routes and time matrix
    - **CRITICAL**: Preserve existing DLL loading configuration
    - _Requirements: 1.3, 1.4, 2.1_

  - [ ]* 4.2 Write property test for customer list growth
    - **Property 2: Customer List Growth**
    - **Validates: Requirements 1.3**
    - Test that injecting order increases list size by 1 with unique ID

  - [ ]* 4.3 Write property test for solver invocation
    - **Property 3: Solver Invocation After Injection**
    - **Validates: Requirements 1.4**
    - Test that solve_routing is called with updated customer list

- [x] 5. Checkpoint - Test emergency order injection flow
  - Manually test injecting emergency orders in dashboard
  - Verify new customers appear in customer list
  - Verify solver is invoked and routes are updated
  - Verify toast notification displays
  - Ensure all tests pass, ask the user if questions arise

- [x] 6. Implement visual highlighting for emergency orders
  - [x] 6.1 Modify `create_customer_layer()` function
    - Add parameter `dynamic_customer_ids` (List[int])
    - Add column to DataFrame: `is_dynamic = df['id'].isin(dynamic_customer_ids)`
    - Update get_color to use conditional: yellow (255,255,0) for dynamic, red (255,0,0) for original
    - Update tooltip to show "EMERGENCY" label for dynamic customers
    - _Requirements: 2.2_

  - [x] 6.2 Update `main()` to pass dynamic customer IDs to visualization
    - Extract dynamic customer IDs from `st.session_state.dynamic_customers`
    - Pass IDs to `create_customer_layer()` function
    - _Requirements: 2.2_

  - [ ]* 6.3 Write property test for visual distinction
    - **Property 5: Visual Distinction for Emergency Orders**
    - **Validates: Requirements 2.2**
    - Test that rendering assigns different colors to dynamic vs original customers

  - [ ]* 6.4 Write property test for route completeness
    - **Property 6: Route Completeness**
    - **Validates: Requirements 2.3**
    - Test that injected customer ID appears in at least one route

- [x] 7. Implement reset simulation functionality
  - [x] 7.1 Create `handle_reset_button()` function in `dashboard/app.py`
    - Clear `st.session_state.dynamic_customers` (set to empty list)
    - Set `st.session_state.chaos_mode_active = False`
    - Reset `st.session_state.current_time = 0.0`
    - Clear routes: `st.session_state.routes = None`
    - Clear execution time: `st.session_state.execution_time_ms = None`
    - Clear time matrix: `st.session_state.time_matrix = None`
    - Call `st.rerun()` to refresh UI
    - _Requirements: 4.4_

  - [x] 7.2 Integrate reset handler into `main()` function
    - Check if reset_button is clicked
    - Call `handle_reset_button()` if clicked
    - _Requirements: 4.4_

  - [ ]* 7.3 Write property test for reset behavior
    - **Property 10: Reset to Initial State**
    - **Validates: Requirements 4.4**
    - Test that reset clears all dynamic customers and returns to original state

  - [ ]* 7.4 Write unit test for reset edge cases
    - Test reset with no injected orders
    - Test reset with multiple injected orders
    - Test reset preserves original customer data
    - _Requirements: 4.4_

- [x] 8. Implement OSRM integration for dynamic customers
  - [x] 8.1 Verify `solve_routing()` respects OSRM toggle for dynamic customers
    - Review existing OSRM/Haversine logic in `solve_routing()`
    - Ensure time matrix generation works correctly with merged customer list
    - No code changes needed if existing logic already handles this
    - _Requirements: 3.1_

  - [ ]* 8.2 Write property test for distance matrix configuration respect
    - **Property 7: Distance Matrix Configuration Respect**
    - **Validates: Requirements 3.1**
    - Test that OSRM is used when enabled, Haversine when disabled
    - Mock OSRM API calls to test both paths

- [x] 9. Implement graceful infeasibility handling
  - [x] 9.1 Add infeasibility detection in injection handler
    - After `solve_routing()` returns, check if routes are empty or incomplete
    - If infeasible: keep previous solution, display warning toast
    - Warning format: "⚠️ Emergency order could not be fully integrated. Showing best available solution."
    - Still add customer to dynamic list for transparency
    - _Requirements: 3.3_

  - [ ]* 9.2 Write property test for graceful infeasibility handling
    - **Property 8: Graceful Infeasibility Handling**
    - **Validates: Requirements 3.3**
    - Generate infeasible emergency orders (impossible time windows)
    - Test that system doesn't crash and displays warning

  - [ ]* 9.3 Write unit test for infeasibility scenarios
    - Test with emergency order that has impossible time window
    - Test with emergency order that exceeds all vehicle capacities
    - Verify warning message is displayed
    - _Requirements: 3.3_

- [x] 10. Checkpoint - Test complete chaos mode workflow
  - Test full injection workflow: load data → inject → visualize → reset
  - Test multiple sequential injections
  - Test OSRM toggle with injections
  - Test infeasibility handling
  - Verify performance metrics display correctly
  - Ensure all tests pass, ask the user if questions arise

- [x] 11. Add performance monitoring enhancements
  - [x] 11.1 Update metrics display to show chaos mode statistics
    - Add metric for "Dynamic Orders Injected" count
    - Add metric for "Average Re-optimization Time" (if multiple injections)
    - Display in existing metrics section
    - _Requirements: 2.1_

  - [ ]* 11.2 Write property test for performance toast display
    - **Property 4: Performance Toast Display**
    - **Validates: Requirements 2.1**
    - Test that toast is displayed after every re-optimization

- [x] 12. Final integration and polish
  - [x] 12.1 Add visual indicators in route details
    - Update route details expander to mark emergency orders with 🚨 emoji
    - Highlight emergency order rows in timing table
    - _Requirements: 2.2, 2.3_

  - [x] 12.2 Add chaos mode status indicator
    - Display badge in sidebar showing number of active emergency orders
    - Format: "🚨 Active Emergency Orders: N"
    - Only show when chaos_mode_active is True
    - _Requirements: 4.1_

  - [ ]* 12.3 Write integration tests for complete workflow
    - Test end-to-end: load → inject → visualize → reset
    - Test multiple injections with different configurations
    - Test interaction with existing features (CSV upload, OSRM toggle)
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 4.1, 4.2, 4.3, 4.4_

- [x] 13. Final checkpoint - Comprehensive testing
  - Run all unit tests: `python -m pytest tests/ -v`
  - Run all property tests with 100+ iterations
  - Manually test all user workflows in dashboard
  - Verify DLL loading configuration is preserved
  - Verify performance targets (< 10ms re-optimization)
  - Ensure all tests pass, ask the user if questions arise

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at key milestones
- Property tests validate universal correctness properties with 100+ iterations
- Unit tests validate specific examples and edge cases
- **CRITICAL**: All modifications to `dashboard/app.py` must preserve the Windows DLL loading configuration at the top of the file
- The C++ solver is not modified - all changes are in the Python dashboard layer
