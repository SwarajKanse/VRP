# Product Overview

This is a high-performance Vehicle Routing Problem (VRP) solver built in C++20 with Python bindings. The solver addresses Capacitated VRP (CVRP) and VRP with Time Windows (VRPTW) using a Nearest Neighbor heuristic.

## Core Capabilities

- Solve vehicle routing problems with capacity constraints
- Support time window constraints for customer visits
- Calculate geographic distances using Haversine formula
- Generate feasible delivery routes for multiple vehicles
- Python integration via Nanobind for easy scripting and testing

## Design Philosophy

The system is designed as a foundation for high-frequency trading style performance optimization. The current implementation prioritizes correctness and extensibility, with architecture that supports future enhancements:

- Data-Oriented Design (Struct of Arrays) for SIMD optimization
- Custom memory allocators (Linear/Arena allocators)
- Advanced metaheuristics beyond Nearest Neighbor

## Key Constraints

- Vehicle capacity: Routes cannot exceed specified capacity
- Time windows: Customers must be visited within their service windows
- Depot-based: All routes start and end at depot (customer 0)
