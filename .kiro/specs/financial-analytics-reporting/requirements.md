# Requirements Document: Financial Analytics & Reporting

## Introduction

This document specifies the requirements for adding a "Business Intelligence" layer to the VRP Dashboard. Currently, the system displays technical metrics (execution time, routes on a map). This feature extends the dashboard to show financial metrics (cost, efficiency) and operational tools (export), transforming the tool from a solver into a fleet management product.

The Financial Analytics & Reporting feature provides fleet managers with cost visibility, operational insights, and driver manifest generation capabilities. This enables data-driven decision-making for fleet operations and budget planning.

## Glossary

- **Dashboard**: The Streamlit-based web application that visualizes VRP solutions
- **Fuel_Cost**: Cost incurred based on distance traveled (Default: ₹100/liter, 10 km/liter)
- **Driver_Wage**: Hourly cost for fleet operation (Default: ₹500/hour)
- **Manifest**: A detailed schedule for a specific driver to follow, including stop sequence and timing
- **KPI**: Key Performance Indicators (Cost per km, Cost per Delivery)
- **Total_Distance**: Sum of all travel distances across all routes in kilometers
- **Total_Duration**: Sum of all time spent including travel time, service time, and waiting time in hours
- **Route**: A sequence of customer visits assigned to a single vehicle
- **OSRM**: Open Source Routing Machine, used for calculating real-world travel distances and times
- **Time_Matrix**: N×N matrix containing travel times between all customer pairs

## Requirements

### Requirement 1: Financial Modeling Engine

**User Story:** As a fleet manager, I want to see the estimated cost of the routing plan so I can budget effectively.

#### Acceptance Criteria

1. WHEN a routing solution exists, THE Dashboard SHALL calculate Total_Distance in kilometers by summing distances for all routes using the distance matrix
2. WHEN a routing solution exists, THE Dashboard SHALL calculate Total_Duration in hours by summing travel time, service time, and waiting time for all routes
3. THE Dashboard SHALL compute Fuel_Cost using the formula: (Total_Distance / Vehicle_Mileage) * Fuel_Price
4. THE Dashboard SHALL compute Labor_Cost using the formula: Total_Duration * Driver_Wage
5. THE Dashboard SHALL compute Total_Cost as the sum of Fuel_Cost and Labor_Cost
6. THE Dashboard SHALL display these financial metrics in a "Financial Overview" section using Streamlit metric components
7. WHEN no routing solution exists, THE Dashboard SHALL NOT display the Financial Overview section

### Requirement 2: Interactive Cost Configurator

**User Story:** As a user, I want to adjust cost assumptions to match my real-world scenario.

#### Acceptance Criteria

1. THE Dashboard SHALL provide an "Operations Config" expander in the sidebar
2. THE Configurator SHALL provide a number input for Fuel_Price with default value ₹100 per liter
3. THE Configurator SHALL provide a number input for Vehicle_Mileage with default value 10 km per liter
4. THE Configurator SHALL provide a number input for Driver_Wage with default value ₹500 per hour
5. WHEN any cost parameter changes, THE Dashboard SHALL recalculate all financial metrics without re-running the solver
6. THE Configurator SHALL validate that all input values are positive numbers greater than zero

### Requirement 3: Operational Reporting (Export)

**User Story:** As a driver, I need a file telling me where to go.

#### Acceptance Criteria

1. WHEN a routing solution exists, THE Dashboard SHALL generate a structured DataFrame containing Route_ID, Stop_Number, Customer_ID, Arrival_Time, and Action columns
2. THE Dashboard SHALL provide a "Download Driver Manifests" button in the sidebar
3. WHEN the download button is clicked, THE Dashboard SHALL generate a CSV file named "fleet_manifest_{timestamp}.csv"
4. THE CSV file SHALL contain all route information in a format suitable for driver use
5. WHEN no routing solution exists, THE download button SHALL be disabled

### Requirement 4: Visual Cost Analysis

**User Story:** As a manager, I want to see which routes are the most expensive.

#### Acceptance Criteria

1. WHEN a routing solution exists, THE Dashboard SHALL calculate cost per route by summing fuel cost and labor cost for each individual route
2. THE Dashboard SHALL display a bar chart comparing cost across all routes
3. THE Bar_Chart SHALL show Route_ID on the x-axis and Cost on the y-axis
4. THE Bar_Chart SHALL use a color scheme that distinguishes between routes
5. WHEN no routing solution exists, THE Dashboard SHALL NOT display the cost analysis chart

### Requirement 5: Per-Route Financial Metrics

**User Story:** As a fleet manager, I want to see detailed financial breakdown for each route so I can identify inefficiencies.

#### Acceptance Criteria

1. WHEN a routing solution exists, THE Dashboard SHALL calculate distance for each individual route
2. WHEN a routing solution exists, THE Dashboard SHALL calculate duration for each individual route
3. WHEN a routing solution exists, THE Dashboard SHALL calculate fuel cost for each individual route
4. WHEN a routing solution exists, THE Dashboard SHALL calculate labor cost for each individual route
5. THE Dashboard SHALL calculate Cost_Per_Kilometer as Total_Cost divided by Total_Distance
6. THE Dashboard SHALL calculate Cost_Per_Delivery as Total_Cost divided by number of customers served
7. THE Dashboard SHALL display these KPIs in the Financial Overview section

### Requirement 6: Integration with Existing Dashboard

**User Story:** As a developer, I want the financial features to integrate seamlessly with the existing dashboard architecture.

#### Acceptance Criteria

1. THE Financial_Analytics module SHALL use the existing time_matrix from session state for distance calculations
2. THE Financial_Analytics module SHALL use the existing routes from session state for cost calculations
3. THE Financial_Analytics module SHALL preserve the existing DLL loading configuration for Windows compatibility
4. WHEN chaos mode is active, THE Financial_Analytics module SHALL recalculate costs based on the updated routes
5. THE Financial_Analytics module SHALL follow the existing code organization patterns in the dashboard
