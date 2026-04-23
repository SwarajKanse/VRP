# Project Structure

## Directory Layout

```
vrp-platform/
├── .kiro/
│   ├── specs/                    # Feature specifications (legacy)
│   └── steering/                 # AI assistant guidance documents
├── src/
│   └── vrp_platform/
│       ├── domain/               # Domain entities and enums
│       │   ├── entities.py       # Order, Vehicle, Depot, Route, etc.
│       │   └── enums.py          # Status codes and type enums
│       ├── optimizer/            # Route optimization engine
│       │   ├── engine.py         # Main optimizer with regret insertion
│       │   ├── objectives.py    # Objective function scoring
│       │   └── fallback.py      # Fallback strategies
│       ├── repos/                # Data persistence layer
│       │   ├── models.py         # SQLAlchemy models
│       │   ├── catalog.py        # Vehicles, depots, drivers
│       │   ├── orders.py         # Order management
│       │   ├── planning.py       # Routes and assignments
│       │   └── events.py         # Audit trail
│       ├── services/             # Business logic services
│       │   ├── planning.py       # Optimization orchestration
│       │   ├── ingestion.py      # Manifest processing
│       │   ├── operations.py     # Route execution
│       │   ├── manifests.py      # Manifest generation
│       │   ├── auth.py           # User management
│       │   └── events.py         # Event logging
│       ├── integrations/         # External integrations
│       │   └── travel.py         # Travel matrix providers
│       ├── ui/                   # NiceGUI web application
│       │   ├── app.py            # Main application entry point
│       │   └── theme.py          # UI theme configuration
│       ├── workers/              # Background job processing
│       │   ├── queue.py          # Queue management
│       │   └── tasks.py          # Task definitions
│       ├── bootstrap.py          # Application bootstrap
│       ├── config.py             # Configuration management
│       ├── db.py                 # Database initialization
│       └── logging.py            # Logging configuration
├── tests/
│   └── platform/                 # Platform integration tests
│       ├── test_optimizer_platform.py
│       ├── test_platform_operations.py
│       ├── test_resilience_and_auth.py
│       └── test_travel_and_loading.py
├── var/                          # Runtime data
│   └── vrp_platform.db           # SQLite database (dev)
├── test_installation.py          # Installation verification
├── setup.bat / setup.sh          # Platform setup scripts
├── run_dashboard.bat / run_dashboard.sh  # Quick launchers
├── pyproject.toml                # Project configuration
├── requirements.txt              # Python dependencies
├── sample_manifest.csv           # Example intake file
└── *.md                          # Documentation files
```

## Key Files

### Core Implementation

- **src/vrp_platform/optimizer/engine.py**: Pure Python VRP optimizer
  - `RouteOptimizer`: Main optimizer class with regret insertion and local search
  - Multi-depot assignment logic
  - Feasibility checking and constraint validation
  - Local search operators: 2-opt, relocate, swap, cross-exchange
  - Route metrics calculation (distance, time, cost, emissions)

- **src/vrp_platform/domain/entities.py**: Domain model
  - `Order`: Delivery order with location, demand, time windows
  - `Vehicle`: Vehicle with capacity, speed, fuel type, dimensions
  - `Depot`: Depot location with operating hours
  - `Route`: Planned route with stops and metrics
  - `SolveRequest` / `SolveResponse`: Optimization API

- **src/vrp_platform/services/planning.py**: Planning orchestration
  - Coordinates optimization runs
  - Manages scenario creation and comparison
  - Handles route assignment and publishing

### Web Application

- **src/vrp_platform/ui/app.py**: NiceGUI application
  - Multi-workspace routing (dispatcher, warehouse, driver, customer, admin)
  - Reactive UI components
  - Map visualizations
  - Real-time updates

### Data Persistence

- **src/vrp_platform/repos/models.py**: SQLAlchemy models
  - Database schema definitions
  - Relationships and constraints
  - Indexes for query performance

### Testing

- **tests/platform/**: Integration test suite
  - Property-based tests with hypothesis
  - End-to-end workflow tests
  - Resilience and error handling tests

### Configuration

- **pyproject.toml**: Modern Python project configuration
- **src/vrp_platform/config.py**: Environment-based settings with pydantic
- **test_installation.py**: Quick verification script

## Architecture Layers

### Layer 1: Domain Model (domain/)

Pure business entities with no infrastructure dependencies:
- `Order`, `Vehicle`, `Depot`, `Route`, `Stop`, `RouteLeg`
- `SolveRequest`, `SolveResponse`, `Violation`
- `ConstraintSet`, `ObjectiveWeights`
- Status enums and type codes

### Layer 2: Optimizer (optimizer/)

Route construction and improvement algorithms:
- Regret insertion heuristic for initial solution
- Local search operators (2-opt, relocate, swap, cross-exchange)
- Objective function scoring with configurable weights
- Constraint validation (capacity, time windows, breaks, shifts)
- Multi-depot assignment logic

### Layer 3: Services (services/)

Business logic orchestration:
- Planning service: optimization workflow
- Ingestion service: manifest parsing and validation
- Operations service: route execution and tracking
- Manifests service: load sheet and route document generation
- Auth service: user and role management
- Events service: audit logging

### Layer 4: Repositories (repos/)

Data access and persistence:
- SQLAlchemy models and queries
- Transaction management
- Read models for UI queries
- Event store for audit trail

### Layer 5: Integrations (integrations/)

External system interfaces:
- Travel matrix providers (Euclidean, road network)
- Traffic incident feeds
- Telematics APIs (future)

### Layer 6: UI (ui/)

Web application interface:
- NiceGUI reactive components
- Multi-workspace routing
- Map visualizations with route geometry
- Real-time status updates

### Layer 7: Workers (workers/)

Background job processing:
- Queue management with Redis/RQ
- Long-running optimization tasks
- Scheduled jobs (future)

## Code Organization Principles

1. **Pure Python**: No compilation required, works on any platform
2. **Domain-Driven Design**: Clear separation of concerns
3. **Dependency Inversion**: Domain layer has no infrastructure dependencies
4. **Event Sourcing**: Audit trail through event logging
5. **Modular Architecture**: Pluggable components (travel providers, objectives)
6. **Type Safety**: Comprehensive type hints with pydantic validation

## Module Import Structure

```python
# Domain entities
from vrp_platform.domain.entities import Order, Vehicle, Depot, SolveRequest
from vrp_platform.domain.enums import OrderStatus, VehicleType

# Optimizer
from vrp_platform.optimizer.engine import RouteOptimizer
from vrp_platform.integrations.travel import EuclideanTravelProvider

# Services
from vrp_platform.services.planning import PlanningService
from vrp_platform.services.ingestion import IngestionService

# Bootstrap
from vrp_platform.bootstrap import bootstrap_platform

# Create and run
app = bootstrap_platform()
response = app.solve_plan(request)
```

## Data Flow

1. **Manifest Intake**: CSV → IngestionService → Orders in DB
2. **Planning**: Orders → PlanningService → RouteOptimizer → Routes
3. **Assignment**: Routes → Warehouse → Load Sheets
4. **Execution**: Routes → Driver App → Status Updates
5. **Tracking**: Status → Events → Customer Portal
6. **Audit**: All actions → Event Store → Admin Dashboard

