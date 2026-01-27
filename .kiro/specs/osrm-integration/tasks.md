# Implementation Plan: OSRM Integration

## Overview

This implementation plan converts the OSRM integration design into discrete coding tasks. The approach is to add the new `get_osrm_matrix()` function, modify `solve_routing()` to use it with fallback logic, and add comprehensive tests. All changes are confined to `dashboard/app.py` with no modifications to C++ code or other files.

## Tasks

- [x] 1. Add requests library import and implement get_osrm_matrix() function
  - Add `import requests` at the top of dashboard/app.py (after existing imports)
  - Implement `get_osrm_matrix(locations: List[List[float]]) -> List[List[float]]` function
  - Place the function after `generate_time_matrix()` in the Solver Integration Module section
  - Extract coordinates and convert from [lat, lon] to "lon,lat" format for OSRM
  - Construct OSRM Table Service URL: `http://router.project-osrm.org/table/v1/driving/{coords}?annotations=duration`
  - Make HTTP GET request with 10-second timeout using `requests.get(url, timeout=10)`
  - Call `response.raise_for_status()` to handle HTTP errors
  - Parse JSON response and extract `data['durations']` matrix
  - Convert duration values from seconds to minutes by dividing by 60.0
  - Return the N×N time matrix in minutes
  - Let all exceptions (ConnectionError, Timeout, HTTPError, JSONDecodeError, KeyError) propagate to caller
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 3.4, 5.1, 5.2, 5.3, 5.4_

- [x] 2. Modify solve_routing() to use OSRM with fallback
  - [x] 2.1 Update solve_routing() function to integrate OSRM
    - Extract locations from DataFrame: `locations = [[row['lat'], row['lon']] for _, row in df_sorted.iterrows()]`
    - Wrap OSRM call in try-except block before solver invocation
    - In try block: call `time_matrix = get_osrm_matrix(locations)` and display success message using `st.info("✅ Using OSRM real road network travel times")`
    - In except block: catch all exceptions, display warning using `st.warning()` with error type and fallback message, call `time_matrix = generate_time_matrix(df)` as fallback
    - Pass the time_matrix (from either OSRM or fallback) to the C++ solver
    - Preserve all existing solver invocation logic and function signature
    - **CRITICAL**: Do not modify the DLL loading block at the top of app.py
    - _Requirements: 2.1, 2.2, 2.4, 3.1, 3.2, 3.3, 3.5, 4.1, 4.2, 6.1, 6.2, 6.3_

  - [ ]* 2.2 Write unit tests for get_osrm_matrix()
    - Create `tests/test_osrm_integration.py` with DLL loading block
    - Test happy path: 3 Mumbai locations returning 3×3 matrix
    - Test single location: returns 1×1 matrix with [0.0]
    - Test coordinate order: verify URL contains "lon,lat" format
    - Test timeout: mock slow response, verify Timeout exception
    - Test HTTP error: mock 404/500 response, verify HTTPError raised
    - Test invalid JSON: mock malformed response, verify JSONDecodeError
    - Test missing field: mock JSON without "durations", verify KeyError
    - _Requirements: 1.2, 1.3, 1.4, 1.5, 3.4, 5.3_

  - [ ]* 2.3 Write property test for coordinate order transformation
    - **Property 1: Coordinate Order Transformation**
    - **Validates: Requirements 1.2**
    - Use Hypothesis to generate random lists of [lat, lon] pairs
    - For any list of coordinates, verify constructed URL contains "lon,lat" order
    - Run with minimum 100 iterations
    - Tag: `# Feature: osrm-integration, Property 1: Coordinate Order Transformation`

  - [ ]* 2.4 Write property test for URL format compliance
    - **Property 2: URL Format Compliance**
    - **Validates: Requirements 1.3**
    - Use Hypothesis to generate random location lists
    - For any locations, verify URL starts with correct base and contains "?annotations=duration"
    - Run with minimum 100 iterations
    - Tag: `# Feature: osrm-integration, Property 2: URL Format Compliance`

  - [ ]* 2.5 Write property test for time unit conversion
    - **Property 3: Time Unit Conversion**
    - **Validates: Requirements 1.4**
    - Use Hypothesis to generate random duration matrices in seconds
    - For any duration matrix, verify output equals input divided by 60.0
    - Run with minimum 100 iterations
    - Tag: `# Feature: osrm-integration, Property 3: Time Unit Conversion`

  - [ ]* 2.6 Write property test for matrix dimensions
    - **Property 4: Matrix Dimensions**
    - **Validates: Requirements 1.5**
    - Use Hypothesis to generate random location lists of size N
    - Mock OSRM response with appropriate dimensions
    - For any N locations, verify output is N×N matrix
    - Run with minimum 100 iterations
    - Tag: `# Feature: osrm-integration, Property 4: Matrix Dimensions`

- [x] 3. Checkpoint - Ensure all tests pass
  - Run `python -m pytest tests/test_osrm_integration.py -v` to verify all tests pass
  - Manually test dashboard with network connected (OSRM should work)
  - Manually test dashboard with network disconnected (fallback should activate)
  - Verify DLL loading still works on Windows
  - Ask the user if questions arise

- [-] 4. Add integration tests for solve_routing() fallback behavior
  - [x] 4.1 Write unit tests for solve_routing() integration
    - Test OSRM success path: mock successful OSRM response, verify matrix used and success message displayed
    - Test OSRM failure fallback: mock ConnectionError, verify fallback to generate_time_matrix() and warning displayed
    - Test DLL configuration preservation: verify os.add_dll_directory() calls remain unchanged
    - _Requirements: 2.1, 2.2, 3.1, 3.2, 3.3, 4.1, 4.2, 6.1_

  - [ ]* 4.2 Write property test for exception handling
    - **Property 5: Exception Handling for Network Errors**
    - **Validates: Requirements 3.1, 3.5**
    - Use Hypothesis to sample different error types (ConnectionError, Timeout, HTTPError)
    - For any network error, verify exception propagates without crash
    - Run with minimum 100 iterations
    - Tag: `# Feature: osrm-integration, Property 5: Exception Handling for Network Errors`

  - [ ]* 4.3 Write property test for fallback activation
    - **Property 6: Fallback Activation**
    - **Validates: Requirements 3.2**
    - Use Hypothesis to sample different exception types
    - For any OSRM error, verify solve_routing() falls back successfully and returns valid routes
    - Run with minimum 100 iterations
    - Tag: `# Feature: osrm-integration, Property 6: Fallback Activation`

  - [ ]* 4.4 Write property test for fallback user notification
    - **Property 7: Fallback User Notification**
    - **Validates: Requirements 3.3, 6.2**
    - Use Hypothesis to sample different error types
    - For any OSRM failure, verify warning message is displayed containing "Haversine"
    - Run with minimum 100 iterations
    - Tag: `# Feature: osrm-integration, Property 7: Fallback User Notification`

  - [ ]* 4.5 Write property test for HTTP error handling
    - **Property 8: HTTP Error Handling**
    - **Validates: Requirements 5.3**
    - Use Hypothesis to generate different non-200 status codes
    - For any non-200 response, verify HTTPError is raised
    - Run with minimum 100 iterations
    - Tag: `# Feature: osrm-integration, Property 8: HTTP Error Handling`

  - [ ]* 4.6 Write property test for JSON response parsing
    - **Property 9: JSON Response Parsing**
    - **Validates: Requirements 5.4**
    - Use Hypothesis to generate valid OSRM JSON responses with "durations" field
    - For any valid response, verify parsing succeeds without exceptions
    - Run with minimum 100 iterations
    - Tag: `# Feature: osrm-integration, Property 9: JSON Response Parsing`

- [x] 5. Final checkpoint - Ensure all tests pass
  - Run full test suite: `python -m pytest tests/ -v`
  - Run property tests with thorough profile: `python -m pytest tests/ -v --hypothesis-profile=thorough`
  - Verify dashboard works in both OSRM and fallback modes
  - Verify no crashes or unhandled exceptions
  - Ensure all tests pass, ask the user if questions arise

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- All changes are confined to `dashboard/app.py` - no C++ modifications
- The DLL loading block at the top of app.py must remain unchanged
- Property tests validate universal correctness properties across many inputs
- Unit tests validate specific examples and edge cases
- Both testing approaches are complementary and necessary for comprehensive coverage
