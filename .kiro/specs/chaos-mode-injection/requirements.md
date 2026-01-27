# Requirements Document: Dynamic Event Injection (Chaos Mode)

## Introduction

This document specifies the requirements for "Chaos Mode" (Dynamic Re-routing). This feature demonstrates the system's "High-Frequency" capabilities by allowing users to inject new, random emergency orders into the system in real-time. The solver must accept this new state and re-optimize all routes in sub-millisecond time, proving its suitability for event-driven environments.

## Glossary

- **Dynamic_Re-routing**: The ability to update routes instantly when new data arrives
- **Chaos_Mode**: A feature flag that injects random constraints or customers to stress-test the solver
- **Emergency_Order**: A new customer added with tight time windows and high priority
- **Re-optimization_Latency**: The time taken to calculate new routes after an injection event (Target: < 10ms)
- **Dashboard**: The Streamlit web interface for visualizing and controlling the VRP solver
- **OSRM**: Open Source Routing Machine - external service for real-world distance calculations
- **Session_State**: Streamlit's mechanism for persisting data across page interactions

## Requirements

### Requirement 1: Emergency Order Injection

**User Story:** As a fleet manager, I want to inject a new order instantly, so I can see how the fleet adapts to unexpected demand.

#### Acceptance Criteria

1. THE Dashboard SHALL display a button labeled "🚨 Inject Emergency Order" in the sidebar
2. WHEN the button is clicked, THE Dashboard SHALL generate a new random Customer with the following properties:
   - Location: Randomly selected within the bounding box of existing customers
   - Demand: Random integer between 1 and 5
   - Time Window: A valid window that fits within the current schedule (current time + 30 minutes)
   - Service Time: 5 minutes for priority handling
3. THE Dashboard SHALL append this new customer to the existing customer list
4. WHEN a new customer is added, THE Dashboard SHALL immediately trigger solve_routing() with the updated list

### Requirement 2: Visual Feedback and Performance Monitoring

**User Story:** As a user, I want to see the system's reaction speed, so I can verify its "High-Frequency" nature.

#### Acceptance Criteria

1. WHEN re-optimization is complete, THE Dashboard SHALL display a toast notification showing the re-calculation time in milliseconds
2. THE Dashboard SHALL highlight the new Emergency Order on the map using a distinct visual marker
3. THE Dashboard SHALL clearly show which vehicle route was modified to handle the new order
4. THE Dashboard SHALL display performance metrics including re-optimization latency

### Requirement 3: System Stability and Integration

**User Story:** As a developer, I want to ensure dynamic updates don't break existing logic.

#### Acceptance Criteria

1. THE Injection logic SHALL respect the OSRM/Fallback distance calculation toggle
2. WHEN OSRM is active, THE Dashboard SHALL fetch updated distance matrix data for the new customer
3. THE Dashboard SHALL preserve the existing DLL loading configuration for Windows compatibility
4. IF the new order makes the problem infeasible, THE Dashboard SHALL return the best possible partial solution and display a warning message to the user

### Requirement 4: State Management and Persistence

**User Story:** As a user, I want the injected order to persist until I reset the simulation.

#### Acceptance Criteria

1. THE Dashboard SHALL use Streamlit session_state to track the list of dynamic customers
2. WHEN the page refreshes or "Run Solver" is clicked, THE Dashboard SHALL preserve all injected customers
3. THE Dashboard SHALL provide a "Reset Simulation" button to clear all injected orders
4. WHEN "Reset Simulation" is clicked, THE Dashboard SHALL return to the initial state with only the original customers
