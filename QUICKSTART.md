# Quick Start

## Prerequisites

- Python 3.11 or higher
- pip (Python package manager)

No compilation, no C++ dependencies, no build tools needed!

## 1. Install

### Windows

```bash
setup.bat
```

### Linux/macOS

```bash
chmod +x setup.sh
./setup.sh
```

### Manual Install

```bash
python -m pip install -e .[dev]
```

## 2. Verify

```bash
python test_installation.py
```

This will:
- Check all Python dependencies
- Bootstrap the platform
- Run a demo optimization
- Verify database connectivity

## 3. Run

### Quick Launch

**Windows:**
```bash
run_dashboard.bat
```

**Linux/macOS:**
```bash
./run_dashboard.sh
```

### Manual Launch

```bash
python -m vrp_platform.ui.app
```

The platform will open at [http://localhost:8080](http://localhost:8080)

## 4. Run Tests

```bash
# Run all platform tests
python -m pytest tests/platform -q

# Verbose output
python -m pytest tests/platform -v

# Property-based tests with more iterations
python -m pytest tests/platform -v --hypothesis-profile=thorough
```

## What You Get

### Multi-Workspace Application

- **Dispatcher**: Manifest intake, route planning, scenario comparison
- **Warehouse**: Load sheets, dock assignments, shipment tracking
- **Driver**: Route execution, turn-by-turn navigation, incident reporting
- **Customer**: Shipment lookup and tracking
- **Admin**: Audit logs, system monitoring, configuration

### Routing Engine

- Multi-depot vehicle routing
- Capacity and time window constraints
- Break scheduling and shift enforcement
- Traffic incident awareness
- Heterogeneous fleet support
- Configurable objective functions

### Data Persistence

- SQLite for local development (default)
- PostgreSQL-ready for production
- Event sourcing for audit trails
- SQLAlchemy ORM

## Configuration

Set environment variables to customize:

```bash
# Database (default: SQLite in var/)
export VRP_DATABASE_URL="sqlite:///var/vrp_platform.db"

# Redis for background jobs (optional)
export VRP_REDIS_URL="redis://localhost:6379/0"

# Timezone for operations
export VRP_TIMEZONE="America/New_York"

# Enable road geometry for maps
export VRP_USE_ROAD_GEOMETRY="true"
```

## Next Steps

1. **Upload a manifest**: Use the dispatcher page to upload `sample_manifest.csv`
2. **Run optimization**: Select orders and run route planning
3. **Review routes**: Check the route board and warehouse load sheets
4. **Assign drivers**: Assign routes to drivers and view driver workflow
5. **Track shipments**: Use customer portal to track deliveries
6. **Monitor operations**: Check admin dashboard for audit logs

## Troubleshooting

### Import Errors

If you see import errors, ensure dependencies are installed:

```bash
python -m pip install -e .[dev]
```

### Database Errors

If database initialization fails, delete and recreate:

```bash
rm -rf var/vrp_platform.db
python test_installation.py
```

### Port Already in Use

If port 8080 is in use, the platform will try alternative ports automatically.

## Project Structure

```
src/vrp_platform/
  domain/           # Domain entities and enums
  optimizer/        # Route construction and local search
  repos/            # SQLAlchemy models and data access
  services/         # Business logic services
  integrations/     # External integrations
  ui/               # NiceGUI web application
  workers/          # Background job queue

tests/platform/     # Integration tests
var/                # Runtime data (SQLite database)
```

## Learn More

- **README.md**: Complete platform documentation
- **GETTING_STARTED.txt**: Detailed getting started guide
- **.kiro/steering/**: AI assistant guidance documents
