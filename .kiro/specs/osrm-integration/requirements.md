# Requirements Document: OSRM Integration

## Introduction

This specification defines the integration of the Open Source Routing Machine (OSRM) API into the VRP solver dashboard to replace the current Haversine-based time matrix calculation with real road network travel times. The current implementation uses a simplified "fake" time matrix based on Haversine distance divided by 40 km/h, which does not reflect actual road network conditions, traffic patterns, or routing constraints. By integrating OSRM, the solver will use realistic driving times that account for actual road networks, improving route quality and accuracy.

## Glossary

- **OSRM**: Open Source Routing Machine - an open-source routing engine for road networks
- **Time_Matrix**: An N×N matrix where element [i][j] represents the travel time in minutes from customer i to customer j
- **Haversine_Distance**: The great-circle distance between two points on a sphere, calculated using their latitude and longitude
- **OSRM_Table_Service**: The OSRM API endpoint that computes distance or duration matrices for multiple source-destination pairs
- **Dashboard**: The Streamlit-based web application in dashboard/app.py
- **Fallback_Mode**: Operation mode where the system uses Haversine-based calculations when OSRM API is unavailable
- **DLL_Configuration**: The Windows-specific DLL loading block at the top of app.py that must be preserved

## Requirements

### Requirement 1: OSRM API Integration

**User Story:** As a logistics planner, I want the VRP solver to use real road network travel times from OSRM, so that the generated routes reflect actual driving conditions.

#### Acceptance Criteria

1. THE Dashboard SHALL implement a function `get_osrm_matrix(locations)` that accepts a list of [latitude, longitude] coordinate pairs
2. WHEN constructing the OSRM API request, THE Dashboard SHALL convert coordinates from [latitude, longitude] format to [longitude, latitude] format required by OSRM
3. THE Dashboard SHALL construct a URL for the OSRM Table Service in the format: `http://router.project-osrm.org/table/v1/driving/{lon},{lat};{lon},{lat}...?annotations=duration`
4. WHEN the OSRM API returns duration data, THE Dashboard SHALL convert the values from seconds to minutes by dividing by 60.0
5. THE Dashboard SHALL return an N×N matrix of driving times in minutes where element [i][j] represents travel time from location i to location j

### Requirement 2: Solver Integration

**User Story:** As a developer, I want the solve_routing function to use OSRM travel times, so that the C++ solver receives realistic time matrices.

#### Acceptance Criteria

1. WHEN the solve_routing function is called, THE Dashboard SHALL invoke `get_osrm_matrix` to obtain real driving times
2. THE Dashboard SHALL pass the OSRM-generated time matrix to the C++ solver via the existing time_matrix parameter
3. THE Dashboard SHALL NOT modify the C++ solver code or bindings
4. THE Dashboard SHALL preserve the existing function signature of solve_routing

### Requirement 3: Robust Error Handling and Fallback

**User Story:** As a user, I want the dashboard to continue working even when the OSRM API is unavailable, so that network issues don't prevent me from using the solver.

#### Acceptance Criteria

1. WHEN the OSRM API request fails due to network errors, timeouts, or HTTP errors, THE Dashboard SHALL catch the exception
2. IF the OSRM API fails, THEN THE Dashboard SHALL automatically fall back to the existing `generate_time_matrix` function (Haversine-based calculation)
3. WHEN fallback mode is activated, THE Dashboard SHALL log a warning message to inform the user
4. THE Dashboard SHALL set a timeout of 10 seconds for OSRM API requests to prevent indefinite hanging
5. THE Dashboard SHALL NOT crash or raise unhandled exceptions due to OSRM API failures

### Requirement 4: Code Preservation

**User Story:** As a Windows user, I want the DLL loading configuration to remain intact, so that the dashboard continues to work on my system.

#### Acceptance Criteria

1. THE Dashboard SHALL preserve the existing DLL loading block at the top of app.py without modification
2. WHEN modifying app.py, THE Dashboard SHALL NOT remove or alter the `os.add_dll_directory()` calls
3. THE Dashboard SHALL NOT modify any code outside of the time matrix generation and error handling logic

### Requirement 5: HTTP Request Implementation

**User Story:** As a developer, I want the OSRM integration to use standard Python libraries, so that the implementation is maintainable and reliable.

#### Acceptance Criteria

1. THE Dashboard SHALL use Python's `requests` library for HTTP communication with the OSRM API
2. WHEN making HTTP requests, THE Dashboard SHALL include a timeout parameter set to 10 seconds
3. THE Dashboard SHALL handle HTTP status codes and raise appropriate exceptions for non-200 responses
4. THE Dashboard SHALL parse JSON responses from the OSRM API correctly

### Requirement 6: User Feedback

**User Story:** As a user, I want to know when the system is using fallback mode, so that I understand the quality of the routing results.

#### Acceptance Criteria

1. WHEN the OSRM API is successfully used, THE Dashboard SHALL display a success indicator or message
2. WHEN fallback mode is activated, THE Dashboard SHALL display a warning message indicating that Haversine-based times are being used
3. THE Dashboard SHALL use Streamlit's messaging components (st.warning, st.info, st.success) for user notifications
4. THE Dashboard SHALL provide clear, non-technical language in user-facing messages
