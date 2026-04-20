# Product Overview

This is a professional-grade Vehicle Routing Problem (VRP) solver implemented in pure Python. The solver addresses Capacitated VRP (CVRP) and VRP with Time Windows (VRPTW) using a Nearest Neighbor heuristic.

## Core Capabilities

- Solve vehicle routing problems with capacity constraints
- Support time window constraints for customer visits
- Calculate geographic distances using Haversine formula
- Generate feasible delivery routes for heterogeneous fleets (different vehicle capacities)
- Python-native implementation for easy integration and deployment

## Design Philosophy

The system is designed for ease of use, maintainability, and cross-platform compatibility. The pure Python implementation prioritizes:

- **Simplicity**: No compilation, no build tools, just Python
- **Portability**: Works on any platform with Python 3.8+
- **Maintainability**: Clear, readable code that's easy to modify
- **Extensibility**: Architecture supports future enhancements

Future enhancements may include:
- Advanced metaheuristics (genetic algorithms, simulated annealing)
- Performance optimization with NumPy/Numba
- Additional constraint types
- Multi-depot routing

## Key Constraints

- **Vehicle capacity**: Routes cannot exceed specified capacity
- **Time windows**: Customers must be visited within their service windows
- **Depot-based**: All routes start and end at depot (customer 0)
- **Heterogeneous fleet**: Different vehicles can have different capacities

## Use Cases

- Last-mile delivery optimization
- Field service routing
- Logistics planning
- Supply chain optimization
- Fleet management

