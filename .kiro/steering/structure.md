# Project Structure

## Directory Layout

```
vrp-solver/
├── .kiro/
│   ├── specs/                    # Feature specifications
│   └── steering/                 # AI assistant guidance documents
├── dashboard/
│   ├── app.py                    # Main Streamlit dashboard
│   ├── csv_parser.py             # CSV manifest parser
│   ├── financial_engine.py       # Cost calculations
│   ├── fleet_composer.py         # Fleet management
│   ├── packing_engine.py         # Bin packing algorithms
│   └── ...                       # Other dashboard modules
├── tests/
│   ├── test_solver.py            # VRP solver tests
│   ├── test_packing_algorithm.py # Packing tests
│   └── ...                       # Other test files
├── vrp_core.py                   # Pure Python VRP solver module
├── test_installation.py          # Installation verification
├── setup.py                      # Setup script
├── setup.bat / setup.sh          # Platform-specific setup scripts
├── requirements.txt              # Python dependencies
└── *.md                          # Documentation files
```

## Key Files

### Core Implementation

- **vrp_core.py**: Pure Python VRP solver module containing:
  - `Location`: Geographic coordinate dataclass
  - `Customer`: Delivery point dataclass with demand and time windows
  - `VRPSolver`: Main solver class with nearest neighbor heuristic
  - `haversine_distance()`: Geographic distance utility function

### Dashboard

- **dashboard/app.py**: Main Streamlit application entry point
- **dashboard/csv_parser.py**: Parses delivery manifest CSV files
- **dashboard/financial_engine.py**: Calculates routing costs and metrics
- **dashboard/fleet_composer.py**: Manages vehicle fleet configuration
- **dashboard/packing_engine.py**: Bin packing algorithms for cargo loading

### Testing

- **tests/test_solver.py**: Primary test suite with pytest and hypothesis
- **tests/test_*.py**: Additional test modules for various components
- **test_installation.py**: Quick verification script

### Configuration

- **requirements.txt**: Python package dependencies
- **setup.py**: Installation script
- **.gitignore**: Git ignore patterns

## Architecture Layers

### Layer 1: Data Structures (vrp_core.py)

- `Location`: Geographic coordinates (latitude, longitude)
- `Customer`: Delivery point with demand, time windows, and service time
- `Route`: Type alias for `list[int]` (customer IDs)

### Layer 2: Core Solver (vrp_core.py)

- `VRPSolver.solve()`: Main entry point
- `VRPSolver._build_distance_matrix()`: Precompute Euclidean distances
- `VRPSolver._nearest_neighbor_heuristic()`: Route construction algorithm
- `VRPSolver._can_add_to_route()`: Constraint validation
- `haversine_distance()`: Geographic distance calculation

### Layer 3: Dashboard Integration (dashboard/)

- Imports `vrp_core` module directly
- Converts CSV data to Customer objects
- Calls solver and visualizes results
- Generates reports and metrics

## Code Organization Principles

1. **Pure Python**: No compilation required, works on any platform
2. **Separation of Concerns**: Data structures separate from algorithms
3. **Single Module**: Core solver in one file for simplicity
4. **Standard Library**: Minimal external dependencies
5. **Test Isolation**: Comprehensive test coverage with pytest

## Module Import Structure

```python
# From dashboard or tests
import vrp_core

# Create objects
location = vrp_core.Location(lat, lon)
customer = vrp_core.Customer(id, location, demand, start, end, service)
solver = vrp_core.VRPSolver()

# Solve problem
routes = solver.solve(customers, capacities)

# Calculate distances
dist = vrp_core.haversine_distance(lat1, lon1, lat2, lon2)
```

