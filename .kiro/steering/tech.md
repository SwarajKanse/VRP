# Technology Stack

## Core Technologies

- **Language**: Python 3.11+ (pure Python implementation)
- **Web Framework**: NiceGUI for multi-workspace UI
- **Database**: SQLAlchemy with SQLite (dev) / PostgreSQL (prod)
- **Queue System**: Redis + RQ for background jobs
- **Testing Framework**: pytest with hypothesis for property-based testing

## Python Dependencies

### Runtime Dependencies

- **nicegui**: Modern web UI framework with reactive components
- **sqlalchemy**: ORM and database abstraction
- **alembic**: Database migrations
- **pydantic**: Data validation and settings management
- **pydantic-settings**: Environment-based configuration
- **pandas**: Data manipulation and CSV processing
- **redis**: Queue backend for async tasks
- **rq**: Background job processing
- **reportlab**: PDF generation for load sheets
- **requests**: HTTP client for external integrations

### Development Dependencies

- **pytest**: Testing framework
- **hypothesis**: Property-based testing
- **ruff**: Fast Python linter and formatter

## Common Commands

### Installing Dependencies

```bash
# Install all dependencies (including dev)
python -m pip install -e .[dev]

# Or use setup script
setup.bat       # Windows
./setup.sh      # Linux/macOS
```

### Running the Platform

```bash
# Start the platform
python -m vrp_platform.ui.app

# Or use quick launcher
run_dashboard.bat   # Windows
./run_dashboard.sh  # Linux/macOS

# Opens at http://localhost:8080
```

### Running Tests

```bash
# Run all platform tests
python -m pytest tests/platform -v

# Run with quiet output
python -m pytest tests/platform -q

# Run property-based tests with more iterations
python -m pytest tests/platform -v --hypothesis-profile=thorough

# Run specific test file
python -m pytest tests/platform/test_optimizer_platform.py -v
```

### Verification

```bash
# Verify installation and run demo
python test_installation.py
```

## Environment Configuration

Key environment variables:

- `VRP_DATABASE_URL`: Database connection string (default: SQLite in `var/`)
- `VRP_REDIS_URL`: Redis connection for queue backend
- `VRP_TIMEZONE`: Operational timezone for timestamps
- `VRP_USE_ROAD_GEOMETRY`: Enable road-shaped route polylines for maps

## Platform Notes

### All Platforms

- Pure Python implementation works on any platform with Python 3.11+
- No compilation required
- No platform-specific dependencies
- No C++ runtime requirements

### Windows

- No Visual C++ Redistributable needed
- No MinGW or compiler required
- Works with standard Python installation

### Linux/macOS

- Works with standard Python 3.11+ installation
- No additional system packages required

## Architecture Layers

### Domain Layer (`src/vrp_platform/domain/`)
- Typed entities (Order, Vehicle, Depot, Route, etc.)
- Enums for status codes and types
- Pure business logic, no infrastructure dependencies

### Service Layer (`src/vrp_platform/services/`)
- Planning service (optimization orchestration)
- Ingestion service (manifest processing)
- Operations service (route execution)
- Auth service (user management)
- Event service (audit logging)

### Repository Layer (`src/vrp_platform/repos/`)
- SQLAlchemy models and database access
- Catalog repo (vehicles, depots, drivers)
- Orders repo (order management)
- Planning repo (routes and assignments)
- Events repo (audit trail)

### Optimizer Layer (`src/vrp_platform/optimizer/`)
- Route construction engine
- Local search operators
- Objective scoring
- Fallback strategies

### Integration Layer (`src/vrp_platform/integrations/`)
- Travel matrix providers (Euclidean, road network)
- External API integrations

### UI Layer (`src/vrp_platform/ui/`)
- NiceGUI application
- Multi-workspace routing
- Reactive components

### Worker Layer (`src/vrp_platform/workers/`)
- Background task queue
- Long-running job processing

