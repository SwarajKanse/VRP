# VRP Solver - Vehicle Routing Problem Solver

A high-performance Vehicle Routing Problem (VRP) solver built in C++20 with Python bindings. The solver addresses Capacitated VRP (CVRP) and VRP with Time Windows (VRPTW) using a Nearest Neighbor heuristic.

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

- **Heterogeneous Fleet Support**: Define mixed vehicle fleets with different capacity constraints
- **Capacity Constraints**: Routes respect individual vehicle capacity limits
- **Time Window Constraints**: Customers must be visited within their service windows
- **Geographic Distance Calculation**: Uses Haversine formula for accurate distance computation
- **Python Integration**: Easy-to-use Python API via Nanobind bindings
- **High Performance**: C++20 implementation optimized for speed
- **CSV Manifest Ingestion**: Upload detailed order data with package dimensions and handling constraints
- **Vehicle-Specific Fuel Economics**: Track precise fuel costs per vehicle type with custom efficiency ratings
- **Physics-Compliant LIFO Packing**: Intelligent Last-In-First-Out packing with fragile and orientation constraints
- **Driver Manifest Generation**: Generate professional CSV and PDF delivery instructions

## 📦 What's Included

This package contains everything you need to run the VRP solver:

- **C++ Core Engine**: High-performance routing solver
- **Python Bindings**: Easy-to-use Python API
- **Streamlit Dashboard**: Interactive web interface
- **Test Suite**: Comprehensive tests with pytest and hypothesis
- **Sample Data**: Example CSV manifest file
- **Setup Scripts**: Automated installation for Windows/Linux/macOS

## Installation

### Prerequisites

- **Python 3.8+** - [Download here](https://www.python.org/downloads/)
- **CMake 3.15+** - [Download here](https://cmake.org/download/)
- **C++20 Compiler**:
  - Windows: Visual Studio 2019+ or MinGW-w64
  - Linux: GCC 10+ (`sudo apt install build-essential`)
  - macOS: Xcode Command Line Tools (`xcode-select --install`)

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
1. Check prerequisites
2. Install Python dependencies
3. Build the C++ extension
4. Verify the installation

### Manual Setup

If you prefer manual installation:

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Build C++ extension
mkdir build
cd build
cmake ..
cmake --build . --config Release
cd ..

# 3. Verify installation
python -m pytest tests/ -v
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

### Fleet Configuration Best Practices

1. **Sort by Capacity**: Always sort vehicle capacities in descending order (largest first) to maximize fleet utilization
2. **Capacity Constraints**: Each route will respect its assigned vehicle's capacity
3. **Maximum Routes**: The solver will generate at most N routes for N vehicles
4. **Unassigned Customers**: If fleet capacity is insufficient, some customers may remain unassigned

### Dashboard Integration

The project includes a Streamlit dashboard for interactive fleet management:

```python
# In dashboard/app.py

# Define vehicle profiles
vehicle_profiles = [
    {"name": "Truck", "capacity": 50.0, "quantity": 2},
    {"name": "Van", "capacity": 20.0, "quantity": 2},
    {"name": "Bike", "capacity": 10.0, "quantity": 1}
]

# Flatten and sort fleet (descending by capacity)
from dashboard.app import flatten_and_sort_fleet

vehicle_capacities, vehicle_map = flatten_and_sort_fleet(vehicle_profiles)
# vehicle_capacities = [50.0, 50.0, 20.0, 20.0, 10.0]
# vehicle_map contains vehicle names and instance numbers for display

# Solve with heterogeneous fleet
routes = solver.solve(customers, vehicle_capacities)

# Map routes to vehicles for display
for route_idx, route in enumerate(routes):
    vehicle = vehicle_map[route_idx]
    print(f"Route {route_idx}: {vehicle['name']} #{vehicle['instance']} (Cap: {vehicle['capacity']})")
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

#### `solve(customers, vehicle_capacities, use_simd=True, time_matrix=[])`

Solve the VRP with heterogeneous fleet.

**Parameters:**
- `customers`: List of Customer objects (first must be depot with id=0)
- `vehicle_capacities`: List of float capacities for each vehicle (sorted descending recommended)
- `use_simd`: Enable SIMD optimizations (default: True)
- `time_matrix`: Optional pre-computed time matrix (default: computed using Haversine)

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

## Testing

### Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_solver.py -v

# Run heterogeneous fleet tests
python -m pytest tests/test_solver.py::TestHeterogeneousFleet -v

# Run integration tests
python -m pytest tests/test_heterogeneous_fleet_integration.py -v
```

### Test Coverage

The project includes comprehensive test coverage:

- **Unit Tests**: Test individual components and functions
- **Integration Tests**: Test complete workflow from dashboard to solver
- **Property-Based Tests**: Test universal properties using Hypothesis
- **Edge Case Tests**: Test boundary conditions and error handling

## Architecture

### Components

1. **C++ Core** (`src/solver.cpp`, `include/solver.h`)
   - VRPSolver implementation
   - Nearest Neighbor heuristic
   - Distance matrix computation
   - Constraint validation

2. **Python Bindings** (`src/bindings.cpp`)
   - Nanobind module exposing C++ classes to Python
   - Type conversions between Python and C++

3. **Dashboard** (`dashboard/app.py`)
   - Streamlit web interface
   - Fleet configuration UI
   - Route visualization
   - Financial analytics

### Data Flow

```
User Input (Dashboard)
    ↓
Fleet Configuration (vehicle profiles)
    ↓
Flatten & Sort (descending by capacity)
    ↓
Python Bindings (Nanobind)
    ↓
C++ Solver (VRPSolver::solve)
    ↓
Routes (with vehicle assignments)
    ↓
Visualization (Dashboard)
```

## Heterogeneous Fleet Feature

### Overview

The heterogeneous fleet feature allows you to define a mixed fleet with different vehicle types and capacities. This is essential for real-world logistics where fleets typically include various vehicle sizes.

### Key Concepts

1. **Vehicle Profile**: Specification of a vehicle type (name, capacity, quantity)
2. **Fleet Flattening**: Converting profiles into a flat list of capacities
3. **Capacity Sorting**: Ordering vehicles by capacity (descending) for optimal utilization
4. **Vehicle Mapping**: Tracking which route corresponds to which vehicle

### Implementation Details

#### Fleet Configuration

```python
# Define vehicle profiles
vehicle_profiles = [
    {"name": "Truck", "capacity": 50.0, "quantity": 2},
    {"name": "Van", "capacity": 20.0, "quantity": 2},
    {"name": "Bike", "capacity": 10.0, "quantity": 1}
]

# Flatten and sort
vehicle_capacities, vehicle_map = flatten_and_sort_fleet(vehicle_profiles)

# Result:
# vehicle_capacities = [50.0, 50.0, 20.0, 20.0, 10.0]
# vehicle_map = [
#     {"name": "Truck", "instance": 1, "capacity": 50.0},
#     {"name": "Truck", "instance": 2, "capacity": 50.0},
#     {"name": "Van", "instance": 1, "capacity": 20.0},
#     {"name": "Van", "instance": 2, "capacity": 20.0},
#     {"name": "Bike", "instance": 1, "capacity": 10.0}
# ]
```

#### Solver Integration

```python
# Solve with heterogeneous fleet
routes = solver.solve(customers, vehicle_capacities)

# Each route respects its vehicle's capacity
for route_idx, route in enumerate(routes):
    capacity = vehicle_capacities[route_idx]
    vehicle = vehicle_map[route_idx]
    
    # Calculate route demand
    route_demand = sum(customers[cid].demand for cid in route if cid != 0)
    
    print(f"Route {route_idx}: {vehicle['name']} #{vehicle['instance']}")
    print(f"  Capacity: {capacity}, Demand: {route_demand}")
    print(f"  Customers: {route}")
```

#### Unassigned Customer Detection

```python
from dashboard.app import detect_unassigned_customers

# Detect customers that couldn't be assigned
unassigned = detect_unassigned_customers(routes, customer_dataframe)

if unassigned:
    print(f"Warning: {len(unassigned)} customers unassigned")
    print(f"Unassigned customer IDs: {unassigned}")
    print("Suggestion: Add more vehicles or increase capacities")
```

### Constraints

1. **Capacity Constraint**: Each route's total demand ≤ vehicle capacity
2. **Maximum Routes**: Number of routes ≤ number of vehicles
3. **Time Window Constraint**: Customers visited within their time windows
4. **Depot Constraint**: All routes start and end at depot (customer 0)

## Realistic Data & Physics Upgrade

### Overview

The realistic data and physics upgrade transforms the VRP solver into a professional logistics tool with detailed package handling, vehicle-specific fuel economics, physics-compliant packing, and comprehensive driver manifests.

### CSV Manifest Ingestion

Upload detailed order data with package dimensions and handling constraints:

```csv
Order ID,Source Name,Destination Name,Latitude,Longitude,Length (cm),Width (cm),Height (cm),Weight (kg),Fragile,This Side Up
ORD001,Warehouse A,Customer 1,19.0760,72.8777,50,40,30,15.5,Yes,No
ORD002,Warehouse A,Customer 2,19.0896,72.8656,30,30,30,8.2,No,Yes
```

**Features:**
- Automatic validation of coordinates, dimensions, and weights
- Case-insensitive boolean parsing for constraints
- Dimension conversion from centimeters to meters
- Weight aggregation by destination for routing
- Descriptive error messages for invalid data

**Usage:**
```python
from dashboard.csv_parser import CSVParser, Package, Destination

parser = CSVParser()
destinations, error = parser.parse_manifest("sample_manifest.csv")

if error:
    print(f"Parsing error: {error}")
else:
    print(f"Parsed {len(destinations)} destinations")
    for dest in destinations:
        print(f"{dest.name}: {len(dest.packages)} packages, {dest.total_weight_kg} kg")
```

### Vehicle-Specific Fuel Economics

Track precise fuel costs per vehicle type with custom efficiency ratings:

```python
from dashboard.fleet_composer import FleetComposer, VehicleType
from dashboard.financial_engine import FinancialEngine

# Configure fleet with fuel efficiency
fleet = FleetComposer()
fleet.add_vehicle_type(
    name="Truck",
    capacity_kg=1000.0,
    length_m=4.0,
    width_m=2.0,
    height_m=2.5,
    fuel_efficiency_km_per_L=8.0,  # 8 km per liter
    count=2
)

# Calculate route costs
financial_engine = FinancialEngine(
    fuel_price_per_L=1.50,  # $1.50 per liter
    driver_hourly_wage=25.0  # $25 per hour
)

vehicle = fleet.get_vehicle_by_name("Truck")
route_cost = financial_engine.calculate_route_cost(
    route_distance_km=120.0,
    route_time_hours=3.5,
    vehicle=vehicle
)

print(f"Fuel consumed: {route_cost.fuel_consumed_L:.2f} L")
print(f"Fuel cost: ${route_cost.fuel_cost:.2f}")
print(f"Labor cost: ${route_cost.labor_cost:.2f}")
print(f"Total cost: ${route_cost.total_cost:.2f}")
```

**Cost Calculation Formulas:**
- Fuel consumed (L) = distance (km) / fuel efficiency (km/L)
- Fuel cost ($) = fuel consumed (L) × fuel price ($/L)
- Labor cost ($) = time (hours) × hourly wage ($/hour)
- Total cost ($) = fuel cost + labor cost

### Physics-Compliant Packing Engines

The system provides two packing algorithms optimized for different scenarios:

#### 1. LIFO Packing Engine (Simple First-Fit)

Fast packing with basic LIFO ordering and fragile handling:

```python
from dashboard.lifo_packing_engine import LIFOPackingEngine

# Create packing engine for vehicle
packer = LIFOPackingEngine(
    vehicle_length_m=4.0,  # X-axis: back (0) to door (4.0)
    vehicle_width_m=2.0,   # Y-axis
    vehicle_height_m=2.5   # Z-axis
)

# Pack route with stop order
packing_result = packer.pack_route(
    packages=packages,
    stop_order=[1, 2, 3, 4, 5]  # Delivery sequence
)

print(f"Placed: {len(packing_result.placed_packages)} packages")
print(f"Failed: {len(packing_result.failed_packages)} packages")
print(f"Utilization: {packing_result.utilization_percent:.1f}%")
```

**LIFO Engine Constraints:**
- **LIFO Ordering**: Last delivery loaded first (at back), first delivery loaded last (at door)
- **Fragile Constraint**: No packages stacked on top of fragile items
- **Orientation Lock**: Packages marked "This Side Up" cannot be rotated
- **Stability Requirement**: Packages must have 60% base area support
- **Coordinate System**: X=0 (back wall) to X=max (door)

#### 2. DBL Packing Engine (Gravity-Driven Deepest-Bottom-Left)

Advanced packing with strict physics constraints and optimal space utilization:

```python
from dashboard.packing_engine_dbl import DBLPackingEngine, Package

# Create DBL packing engine
engine = DBLPackingEngine(
    vehicle_length_m=4.0,  # X-axis: back (0) to door (4.0)
    vehicle_width_m=2.0,   # Y-axis
    vehicle_height_m=2.5   # Z-axis
)

# Create packages with stop numbers
packages = [
    Package(
        order_id="ORD001",
        length_m=0.5,
        width_m=0.4,
        height_m=0.3,
        weight_kg=15.0,
        stop_number=3  # Delivery stop
    ),
    Package(
        order_id="ORD002",
        length_m=0.6,
        width_m=0.5,
        height_m=0.4,
        weight_kg=20.0,
        stop_number=2
    ),
    # ... more packages
]

# Pack route (automatically sorts by LIFO + weight)
result = engine.pack_route(packages)

print(f"Placed: {len(result.placed_packages)} packages")
print(f"Failed: {len(result.failed_packages)} packages")
print(f"Utilization: {result.utilization_percent:.1f}%")
print(f"Total Weight: {result.total_weight_kg:.1f} kg")

# Inspect placed packages
for placed in result.placed_packages:
    print(f"Package {placed.package.order_id}:")
    print(f"  Position: ({placed.x:.2f}, {placed.y:.2f}, {placed.z:.2f})")
    print(f"  Stop: {placed.package.stop_number}")
    print(f"  Weight: {placed.package.weight_kg} kg")

# Inspect failed packages
for package, reason in result.failed_packages:
    print(f"Failed: {package.order_id} - {reason}")
```

**DBL Engine Features:**

1. **Deepest-Bottom-Left Heuristic**: Places packages as close as possible to the back-bottom-left corner (0,0,0) using Euclidean distance minimization
2. **Contact Point Strategy**: Generates candidate positions from existing package corners instead of grid scanning
3. **Strict Gravity Enforcement**: Packages must have ≥80% of base area supported by packages below (no floating boxes)
4. **Weight Constraints**: Heavy packages cannot be placed on lighter packages (max 1.5x weight ratio)
5. **LIFO Preservation**: Maintains reverse stop order with weight-based secondary sort

**DBL Engine Constraints:**

- **80% Support Rule**: Packages at height z > 0 must have at least 80% of their bottom surface supported
- **Floor Exemption**: Packages at z = 0 (floor level) don't require support validation
- **Bridge Support**: Packages can span multiple supporting packages as long as total support ≥ 80%
- **Weight Ratio**: Package weight ≤ 1.5 × supporting package weight
- **LIFO Ordering**: Primary sort by reverse stop order (stop 5 → 4 → 3 → 2 → 1)
- **Weight Secondary Sort**: Within each stop, heavier packages loaded first
- **Boundary Validation**: All packages must fit within vehicle dimensions
- **Overlap Prevention**: No 3D intersection between packages

**DBL Algorithm Workflow:**

```
1. Sort packages by LIFO priority (reverse stop, then weight descending)
2. Initialize contact points with origin (0,0,0)
3. For each package:
   a. Sort contact points by Euclidean distance to origin
   b. Try each contact point in order:
      - Check boundaries (fits in vehicle?)
      - Check overlap (intersects existing package?)
      - Check support (≥80% base area supported?)
      - Check weight (≤1.5x supporting package weight?)
   c. Place at first valid position
   d. Generate new contact points from placed package:
      - Right edge: (x + length, y, z)
      - Front edge: (x, y + width, z)
      - Top corner: (x, y, z + height)
   e. Filter contact points (boundaries, occupancy)
4. Return placed and failed packages with diagnostics
```

**Choosing Between Engines:**

Use **LIFO Engine** when:
- Speed is critical (simple first-fit is faster)
- Packages have similar weights
- Basic fragile handling is sufficient
- You need quick approximate solutions

Use **DBL Engine** when:
- Maximum space utilization is important
- Packages have varying weights (heavy/light mix)
- Load stability is critical for transport safety
- You need detailed failure diagnostics
- Physics compliance is required

**Engine Comparison Example:**

```python
from dashboard.packing_engine_dbl import DBLPackingEngine
from dashboard.lifo_packing_engine import LIFOPackingEngine

# Same packages for both engines
packages = [...]  # Your package list

# Test LIFO engine
lifo_engine = LIFOPackingEngine(4.0, 2.0, 2.5)
lifo_result = lifo_engine.pack_route(packages, stop_order=[1,2,3,4,5])

# Test DBL engine
dbl_engine = DBLPackingEngine(4.0, 2.0, 2.5)
dbl_result = dbl_engine.pack_route(packages)

# Compare results
print("LIFO Engine:")
print(f"  Placed: {len(lifo_result.placed_packages)}")
print(f"  Utilization: {lifo_result.utilization_percent:.1f}%")

print("\nDBL Engine:")
print(f"  Placed: {len(dbl_result.placed_packages)}")
print(f"  Utilization: {dbl_result.utilization_percent:.1f}%")
print(f"  Failed: {len(dbl_result.failed_packages)}")

# DBL typically achieves higher utilization due to optimal placement
```

**Performance Characteristics:**

- **LIFO Engine**: O(N) time complexity, fast for typical routes
- **DBL Engine**: O(N²) time complexity, completes in <1 second for 20-50 packages
- **Contact Points**: DBL maintains O(N) contact points where N = placed packages
- **Memory**: Both engines use linear memory in number of packages

### Driver Manifest Generation

Generate professional CSV and PDF delivery instructions:

```python
from dashboard.manifest_builder import ManifestBuilder

builder = ManifestBuilder()

# Generate CSV manifest
csv_content = builder.generate_csv(
    route=[1, 2, 3],
    packages=packages,
    destinations=destinations
)

# Generate PDF manifest
pdf_bytes = builder.generate_pdf(
    route=[1, 2, 3],
    packages=packages,
    destinations=destinations,
    vehicle_name="Truck #1",
    route_cost=route_cost
)

# Save manifests
with open("route_manifest.csv", "w") as f:
    f.write(csv_content)

with open("route_manifest.pdf", "wb") as f:
    f.write(pdf_bytes)
```

**Manifest Features:**
- Stop-by-stop delivery instructions in route order
- Source and destination names for each package
- Package dimensions and weight
- Special handling indicators: ⚠️ FRAGILE, ⬆️ THIS SIDE UP
- Route summary with vehicle info and total cost
- Professional PDF formatting with headers and footers

### Dashboard Integration

All features are integrated into the Streamlit dashboard:

1. **CSV Upload**: Upload manifest files with automatic validation
2. **Fleet Configuration**: Define vehicles with fuel efficiency ratings
3. **Route Optimization**: Solve VRP with heterogeneous fleet
4. **Cost Analysis**: View fuel consumption and costs per route
5. **3D Packing Visualization**: See LIFO packing layout with constraints
6. **Manifest Download**: Export CSV and PDF driver instructions

**Running the Dashboard:**
```bash
cd dashboard
streamlit run app.py
```

### Testing

The realistic data and physics upgrade includes comprehensive test coverage:

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific feature tests
python -m pytest tests/test_csv_parser.py -v
python -m pytest tests/test_financial_engine.py -v
python -m pytest tests/test_lifo_packing.py -v
python -m pytest tests/test_manifest_builder.py -v
```

**Test Coverage:**
- CSV parser validation (coordinates, dimensions, weights)
- Financial calculations (fuel cost, labor cost, total cost)
- LIFO packing constraints (fragile, orientation, stability)
- Manifest generation (CSV and PDF formats)
- End-to-end integration workflows

## Performance Considerations

- **Sorting Overhead**: O(N log N) where N is number of vehicles (negligible for typical fleet sizes)
- **Solver Complexity**: O(V × C²) where V is vehicles and C is customers
- **Memory**: Linear in number of vehicles and customers
- **SIMD Optimization**: Available for distance calculations (use `use_simd=True`)

## Future Enhancements

The heterogeneous fleet foundation enables future features:

- **Vehicle-specific speeds**: Different travel times based on vehicle
- **Vehicle-specific time windows**: Availability constraints per vehicle
- **Vehicle-customer compatibility**: Restrictions on which vehicles can serve which customers
- **Advanced packing algorithms**: 3D bin packing with weight distribution
- **Multi-depot routing**: Support for multiple distribution centers

## 🔧 Troubleshooting

### Common Issues

**"CMake not found"**
- Install CMake from [cmake.org](https://cmake.org/download/)
- Add CMake to your system PATH

**"Compiler not found"**
- Windows: Install Visual Studio 2019+ or MinGW-w64
- Linux: `sudo apt install build-essential`
- macOS: `xcode-select --install`

**"ImportError: DLL load failed" (Windows)**
- Ensure MinGW is in your PATH
- Add DLL directories in your Python code:
  ```python
  import os
  os.add_dll_directory(r"C:\mingw64\bin")
  os.add_dll_directory(os.path.abspath("build"))
  ```

**"ModuleNotFoundError: No module named 'vrp_core'"**
- Rebuild the extension: `python setup.py`
- Check that `vrp_core.*.pyd` or `vrp_core.*.so` exists in project root

**Dashboard won't start**
- Verify you're in the `dashboard` directory
- Install dependencies: `pip install -r requirements.txt`
- Check Streamlit is installed: `pip install streamlit`

For more help, see [QUICKSTART.md](QUICKSTART.md)

## 📁 Project Structure

```
vrp-solver/
├── src/                    # C++ source files
│   ├── solver.cpp          # VRP solver implementation
│   ├── bindings.cpp        # Python bindings
│   └── test_*.cpp          # C++ test executables
├── include/
│   └── solver.h            # Public API headers
├── dashboard/              # Streamlit web dashboard
│   ├── app.py              # Main dashboard application
│   ├── csv_parser.py       # CSV manifest parser
│   ├── financial_engine.py # Cost calculations
│   ├── fleet_composer.py   # Fleet configuration
│   ├── packing_engine*.py  # 3D packing algorithms
│   └── manifest_builder.py # Driver manifest generation
├── tests/                  # Python test suite
├── build/                  # Build output (generated)
├── CMakeLists.txt          # Build configuration
├── requirements.txt        # Python dependencies
├── setup.py                # Setup script
├── setup.bat               # Windows setup
├── setup.sh                # Linux/macOS setup
├── run_dashboard.bat       # Windows dashboard launcher
├── run_dashboard.sh        # Linux/macOS dashboard launcher
├── QUICKSTART.md           # Quick start guide
└── README.md               # This file
```

## Contributing

Contributions are welcome! Please ensure:

1. All tests pass: `python -m pytest tests/ -v`
2. Code follows C++20 and Python best practices
3. New features include comprehensive tests
4. Documentation is updated

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contact

For questions, issues, or contributions, please open an issue on the project repository.
