# VRP Platform Architecture

## Overview

The VRP Platform is a production-ready vehicle routing and logistics operations system built entirely in pure Python. It provides a complete operational control tower with multi-workspace interfaces for different user roles.

## Technology Stack

### Core Technologies

- **Language**: Python 3.11+
- **Web Framework**: NiceGUI (reactive web UI)
- **Database**: SQLAlchemy with SQLite (dev) / PostgreSQL (prod)
- **Queue System**: Redis + RQ for background jobs
- **Testing**: pytest with hypothesis for property-based testing

### Key Dependencies

- `nicegui`: Modern reactive web framework
- `sqlalchemy`: ORM and database abstraction
- `alembic`: Database migrations
- `pydantic`: Data validation and settings
- `pandas`: Data manipulation
- `redis` + `rq`: Queue backend and workers
- `reportlab`: PDF generation
- `requests`: HTTP client

## Architecture Layers

### 1. Domain Layer (`src/vrp_platform/domain/`)

Pure business entities with no infrastructure dependencies:

- **entities.py**: Core domain objects
  - `Order`: Delivery order with location, demand, time windows
  - `Vehicle`: Vehicle with capacity, speed, fuel type, dimensions
  - `Depot`: Depot location with operating hours
  - `Route`: Planned route with stops and metrics
  - `SolveRequest` / `SolveResponse`: Optimization API
  - `ConstraintSet`: Constraint configuration
  - `ObjectiveWeights`: Objective function weights

- **enums.py**: Status codes and type enums
  - `OrderStatus`, `RouteStatus`, `VehicleType`, etc.

### 2. Optimizer Layer (`src/vrp_platform/optimizer/`)

Route construction and improvement algorithms:

- **engine.py**: Main optimization engine
  - `RouteOptimizer`: Regret insertion + local search
  - Multi-depot assignment logic
  - Feasibility checking and constraint validation
  - Local search operators: 2-opt, relocate, swap, cross-exchange
  - Route metrics calculation

- **objectives.py**: Objective function scoring
  - Configurable weights for distance, time, cost, emissions
  - Load balancing and priority scoring

- **fallback.py**: Fallback strategies
  - Graceful degradation when optimization fails

### 3. Integration Layer (`src/vrp_platform/integrations/`)

External system interfaces:

- **travel.py**: Travel matrix providers
  - `EuclideanTravelProvider`: Straight-line distance
  - `RoadNetworkTravelProvider`: Road-based routing (future)
  - Traffic incident integration

### 4. Service Layer (`src/vrp_platform/services/`)

Business logic orchestration:

- **planning.py**: Optimization workflow
  - Scenario creation and comparison
  - Route assignment and publishing

- **ingestion.py**: Manifest processing
  - CSV parsing and validation
  - Order creation and enrichment

- **operations.py**: Route execution
  - Status tracking and updates
  - Driver assignment

- **manifests.py**: Document generation
  - Load sheets and route documents
  - PDF generation

- **auth.py**: User management
  - Authentication and authorization
  - Role-based access control

- **events.py**: Event logging
  - Audit trail and operational visibility

### 5. Repository Layer (`src/vrp_platform/repos/`)

Data access and persistence:

- **models.py**: SQLAlchemy models
  - Database schema definitions
  - Relationships and constraints

- **catalog.py**: Vehicles, depots, drivers
- **orders.py**: Order management
- **planning.py**: Routes and assignments
- **events.py**: Event store

### 6. UI Layer (`src/vrp_platform/ui/`)

Web application interface:

- **app.py**: NiceGUI application
  - Multi-workspace routing
  - Reactive components
  - Map visualizations
  - Real-time updates

- **theme.py**: UI theme configuration

### 7. Worker Layer (`src/vrp_platform/workers/`)

Background job processing:

- **queue.py**: Queue management
- **tasks.py**: Task definitions

### 8. Infrastructure Layer

- **bootstrap.py**: Application bootstrap
- **config.py**: Configuration management
- **db.py**: Database initialization
- **logging.py**: Logging configuration

## Data Flow

### 1. Manifest Intake

```
CSV File → IngestionService → Validation → Orders in DB
```

### 2. Route Planning

```
Orders → PlanningService → RouteOptimizer → Routes → DB
```

### 3. Warehouse Operations

```
Routes → Load Sheet Generation → PDF → Warehouse Staff
```

### 4. Driver Execution

```
Routes → Driver App → Status Updates → Events → DB
```

### 5. Customer Tracking

```
Order ID → Customer Portal → Status Display
```

### 6. Audit Trail

```
All Actions → Event Store → Admin Dashboard
```

## Optimization Algorithm

### Phase 1: Multi-Depot Assignment

1. For each order, identify capable depots (vehicles that can serve it)
2. Assign order to nearest capable depot
3. Create depot-specific sub-problems

### Phase 2: Initial Solution (Regret Insertion)

1. Pre-check feasibility (capacity, dimensions, distance)
2. For each unassigned order:
   - Evaluate insertion cost in all routes at all positions
   - Calculate regret (difference between best and second-best)
   - Insert order with highest regret into best position
3. Continue until all orders assigned or no feasible insertions

### Phase 3: Local Search

Iteratively apply operators until no improvement:

1. **2-opt**: Reverse route segments to eliminate crossings
2. **Relocate**: Move orders between routes
3. **Swap**: Exchange orders between routes
4. **Cross-exchange**: Swap route tails between routes

### Phase 4: Repair

For unassigned orders after initial construction:
- Attempt forced insertion with constraint relaxation
- Try alternative vehicle assignments
- Report violations for truly infeasible orders

## Constraint Handling

### Hard Constraints (Must Satisfy)

- Vehicle capacity (weight and volume)
- Vehicle dimensions (length, width, height)
- Time windows (if enforced)
- Shift time limits (if enforced)
- Break requirements

### Soft Constraints (Penalized)

- Lateness (if time windows not enforced)
- Overtime (if shift limits not enforced)
- Load imbalance
- Priority violations

## Objective Function

Configurable weighted sum:

```
score = w1 * distance_km 
      + w2 * drive_min 
      + w3 * lateness_min 
      + w4 * emissions_kg 
      + w5 * energy_cost 
      + w6 * (1 - load_ratio)
      + w7 * overtime_min
      - w8 * priority_score
```

## Database Schema

### Core Tables

- `depots`: Depot locations and operating hours
- `vehicles`: Vehicle fleet with capacities and constraints
- `drivers`: Driver information and assignments
- `orders`: Delivery orders with locations and demands
- `routes`: Planned routes with metrics
- `route_stops`: Individual stops within routes
- `events`: Audit trail of all operations

### Relationships

- Vehicle → Depot (many-to-one)
- Route → Vehicle (many-to-one)
- Route → Driver (many-to-one)
- RouteStop → Order (many-to-one)
- RouteStop → Route (many-to-one)

## Configuration

### Environment Variables

- `VRP_DATABASE_URL`: Database connection string
- `VRP_REDIS_URL`: Redis connection for queue
- `VRP_TIMEZONE`: Operational timezone
- `VRP_USE_ROAD_GEOMETRY`: Enable road-based routing

### Constraint Configuration

```python
ConstraintSet(
    departure_minute=480,           # 8:00 AM
    enforce_time_windows=True,
    enforce_shift_time=True,
    consider_live_traffic=False,
    avoid_incidents=True,
)
```

### Objective Configuration

```python
ObjectiveWeights(
    distance_km=1.0,
    drive_min=0.5,
    lateness_min=10.0,
    emissions_kg=0.1,
    energy_cost=1.0,
    load_imbalance=0.5,
    overtime_min=5.0,
    priority_score=2.0,
)
```

## Deployment

### Development

```bash
# Install dependencies
python -m pip install -e .[dev]

# Run platform
python -m vrp_platform.ui.app

# Uses SQLite database in var/
```

### Production

```bash
# Set environment variables
export VRP_DATABASE_URL="postgresql://user:pass@host/db"
export VRP_REDIS_URL="redis://host:6379/0"

# Run migrations
alembic upgrade head

# Start web server
python -m vrp_platform.ui.app

# Start workers (separate process)
rq worker --url $VRP_REDIS_URL
```

## Testing

### Unit Tests

```bash
# Run all tests
python -m pytest tests/platform -v

# Run specific test
python -m pytest tests/platform/test_optimizer_platform.py -v
```

### Property-Based Tests

```bash
# Run with more iterations
python -m pytest tests/platform -v --hypothesis-profile=thorough
```

### Integration Tests

Tests cover:
- End-to-end optimization workflows
- Multi-depot assignment
- Constraint validation
- Objective function scoring
- Database persistence
- Event logging

## Performance

### Typical Performance

- **Small problems (5-20 orders)**: <1 second
- **Medium problems (20-50 orders)**: 1-5 seconds
- **Large problems (50-100 orders)**: 5-30 seconds
- **Very large problems (100-200 orders)**: 30-120 seconds

### Optimization Opportunities

If performance becomes critical:

1. **NumPy vectorization**: 5-10x speedup for distance calculations
2. **Numba JIT**: 10-20x speedup for hot loops
3. **Cython**: 20-50x speedup with compilation
4. **Parallel evaluation**: Multi-core insertion evaluation
5. **Heuristic tuning**: Reduce local search iterations

## Future Enhancements

### Near-term

- Real-time telematics integration
- External traffic feed integration
- Queue-backed long-running jobs
- Auth hardening and SSO

### Medium-term

- Advanced metaheuristics (genetic algorithms, simulated annealing)
- Machine learning for demand prediction
- Dynamic re-optimization during execution
- Mobile driver app (native)

### Long-term

- Multi-objective optimization (Pareto frontier)
- Stochastic optimization (uncertainty handling)
- Collaborative routing (multiple companies)
- Autonomous vehicle integration

## References

### Academic Papers

- Clarke & Wright (1964): Savings algorithm
- Solomon (1987): Time window benchmarks
- Toth & Vigo (2014): Vehicle Routing book

### Industry Standards

- CVRP: Capacitated Vehicle Routing Problem
- VRPTW: VRP with Time Windows
- MDVRP: Multi-Depot VRP
- HFVRP: Heterogeneous Fleet VRP

## License

See LICENSE file for details.
