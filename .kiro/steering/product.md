# Product Overview

This is a professional-grade Vehicle Routing Platform built with pure Python. The platform provides a complete operational control tower for logistics operations, featuring multi-workspace interfaces for dispatchers, warehouse staff, drivers, customers, and administrators.

## Core Capabilities

### Routing Engine
- Multi-depot vehicle routing with capacity and time window constraints
- Heterogeneous fleet support (different vehicle types and capacities)
- Break scheduling and shift time enforcement
- Traffic incident awareness with dynamic route penalties
- Regret insertion heuristic with local search optimization (2-opt, relocate, swap, cross-exchange)
- Configurable objective functions (distance, time, cost, emissions, load balance)

### Platform Features
- **Dispatcher Control Tower**: Manifest intake, filtered planning, scenario preview, route board
- **Warehouse Operations**: Load sheets, dock assignments, shipment tracking
- **Driver Workflow**: Route execution, turn-by-turn navigation, incident reporting
- **Customer Portal**: Shipment lookup and tracking
- **Admin Dashboard**: Audit logs, system monitoring, configuration management

### Data Persistence
- SQLAlchemy-based persistence layer
- SQLite for local development
- PostgreSQL-ready for production
- Event sourcing for audit trails

## Design Philosophy

The platform is designed for operational excellence, maintainability, and scalability:

- **Pure Python**: No compilation, no build tools, works everywhere
- **Domain-Driven Design**: Clear separation between domain entities, services, and infrastructure
- **Event-Driven**: Audit trail and operational visibility through event logging
- **Modular Architecture**: Pluggable travel providers, objective functions, and constraints
- **Production-Ready**: Queue-backed workers, Redis integration, comprehensive error handling

## Key Constraints

The optimizer handles:
- **Vehicle capacity**: Weight (kg) and volume (m³) constraints
- **Time windows**: Customer service windows and vehicle shift times
- **Break requirements**: Mandatory breaks after continuous driving
- **Depot assignments**: Multi-depot routing with depot-specific fleets
- **Vehicle restrictions**: Dimension limits, fuel type, special equipment requirements
- **Traffic incidents**: Dynamic penalties for affected road segments

## Use Cases

- Last-mile delivery operations
- Field service dispatch
- Multi-depot logistics coordination
- Warehouse load planning
- Real-time route monitoring and adjustment
- Customer shipment tracking
- Operational audit and compliance

