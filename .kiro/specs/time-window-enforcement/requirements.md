# Requirements Document: Time Window Constraint Enforcement

## Introduction

This document specifies the requirements for implementing time window constraint enforcement in the VRP solver using real-world travel time matrices. The current solver includes time window fields (`start_window` and `end_window`) in the Customer struct but does not enforce these constraints during route construction. This feature will add service time tracking and enforce time window constraints in the Nearest Neighbor heuristic using a provided travel time matrix, enabling integration with real road network data (OSRM/Valhalla/Google Maps).

## Glossary

- **VRP_Solver**: The Vehicle Routing Problem solver system that constructs delivery routes
- **Customer**: A delivery point with geographic location, demand, and time window constraints
- **Service_Time**: The duration (in minutes) required to unload/service a customer
- **Time_Window**: The valid time interval [start_window, end_window] during which a customer can be serviced
- **Arrival_Time**: The time when a vehicle arrives at a customer location
- **Current_Time**: The cumulative time tracked for a vehicle route, updated after each customer visit
- **Travel_Time_Matrix**: A 2D array (N×N) where cell [i][j] contains the actual driving time (in minutes) from location i to location j
- **Waiting_Time**: The duration a vehicle waits when arriving before a customer's start_window
- **Dashboard**: The Streamlit web interface for visualizing VRP solutions

## Requirements

### Requirement 1: Service Time Support

**User Story:** As a logistics planner, I want to specify service time for each customer, so that route planning accounts for the time spent unloading and servicing deliveries.

#### Acceptance Criteria

1. THE Customer struct SHALL include a `service_time` field representing service duration in minutes
2. WHEN a Customer object is constructed, THE VRP_Solver SHALL accept a service_time parameter
3. THE service_time field SHALL default to 0 if not specified
4. THE Python bindings SHALL expose the service_time field as a configurable parameter

### Requirement 2: Matrix-Based Travel Time

**User Story:** As a logistics planner, I want the solver to use real-world travel times from a time matrix, so that routes reflect actual road network conditions rather than straight-line distances.

#### Acceptance Criteria

1. THE VRP_Solver solve() method SHALL accept a `time_matrix` parameter as a 2D vector of doubles
2. WHEN calculating travel time between Customer A and Customer B, THE VRP_Solver SHALL retrieve the value from time_matrix[A.id][B.id]
3. THE VRP_Solver SHALL NOT use Haversine distance or assumed speeds for time calculations when time_matrix is provided
4. WHEN time_matrix is not provided, THE VRP_Solver SHALL fall back to the existing Haversine-based distance calculation for backward compatibility
5. THE time_matrix SHALL contain travel times in minutes for all customer pairs

### Requirement 3: Time Window Constraint Enforcement

**User Story:** As a logistics planner, I want routes to respect customer time windows, so that deliveries arrive when customers are available.

#### Acceptance Criteria

1. WHEN evaluating if a customer can be added to a route, THE VRP_Solver SHALL calculate arrival_time as current_time + time_matrix[current_location][candidate_customer]
2. IF arrival_time > end_window, THEN THE VRP_Solver SHALL reject the customer
3. WHEN arrival_time < start_window, THE VRP_Solver SHALL allow the customer and account for waiting time
4. WHEN arrival_time is within [start_window, end_window], THE VRP_Solver SHALL allow the customer without waiting
5. THE canAddToRoute method SHALL validate time window constraints before accepting a customer

### Requirement 4: Route Time Tracking

**User Story:** As a logistics planner, I want the solver to track cumulative time during route construction, so that time window constraints can be validated accurately.

#### Acceptance Criteria

1. WHEN constructing a route, THE VRP_Solver SHALL maintain a current_time variable initialized to 0
2. WHEN a customer is added to a route, THE VRP_Solver SHALL calculate waiting_time as max(0, start_window - arrival_time)
3. WHEN a customer is added to a route, THE VRP_Solver SHALL update current_time as arrival_time + waiting_time + service_time
4. THE current_time SHALL represent the time when the vehicle departs from the current customer
5. THE VRP_Solver SHALL use current_time when calculating arrival_time for the next customer

### Requirement 5: Dashboard Travel Time Matrix Generation

**User Story:** As a dashboard user, I want the dashboard to generate a travel time matrix, so that the solver can use realistic travel times for route planning.

#### Acceptance Criteria

1. THE Dashboard SHALL generate a travel time matrix for all customer pairs before calling the solver
2. WHEN generating the travel time matrix in Phase 1 (MVP), THE Dashboard SHALL use Haversine distance divided by 40 km/h to calculate travel times
3. THE Dashboard SHALL convert travel times to minutes before passing to the solver
4. THE Dashboard SHALL ensure the time_matrix dimensions match the number of customers (N×N matrix)
5. THE Dashboard architecture SHALL be extensible to integrate with OSRM or Valhalla APIs in Phase 2 without modifying C++ code

### Requirement 6: Dashboard Service Time and Arrival Time Display

**User Story:** As a dashboard user, I want to specify service times and see arrival times for each customer, so that I can model and verify realistic delivery scenarios.

#### Acceptance Criteria

1. WHEN displaying customer data in the Dashboard, THE Dashboard SHALL include a "Service Time" column
2. WHEN generating demo data, THE Dashboard SHALL assign a default service_time of 10 minutes to each customer
3. WHEN loading CSV data, THE Dashboard SHALL read service_time from the CSV file if present
4. WHEN service_time is missing from CSV, THE Dashboard SHALL use a default value of 10 minutes
5. WHEN displaying route details, THE Dashboard SHALL show arrival_time for each customer in minutes from start of day
6. WHEN a vehicle waits at a customer, THE Dashboard SHALL display the waiting_time duration
7. THE Dashboard SHALL highlight customers where waiting occurred with a visual indicator

### Requirement 7: Python API Updates

**User Story:** As a Python developer, I want the solve() method to accept a time matrix parameter, so that I can provide real-world travel times to the solver.

#### Acceptance Criteria

1. THE solve() method in bindings.cpp SHALL accept a time_matrix parameter as a named argument
2. THE time_matrix parameter SHALL be optional to maintain backward compatibility
3. WHEN time_matrix is not provided, THE VRP_Solver SHALL fall back to the existing Haversine-based distance calculation
4. THE Python bindings SHALL validate that time_matrix dimensions match the number of customers
5. THE Python bindings SHALL convert Python nested lists or numpy arrays to C++ vector<vector<double>> format
