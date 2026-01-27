# Requirements Document

## Introduction

This document specifies the requirements for a High-Frequency Logistics Dashboard that provides a professional web-based interface for visualizing Vehicle Routing Problem (VRP) solutions. The dashboard integrates with an existing C++ VRP solver (vrp_core module) and provides interactive map-based visualization of routing solutions using Streamlit and Deck.gl.

## Glossary

- **Dashboard**: The Streamlit web application that provides the user interface
- **VRP_Solver**: The existing C++ solver module (vrp_core) with Python bindings
- **Customer**: A delivery location with coordinates, demand, and time windows
- **Route**: A sequence of customer visits assigned to a single vehicle
- **Deck.gl**: A WebGL-powered visualization framework for large-scale data
- **DLL_Path_Fix**: Windows-specific code to resolve dynamic library loading issues
- **Demo_Dataset**: Pre-configured sample data for immediate dashboard functionality

## Requirements

### Requirement 1: Dashboard Application Structure

**User Story:** As a logistics operator, I want a professional web-based dashboard, so that I can access the VRP solver through an intuitive interface.

#### Acceptance Criteria

1. THE Dashboard SHALL be implemented as a Streamlit application with the entry point at `dashboard/app.py`
2. WHEN the Dashboard starts, THE Dashboard SHALL apply a wide layout configuration and dark theme
3. THE Dashboard SHALL display "High-Frequency Logistics" branding in the title
4. WHERE the operating system is Windows, THE Dashboard SHALL include the DLL path fix before importing vrp_core
5. THE Dashboard SHALL organize controls in a sidebar and visualization in the main area

### Requirement 2: Windows DLL Path Resolution

**User Story:** As a Windows user, I want the dashboard to load the C++ solver module correctly, so that I can use the application without manual configuration.

#### Acceptance Criteria

1. WHEN running on Windows (os.name == 'nt'), THE Dashboard SHALL add the build/Release directory to the DLL search path
2. WHEN running on Windows, THE Dashboard SHALL add the build/Release directory to sys.path
3. THE Dashboard SHALL execute the DLL path fix before any vrp_core import statements
4. IF the build/Release directory does not exist, THEN THE Dashboard SHALL handle the missing path gracefully

### Requirement 3: Input Parameter Controls

**User Story:** As a logistics operator, I want to configure vehicle parameters, so that I can solve routing problems with different constraints.

#### Acceptance Criteria

1. THE Dashboard SHALL provide a number input for vehicle capacity with a minimum value of 1
2. THE Dashboard SHALL provide a number input for number of vehicles with a minimum value of 1
3. THE Dashboard SHALL display all input controls in the sidebar
4. WHEN input values change, THE Dashboard SHALL preserve the values until explicitly modified

### Requirement 4: Customer Data Management

**User Story:** As a logistics operator, I want to load customer data from CSV files, so that I can solve routing problems for my delivery locations.

#### Acceptance Criteria

1. THE Dashboard SHALL provide a file uploader accepting CSV format
2. WHEN no file is uploaded, THE Dashboard SHALL use a demo dataset with 5-10 customers
3. THE Demo_Dataset SHALL contain customer locations in the Mumbai/Bandra geographic area
4. THE Demo_Dataset SHALL include valid latitude, longitude, demand, and time window values
5. WHEN a CSV file is uploaded, THE Dashboard SHALL parse it into a pandas DataFrame
6. THE Dashboard SHALL validate that uploaded CSV contains required columns (id, lat, lon, demand, start_window, end_window)

### Requirement 5: VRP Solver Integration

**User Story:** As a logistics operator, I want to execute the VRP solver with my parameters, so that I can generate optimized delivery routes.

#### Acceptance Criteria

1. THE Dashboard SHALL provide a "Run Solver" button to trigger route calculation
2. WHEN the "Run Solver" button is clicked, THE Dashboard SHALL convert DataFrame rows to vrp_core.Customer objects
3. WHEN the "Run Solver" button is clicked, THE Dashboard SHALL create a VRP_Solver instance with the specified capacity and vehicle count
4. WHEN the "Run Solver" button is clicked, THE Dashboard SHALL call the solve() method and capture the returned routes
5. THE Dashboard SHALL measure and record the execution time of the solve() method call
6. IF the solver returns an error, THEN THE Dashboard SHALL display an error message to the user

### Requirement 6: Route Visualization

**User Story:** As a logistics operator, I want to see routes visualized on an interactive map, so that I can understand the routing solution spatially.

#### Acceptance Criteria

1. THE Dashboard SHALL render an interactive map using pydeck
2. THE Dashboard SHALL display all customer locations as scatter plot markers
3. THE Dashboard SHALL size customer markers proportionally to their demand values
4. THE Dashboard SHALL color customer markers in red
5. THE Dashboard SHALL render route paths connecting customers in sequence
6. THE Dashboard SHALL assign a unique color to each vehicle's route (Route 1: Cyan, Route 2: Magenta, Route 3: Yellow, etc.)
7. THE Dashboard SHALL support map zoom and pan interactions
8. THE Dashboard SHALL center the map view on the customer locations

### Requirement 7: Performance Metrics Display

**User Story:** As a logistics operator, I want to see solver performance metrics, so that I can understand the computational efficiency.

#### Acceptance Criteria

1. WHEN the solver completes execution, THE Dashboard SHALL display the execution time in milliseconds
2. THE Dashboard SHALL present the execution time as a prominent metric card
3. THE Dashboard SHALL update the execution time display after each solver run
4. THE Dashboard SHALL format the execution time with appropriate precision (e.g., 2 decimal places)

### Requirement 8: Data Type Conversion

**User Story:** As a system integrator, I want seamless data conversion between Python and C++, so that the dashboard can communicate with the solver correctly.

#### Acceptance Criteria

1. THE Dashboard SHALL convert pandas DataFrame rows to vrp_core.Customer objects with correct field mapping
2. THE Dashboard SHALL convert solver output (route indices) back to geographic coordinates
3. THE Dashboard SHALL handle customer ID mapping between DataFrame indices and route indices
4. THE Dashboard SHALL preserve all customer attributes during conversion (demand, start_window, end_window)

### Requirement 9: Dependency Management

**User Story:** As a developer, I want clear dependency specifications, so that I can set up the dashboard environment correctly.

#### Acceptance Criteria

1. THE Dashboard SHALL require streamlit as a runtime dependency
2. THE Dashboard SHALL require pydeck as a runtime dependency
3. THE Dashboard SHALL require pandas as a runtime dependency
4. THE Dashboard SHALL require numpy as a runtime dependency
5. THE Dashboard SHALL require the vrp_core module (C++ solver with Python bindings)
6. THE Dashboard SHALL document all dependencies in a requirements.txt or similar file

### Requirement 10: Professional Appearance

**User Story:** As a logistics operator, I want a professional-looking interface, so that the dashboard is suitable for operational use.

#### Acceptance Criteria

1. THE Dashboard SHALL use a dark color theme throughout the interface
2. THE Dashboard SHALL use consistent spacing and alignment for all UI elements
3. THE Dashboard SHALL use clear, readable typography
4. THE Dashboard SHALL provide visual feedback for interactive elements (buttons, inputs)
5. THE Dashboard SHALL organize information hierarchically with clear visual grouping
