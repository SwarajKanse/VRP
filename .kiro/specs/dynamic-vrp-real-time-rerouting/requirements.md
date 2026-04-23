# Requirements Document: Dynamic VRP (Real-Time Re-routing)

## Introduction

This document specifies requirements for the Dynamic VRP (Real-Time Re-routing) feature, which enables emergency order injection and route re-optimization while vehicles are actively executing their routes. This capability is critical for operational logistics where urgent orders arrive after trucks have departed, requiring minimal disruption to existing routes while accommodating high-priority deliveries.

The feature integrates with the existing RouteOptimizer engine, PlanningService orchestration layer, and event logging system to provide seamless real-time route adjustments with full audit trails and driver notifications.

## Glossary

- **Emergency_Order**: An urgent order that arrives after route execution has begun and requires immediate insertion into an active route
- **Route_State**: The current execution state of a route, including which stops are completed, in-progress, or pending
- **Pending_Stops**: Stops in a route that have not yet been visited by the driver
- **Completed_Stops**: Stops that have been visited and marked as delivered or attempted
- **Re_Optimizer**: The component responsible for re-optimizing routes with frozen completed stops and new emergency orders
- **Insertion_Cost**: The additional distance, time, and operational cost incurred by inserting an emergency order into a route
- **Driver_Notification_Service**: The service responsible for pushing updated route information to driver devices
- **Rerouting_Event**: An audit log entry capturing the decision, reason, and impact of a route re-optimization
- **Cost_Impact_Analysis**: A comparison showing the operational cost difference between accepting and rejecting an emergency order
- **Feasibility_Check**: Validation that an emergency order can be inserted while respecting all constraints (capacity, time windows, shifts, breaks)
- **Minimal_Disruption_Strategy**: The algorithm for selecting the route and insertion position that causes the least delay to existing stops
- **Route_Snapshot**: A frozen copy of a route's state at the moment re-optimization begins
- **Incremental_Optimization**: Re-optimization that only modifies pending stops, preserving completed stops in their original sequence

## Requirements

### Requirement 1: Emergency Order Injection

**User Story:** As a dispatcher, I want to mark an order as "emergency" and inject it into active routes, so that I can accommodate urgent customer requests without manual route reconstruction.

#### Acceptance Criteria

1. WHEN a dispatcher marks an order as emergency, THE System SHALL validate the order has all required fields (location, demand, time window, service time)
2. WHEN an emergency order is submitted, THE System SHALL identify all routes with status "dispatched" or "in_transit"
3. THE System SHALL reject emergency orders with demand exceeding the maximum vehicle capacity across the entire fleet
4. THE System SHALL reject emergency orders with volume exceeding the maximum vehicle cargo volume across the entire fleet
5. WHEN an emergency order is validated, THE System SHALL trigger the feasibility analysis for all active routes

### Requirement 2: Route State Preservation

**User Story:** As a system, I want to freeze the current route execution state before re-optimization, so that completed stops are never modified or reordered.

#### Acceptance Criteria

1. WHEN re-optimization begins, THE System SHALL capture a Route_Snapshot containing all stops with their current status
2. THE System SHALL classify each stop as completed, in-progress, or pending based on delivery events
3. THE System SHALL preserve completed stops in their original sequence and position
4. THE System SHALL preserve in-progress stops in their current position
5. THE System SHALL only allow re-optimization of pending stops
6. THE System SHALL maintain the original depot return as the final stop if no pending stops exist after the in-progress stop

### Requirement 3: Incremental Re-optimization

**User Story:** As a system, I want to re-optimize only the pending portion of routes, so that I minimize computational cost and preserve driver progress.

#### Acceptance Criteria

1. WHEN re-optimization is triggered, THE Re_Optimizer SHALL receive the list of pending stops plus the emergency order
2. THE Re_Optimizer SHALL treat the last completed or in-progress stop as the new starting point
3. THE Re_Optimizer SHALL apply all existing constraints (capacity, time windows, breaks, shifts) to the pending portion
4. THE Re_Optimizer SHALL calculate remaining vehicle capacity based on completed stops
5. THE Re_Optimizer SHALL adjust time window feasibility based on current time and vehicle position
6. THE Re_Optimizer SHALL use regret insertion and local search on the pending stops only
7. THE Re_Optimizer SHALL return updated stop sequences with recalculated arrival times and distances

### Requirement 4: Minimal Disruption Strategy

**User Story:** As a dispatcher, I want the system to recommend the route with the least disruption, so that I can minimize delays to existing customers.

#### Acceptance Criteria

1. FOR ALL active routes, THE System SHALL calculate the Insertion_Cost for the emergency order
2. THE System SHALL evaluate insertion at every position in the pending stops sequence
3. THE System SHALL calculate added distance, added drive time, and lateness impact for each insertion position
4. THE System SHALL rank routes by total disruption score (weighted sum of distance, time, and lateness)
5. THE System SHALL return the top 3 candidate routes with their insertion positions and cost impacts
6. WHERE no feasible insertion exists, THE System SHALL report the specific constraint violation (capacity, time window, shift limit)

### Requirement 5: Cost Impact Analysis

**User Story:** As a dispatcher, I want to see the cost impact of accepting an emergency order, so that I can make informed business decisions.

#### Acceptance Criteria

1. WHEN feasible insertions are found, THE System SHALL calculate the baseline cost of the route without the emergency order
2. THE System SHALL calculate the new cost of the route with the emergency order inserted
3. THE System SHALL display the cost difference including distance cost, labor cost, fuel cost, and emissions cost
4. THE System SHALL display the delay impact on existing stops (number of stops delayed, maximum delay in minutes)
5. THE System SHALL display the new route completion time and any overtime implications
6. THE System SHALL display the emergency order's time window compliance status after insertion

### Requirement 6: Driver Notification

**User Story:** As a driver, I want to receive updated route information immediately after re-optimization, so that I can adjust my navigation and schedule.

#### Acceptance Criteria

1. WHEN a dispatcher approves an emergency order insertion, THE Driver_Notification_Service SHALL push the updated route to the assigned driver
2. THE Driver_Notification_Service SHALL include the new stop sequence with updated ETAs
3. THE Driver_Notification_Service SHALL highlight the newly inserted stop
4. THE Driver_Notification_Service SHALL include the reason for the route change
5. THE Driver_Notification_Service SHALL update the driver's navigation with the new route geometry
6. WHEN the driver's device is offline, THE System SHALL queue the notification for delivery when connectivity is restored

### Requirement 7: Customer ETA Updates

**User Story:** As a customer, I want to receive updated delivery ETAs when my order is affected by re-routing, so that I can plan accordingly.

#### Acceptance Criteria

1. WHEN a route is re-optimized, THE System SHALL identify all orders with changed ETAs
2. FOR ALL orders with ETA changes exceeding 15 minutes, THE System SHALL publish a customer notification event
3. THE System SHALL include the new ETA and the reason for the change in the notification
4. THE System SHALL publish a notification for the newly inserted emergency order with its confirmed ETA
5. THE System SHALL record all customer notifications in the event log

### Requirement 8: Audit Trail

**User Story:** As an administrator, I want a complete audit trail of all re-routing decisions, so that I can analyze operational patterns and compliance.

#### Acceptance Criteria

1. WHEN re-optimization is triggered, THE System SHALL create a Rerouting_Event with a unique event ID
2. THE Rerouting_Event SHALL capture the trigger reason (emergency order, traffic incident, driver request)
3. THE Rerouting_Event SHALL capture the emergency order ID and details
4. THE Rerouting_Event SHALL capture the selected route ID and insertion position
5. THE Rerouting_Event SHALL capture the cost impact analysis results
6. THE Rerouting_Event SHALL capture the dispatcher who approved the change
7. THE Rerouting_Event SHALL capture the timestamp of the decision
8. THE Rerouting_Event SHALL capture the list of affected orders with old and new ETAs

### Requirement 9: Constraint Enforcement

**User Story:** As a system, I want to enforce all existing routing constraints during re-optimization, so that route quality and compliance are maintained.

#### Acceptance Criteria

1. THE Re_Optimizer SHALL enforce vehicle capacity constraints using remaining capacity after completed stops
2. THE Re_Optimizer SHALL enforce time window constraints for all pending stops and the emergency order
3. THE Re_Optimizer SHALL enforce shift time limits based on elapsed time and remaining shift duration
4. THE Re_Optimizer SHALL enforce break requirements based on continuous drive time since the last break
5. THE Re_Optimizer SHALL enforce vehicle dimension constraints for the emergency order
6. THE Re_Optimizer SHALL respect traffic incident penalties when recalculating travel times
7. WHERE any constraint is violated, THE Re_Optimizer SHALL exclude that insertion option from the candidate list

### Requirement 10: Asynchronous Processing

**User Story:** As a dispatcher, I want re-optimization to run asynchronously for complex scenarios, so that the UI remains responsive during computation.

#### Acceptance Criteria

1. WHEN re-optimization is expected to take longer than 2 seconds, THE System SHALL queue the task using Redis and RQ
2. THE System SHALL return a task ID to the dispatcher immediately
3. THE System SHALL display a progress indicator in the dispatcher UI
4. WHEN the re-optimization completes, THE System SHALL notify the dispatcher with the results
5. WHEN the re-optimization fails, THE System SHALL log the error and notify the dispatcher with a user-friendly message
6. THE System SHALL allow the dispatcher to cancel a queued re-optimization task

### Requirement 11: Rollback Capability

**User Story:** As a dispatcher, I want to undo a re-routing decision if it was made in error, so that I can restore the original route plan.

#### Acceptance Criteria

1. WHEN a route is re-optimized, THE System SHALL store the previous route plan with a version number
2. THE System SHALL provide a rollback action in the dispatcher UI for routes modified within the last 30 minutes
3. WHEN a dispatcher initiates rollback, THE System SHALL restore the previous route plan
4. THE System SHALL send updated notifications to the driver with the restored route
5. THE System SHALL send updated ETA notifications to affected customers
6. THE System SHALL log the rollback action in the audit trail with the reason

### Requirement 12: Multi-Order Emergency Batch

**User Story:** As a dispatcher, I want to inject multiple emergency orders simultaneously, so that I can efficiently handle bulk urgent requests.

#### Acceptance Criteria

1. THE System SHALL accept a batch of up to 10 emergency orders in a single request
2. THE Re_Optimizer SHALL evaluate all emergency orders together for optimal insertion
3. THE System SHALL attempt to assign emergency orders to minimize the total number of affected routes
4. THE System SHALL display the combined cost impact of all emergency orders
5. THE System SHALL allow the dispatcher to approve or reject the entire batch
6. WHERE some orders cannot be feasibly inserted, THE System SHALL report which orders failed and why

### Requirement 13: Conflict Detection

**User Story:** As a system, I want to detect conflicting re-optimization requests, so that I prevent race conditions and data corruption.

#### Acceptance Criteria

1. WHEN a re-optimization request is received, THE System SHALL check if the target route has a pending re-optimization task
2. WHERE a conflict is detected, THE System SHALL reject the new request with a clear error message
3. THE System SHALL provide the dispatcher with the option to cancel the pending task and submit a new one
4. THE System SHALL use optimistic locking to prevent concurrent modifications to the same route
5. WHERE a route is modified by another dispatcher during re-optimization, THE System SHALL invalidate the results and notify the user

### Requirement 14: Performance Monitoring

**User Story:** As an administrator, I want to monitor re-optimization performance metrics, so that I can identify bottlenecks and optimize system capacity.

#### Acceptance Criteria

1. THE System SHALL record the computation time for each re-optimization task
2. THE System SHALL record the number of routes evaluated and insertion positions tested
3. THE System SHALL record the queue wait time for asynchronous tasks
4. THE System SHALL expose performance metrics in the admin dashboard
5. THE System SHALL alert administrators when re-optimization tasks exceed 10 seconds
6. THE System SHALL provide a breakdown of time spent in feasibility checking, cost calculation, and local search

### Requirement 15: Fallback Strategy

**User Story:** As a system, I want a fallback strategy when re-optimization fails, so that dispatchers can still handle emergency orders manually.

#### Acceptance Criteria

1. WHEN the Re_Optimizer fails with an exception, THE System SHALL log the error with full context
2. THE System SHALL return a fallback response showing all active routes without optimization
3. THE System SHALL allow the dispatcher to manually select a route and insertion position
4. THE System SHALL validate the manual insertion for constraint violations
5. THE System SHALL apply the manual insertion if feasible, or report violations if not
6. THE System SHALL log manual insertions in the audit trail with a "manual_override" flag

