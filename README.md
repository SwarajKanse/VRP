# VRP Solver - Vehicle Routing Problem Solver

A professional-grade Vehicle Routing Problem (VRP) solver implemented in pure Python. The solver addresses Capacitated VRP (CVRP) and VRP with Time Windows (VRPTW) using a Nearest Neighbor heuristic.

## 🚀 Quick Start

**New users: See [QUICKSTART.md](QUICKSTART.md) for step-by-step setup instructions!**

### Fast Setup

**Windows:**
```bash
setup.bat
```

**Linux/macOS:**
```bash
chmod +x setup.sh
./setup.sh
```

### Run Dashboard
```bash
# Windows
run_dashboard.bat

# Linux/macOS
chmod +x run_dashboard.sh
./run_dashboard.sh
```

## Features

- **Pure Python Implementation**: No compilation required, works on any platform
- **Heterogeneous Fleet Support**: Define mixed vehicle fleets with different capacity constraints
- **Capacity Constraints**: Routes respect individual vehicle capacity limits
- **Time Window Constraints**: Customers must be visited within their service windows
- **Geographic Distance Calculation**: Uses Haversine formula for accurate distance computation
- **Easy Integration**: Simple Python API with no build dependencies
- **CSV Manifest Ingestion**: Upload detailed order data with package dimensions and handling constraints
- **Vehicle-Specific Fuel Economics**: Track precise fuel costs per vehicle type with custom efficiency ratings
- **Physics-Compliant LIFO Packing**: Intelligent Last-In-First-Out packing with fragile and orientation constraints
- **Driver Manifest Generation**: Generate professional CSV and PDF delivery instructions

## 📦 What's Included

This package contains everything you need to run the VRP solver:

- **Pure Python Solver**: Professional-grade routing algorithm
- **Streamlit Dashboard**: Interactive web interface
- **Test Suite**: Comprehensive tests with pytest and hypothesis
- **Sample Data**: Example CSV manifest file
- **Setup Scripts**: Automated installation for Windows/Linux/macOS

## Installation

### Prerequisites

- **Python 3.8+** - [Download here](https://www.python.org/downloads/)

That's it! No compilers, no build tools, just Python.

### Automated Setup (Recommended)

**Windows:**
```bash
setup.bat
```

**Linux/macOS:**
```bash
chmod +x setup.sh
./setup.sh
```

The setup script will:
1. Install Python dependencies
2. Verify the installation

### Manual Setup

If you prefer manual installation:

```bash
# Install Python dependencies
pip install -r requirements.txt

# Verify installation
python test_installation.py
```

## Usage

### Basic Example

```python
import vrp_core

# Create depot (customer 0)
depot = vrp_core.Customer(
    id=0,
    location=vrp_core.Location(19.065, 72.835),
    demand=0.0,
    start_window=0.0,
    end_window=600.0,
    service_time=0.0
)

# Create customers
customer1 = vrp_core.Customer(
    id=1,
    location=vrp_core.Location(19.070, 72.840),
    demand=10.0,
    start_window=0.0,
    end_window=600.0,
    service_time=10.0
)

customer2 = vrp_core.Customer(
    id=2,
    location=vrp_core.Location(19.075, 72.845),
    demand=15.0,
    start_window=0.0,
    end_window=600.0,
    service_time=10.0
)

# Create solver
solver = vrp_core.VRPSolver()

# Define vehicle capacities (homogeneous fleet)
vehicle_capacities = [50.0, 50.0, 50.0]  # 3 vehicles with capacity 50 each

# Solve
customers = [depot, customer1, customer2]
routes = solver.solve(customers, vehicle_capacities)

# Print routes
for i, route in enumerate(routes):
    print(f"Route {i}: {route}")
```

### Heterogeneous Fleet Example

The solver supports heterogeneous fleets where vehicles have different capacities:

```python
import vrp_core

# Create customers
depot = vrp_core.Customer(0, vrp_core.Location(19.065, 72.835), 0.0, 0.0, 600.0, 0.0)
customer1 = vrp_core.Customer(1, vrp_core.Location(19.070, 72.840), 40.0, 0.0, 600.0, 10.0)
customer2 = vrp_core.Customer(2, vrp_core.Location(19.075, 72.845), 15.0, 0.0, 600.0, 10.0)
customer3 = vrp_core.Customer(3, vrp_core.Location(19.080, 72.850), 10.0, 0.0, 600.0, 10.0)

customers = [depot, customer1, customer2, customer3]

# Define heterogeneous fleet
# 2 Trucks (capacity 50 each), 2 Vans (capacity 20 each), 1 Bike (capacity 10)
# IMPORTANT: Sort capacities in descending order for optimal utilization
vehicle_capacities = [50.0, 50.0, 20.0, 20.0, 10.0]

# Solve
solver = vrp_core.VRPSolver()
routes = solver.solve(customers, vehicle_capacities)

# Each route respects its vehicle's capacity
for i, route in enumerate(routes):
    print(f"Route {i} (Vehicle capacity: {vehicle_capacities[i]}): {route}")
```

## API Reference

### `vrp_core.Location`

Represents a geographic location.

**Constructor:**
```python
Location(latitude: float, longitude: float)
```

**Attributes:**
- `latitude`: Latitude coordinate (-90 to 90)
- `longitude`: Longitude coordinate (-180 to 180)

### `vrp_core.Customer`

Represents a customer delivery point.

**Constructor:**
```python
Customer(
    id: int,
    location: Location,
    demand: float,
    start_window: float,
    end_window: float,
    service_time: float = 0.0
)
```

**Attributes:**
- `id`: Unique customer identifier (0 for depot)
- `location`: Geographic location
- `demand`: Delivery demand quantity
- `start_window`: Earliest service time (minutes from start)
- `end_window`: Latest service time (minutes from start)
- `service_time`: Time required to serve customer (minutes)

### `vrp_core.VRPSolver`

Main solver class for vehicle routing problems.

**Constructor:**
```python
VRPSolver()
```

**Methods:**

#### `solve(customers, vehicle_capacities, use_simd=True, time_matrix=None)`

Solve the VRP with heterogeneous fleet.

**Parameters:**
- `customers`: List of Customer objects (first must be depot with id=0)
- `vehicle_capacities`: List of float capacities for each vehicle (sorted descending recommended)
- `use_simd`: Ignored (kept for API compatibility)
- `time_matrix`: Optional pre-computed time matrix (default: computed using distance * 1.5)

**Returns:**
- List of routes, where each route is a list of customer IDs

**Example:**
```python
solver = vrp_core.VRPSolver()
routes = solver.solve(
    customers=[depot, customer1, customer2],
    vehicle_capacities=[50.0, 30.0, 20.0]
)
```

### `vrp_core.haversine_distance()`

Calculate great-circle distance between two points.

**Parameters:**
- `lat1`, `lon1`: First point coordinates in degrees
- `lat2`, `lon2`: Second point coordinates in degrees

**Returns:**
- Distance in kilometers

**Example:**
```python
# Mumbai to Delhi
distance = vrp_core.haversine_distance(19.0760, 72.8777, 28.7041, 77.1025)
print(f"Distance: {distance:.2f} km")  # ~1153 km
```

## Testing

### Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_solver.py -v

# Run with hypothesis property-based tests
python -m pytest tests/ -v --hypothesis-profile=thorough
```

### Test Coverage

The project includes comprehensive test coverage:

- **Unit Tests**: Test individual components and functions
- **Integration Tests**: Test complete workflow from dashboard to solver
- **Property-Based Tests**: Test universal properties using Hypothesis
- **Edge Case Tests**: Test boundary conditions and error handling

## Architecture

### Components

1. **Pure Python Solver** (`vrp_core.py`)
   - VRPSolver implementation
   - Nearest Neighbor heuristic
   - Distance matrix computation
   - Constraint validation
   - Haversine distance utility

2. **Dashboard** (`dashboard/app.py`)
   - Streamlit web interface
   - Fleet configuration UI
   - Route visualization
   - Financial analytics

3. **Supporting Modules** (`dashboard/`)
   - CSV parser for manifest ingestion
   - Financial engine for cost calculations
   - Fleet composer for vehicle management
   - Packing engines for cargo loading
   - Manifest builder for driver instructions

### Data Flow

```
User Input (Dashboard)
    ↓
Fleet Configuration (vehicle profiles)
    ↓
Flatten & Sort (descending by capacity)
    ↓
Python Solver (VRPSolver.solve)
    ↓
Routes (with vehicle assignments)
    ↓
Visualization (Dashboard)
```

## 🔧 Troubleshooting

### Common Issues

**"ModuleNotFoundError: No module named 'vrp_core'"**
- Ensure `vrp_core.py` is in the project root
- Check your Python path includes the project directory

**"ModuleNotFoundError: No module named 'pytest'"**
- Install dependencies: `pip install -r requirements.txt`

**Dashboard won't start**
- Verify you're in the `dashboard` directory
- Install dependencies: `pip install -r requirements.txt`
- Check Streamlit is installed: `pip install streamlit`

For more help, see [QUICKSTART.md](QUICKSTART.md)

## 📁 Project Structure

```
vrp-solver/
├── vrp_core.py             # Pure Python VRP solver
├── dashboard/              # Streamlit web dashboard
│   ├── app.py              # Main dashboard application
│   ├── csv_parser.py       # CSV manifest parser
│   ├── financial_engine.py # Cost calculations
│   ├── fleet_composer.py   # Fleet configuration
│   ├── packing_engine*.py  # 3D packing algorithms
│   └── manifest_builder.py # Driver manifest generation
├── tests/                  # Python test suite
├── requirements.txt        # Python dependencies
├── setup.py                # Setup script
├── setup.bat               # Windows setup
├── setup.sh                # Linux/macOS setup
├── test_installation.py    # Installation verification
├── run_dashboard.bat       # Windows dashboard launcher
├── run_dashboard.sh        # Linux/macOS dashboard launcher
├── QUICKSTART.md           # Quick start guide
└── README.md               # This file
```

## Performance Considerations

- **Pure Python**: Slower than compiled C++ but sufficient for typical routing problems (5-50 customers)
- **Solver Complexity**: O(V × C²) where V is vehicles and C is customers
- **Memory**: Linear in number of vehicles and customers
- **Typical Performance**: <1 second for 20 customers, <5 seconds for 50 customers

### Future Optimization Options

The pure Python implementation can be optimized if needed:

- **NumPy**: Vectorized distance calculations (5-10x speedup)
- **Numba**: JIT compilation of hot loops (10-20x speedup)
- **Cython**: Compile critical paths to C (20-50x speedup)

All optimizations can be done without changing the public API.

## Contributing

Contributions are welcome! Please ensure:

1. All tests pass: `python -m pytest tests/ -v`
2. Code follows Python best practices (PEP 8)
3. New features include comprehensive tests
4. Documentation is updated

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contact

For questions, issues, or contributions, please open an issue on the project repository.
