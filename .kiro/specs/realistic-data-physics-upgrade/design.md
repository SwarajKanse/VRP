# Design Document: Realistic Data & Physics Upgrade

## Overview

This design extends the existing VRP solver system with professional logistics capabilities. The implementation adds four major components: a robust CSV parser with validation, vehicle-specific fuel cost tracking, a physics-compliant LIFO packing algorithm, and comprehensive driver manifest generation. The design maintains the existing C++ core for performance-critical operations while implementing new features primarily in Python for rapid development and integration with the Streamlit dashboard.

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit Dashboard                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ CSV Upload   │  │ Fleet Config │  │ Manifest Gen │      │
│  │ & Validation │  │ & Fuel Econ  │  │ (CSV/PDF)    │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │              │
│  ┌──────▼──────────────────▼──────────────────▼───────┐    │
│  │           Data Processing Layer                     │    │
│  │  • CSV Parser  • Fleet Composer  • Manifest Builder│    │
│  └──────┬──────────────────┬──────────────────┬───────┘    │
│         │                  │                  │              │
└─────────┼──────────────────┼──────────────────┼──────────────┘
          │                  │                  │
┌─────────▼──────────────────▼──────────────────▼──────────────┐
│              Core Processing Components                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ VRP Solver   │  │ Financial    │  │ LIFO Packing │      │
│  │ (C++ Core)   │  │ Engine       │  │ Engine       │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└───────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Input Phase**: CSV file uploaded → CSV_Parser validates and transforms data
2. **Aggregation Phase**: Parser aggregates weights per destination for solver, preserves individual packages for packer
3. **Routing Phase**: VRP Solver generates optimal routes using aggregated data
4. **Costing Phase**: Financial_Engine calculates vehicle-specific fuel and labor costs
5. **Packing Phase**: LIFO Packing_Engine arranges packages respecting constraints
6. **Output Phase**: Manifest_Builder generates CSV and PDF driver instructions

## Components and Interfaces

### 1. CSV Parser Module

**Location**: `dashboard/csv_parser.py`

**Data Structures**:
```python
@dataclass
class Package:
    order_id: str
    source_name: str
    destination_name: str
    latitude: float
    longitude: float
    length_m: float  # converted from cm
    width_m: float   # converted from cm
    height_m: float  # converted from cm
    weight_kg: float
    fragile: bool
    this_side_up: bool
    volume_m3: float  # calculated
    
@dataclass
class Destination:
    name: str
    latitude: float
    longitude: float
    total_weight_kg: float
    packages: List[Package]
```

**Interface**:
```python
class CSVParser:
    def parse_manifest(self, file_path: str) -> Tuple[List[Destination], Optional[str]]:
        """
        Parse CSV manifest and return destinations with packages.
        
        Returns:
            (destinations, error_message)
            - destinations: List of Destination objects if successful
            - error_message: None if successful, error string if validation fails
        """
        pass
    
    def _validate_coordinates(self, lat: float, lon: float, row_num: int) -> Optional[str]:
        """Validate latitude [-90, 90] and longitude [-180, 180]"""
        pass
    
    def _validate_dimensions(self, length: float, width: float, height: float, 
                            weight: float, row_num: int) -> Optional[str]:
        """Validate all dimensions and weight are positive"""
        pass
    
    def _parse_boolean(self, value: str, default: bool = False) -> bool:
        """Parse Yes/No values case-insensitively"""
        pass
    
    def _convert_to_meters(self, cm: float) -> float:
        """Convert centimeters to meters"""
        pass
```

### 2. Fleet Composer Module

**Location**: `dashboard/fleet_composer.py`

**Data Structures**:
```python
@dataclass
class VehicleType:
    name: str
    capacity_kg: float
    length_m: float
    width_m: float
    height_m: float
    fuel_efficiency_km_per_L: float  # NEW
    count: int
```

**Interface**:
```python
class FleetComposer:
    def __init__(self):
        self.vehicle_types: List[VehicleType] = []
    
    def add_vehicle_type(self, name: str, capacity_kg: float, 
                        length_m: float, width_m: float, height_m: float,
                        fuel_efficiency_km_per_L: float, count: int) -> None:
        """Add a vehicle type with fuel efficiency"""
        pass
    
    def get_vehicle_by_name(self, name: str) -> Optional[VehicleType]:
        """Retrieve vehicle type by name"""
        pass
```

### 3. Financial Engine Module

**Location**: `dashboard/financial_engine.py`

**Data Structures**:
```python
@dataclass
class RouteCost:
    route_id: int
    vehicle_name: str
    distance_km: float
    time_hours: float
    fuel_efficiency_km_per_L: float
    fuel_consumed_L: float
    fuel_cost: float
    labor_cost: float
    total_cost: float
```

**Interface**:
```python
class FinancialEngine:
    def __init__(self, fuel_price_per_L: float, driver_hourly_wage: float):
        self.fuel_price_per_L = fuel_price_per_L
        self.driver_hourly_wage = driver_hourly_wage
    
    def calculate_route_cost(self, route_distance_km: float, 
                            route_time_hours: float,
                            vehicle: VehicleType) -> RouteCost:
        """
        Calculate comprehensive route cost.
        
        Formula:
        - fuel_consumed_L = route_distance_km / vehicle.fuel_efficiency_km_per_L
        - fuel_cost = fuel_consumed_L * fuel_price_per_L
        - labor_cost = route_time_hours * driver_hourly_wage
        - total_cost = fuel_cost + labor_cost
        """
        pass
    
    def generate_cost_summary(self, route_costs: List[RouteCost]) -> Dict[str, Any]:
        """Generate summary statistics across all routes"""
        pass
```

### 4. LIFO Packing Engine Module

**Location**: `dashboard/packing_engine.py` (enhancement to existing)

**Data Structures**:
```python
@dataclass
class PlacedPackage:
    package: Package
    x: float  # back-bottom-left corner
    y: float
    z: float
    length: float  # actual dimensions after potential rotation
    width: float
    height: float
    stop_number: int
    
@dataclass
class PackingResult:
    placed_packages: List[PlacedPackage]
    failed_packages: List[Package]
    utilization_percent: float
```

**Interface**:
```python
class LIFOPackingEngine:
    def __init__(self, vehicle_length_m: float, vehicle_width_m: float, 
                 vehicle_height_m: float):
        self.vehicle_length_m = vehicle_length_m  # X dimension (back to door)
        self.vehicle_width_m = vehicle_width_m    # Y dimension
        self.vehicle_height_m = vehicle_height_m  # Z dimension
        self.placed_packages: List[PlacedPackage] = []
    
    def pack_route(self, packages: List[Package], 
                   stop_order: List[int]) -> PackingResult:
        """
        Pack packages using LIFO strategy.
        
        Algorithm:
        1. Sort packages by reverse stop order (last delivery first)
        2. Within same stop, sort by volume (largest first)
        3. Place from X=0 (back) toward X=max (door)
        4. Respect fragile and orientation constraints
        """
        pass
    
    def _sort_packages_lifo(self, packages: List[Package], 
                           stop_order: List[int]) -> List[Tuple[Package, int]]:
        """Sort packages by LIFO priority"""
        pass
    
    def _find_placement_position(self, package: Package, 
                                stop_num: int) -> Optional[Tuple[float, float, float]]:
        """Find valid (x, y, z) position for package"""
        pass
    
    def _check_fragile_constraint(self, package: Package, 
                                 x: float, y: float, z: float) -> bool:
        """Verify no packages placed on top of fragile items"""
        pass
    
    def _check_stability(self, package: Package, 
                        x: float, y: float, z: float) -> bool:
        """Verify 60% base area support"""
        pass
    
    def _can_rotate(self, package: Package) -> bool:
        """Check if package allows X/Y rotation (not this_side_up)"""
        pass
```

### 5. Manifest Builder Module

**Location**: `dashboard/manifest_builder.py`

**Interface**:
```python
class ManifestBuilder:
    def generate_csv(self, route: List[int], packages: List[Package], 
                    destinations: List[Destination]) -> str:
        """
        Generate CSV manifest with columns:
        Stop, Source Name, Destination Name, Order ID, 
        Dimensions (LxWxH cm), Weight (kg), Special Handling
        """
        pass
    
    def generate_pdf(self, route: List[int], packages: List[Package],
                    destinations: List[Destination], 
                    vehicle_name: str, route_cost: RouteCost) -> bytes:
        """
        Generate PDF manifest with:
        - Header: Route info, vehicle, total cost
        - Table: Stop-by-stop instructions with icons
        - Footer: Summary statistics
        """
        pass
    
    def _format_special_handling(self, package: Package) -> str:
        """Return '⚠️ FRAGILE' and/or '⬆️ THIS SIDE UP' as needed"""
        pass
```

## Data Models

### CSV Input Schema

```
Order ID,Source Name,Destination Name,Latitude,Longitude,Length (cm),Width (cm),Height (cm),Weight (kg),Fragile,This Side Up
ORD001,Warehouse A,Customer 1,40.7128,-74.0060,50,40,30,15.5,Yes,No
ORD002,Warehouse A,Customer 2,40.7589,-73.9851,30,30,30,8.2,No,Yes
```

### Internal Data Flow

```
CSV File
  ↓
[CSV Parser]
  ↓
Destinations (aggregated weights) + Packages (individual details)
  ↓                                    ↓
[VRP Solver]                    [Stored for Packing]
  ↓
Routes (customer order)
  ↓
[Financial Engine] ← Vehicle Fuel Efficiency
  ↓
Route Costs
  ↓
[LIFO Packing Engine] ← Packages + Route Order
  ↓
Packing Layout
  ↓
[Manifest Builder]
  ↓
CSV + PDF Manifests
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*


### CSV Parser Properties

**Property 1: Valid column acceptance**
*For any* CSV file containing all required columns (Order ID, Source Name, Destination Name, Latitude, Longitude, Length (cm), Width (cm), Height (cm), Weight (kg), Fragile, This Side Up), the parser should successfully parse the file without errors.
**Validates: Requirements 1.1**

**Property 2: Geographic coordinate validation**
*For any* CSV row, if latitude is outside [-90, 90] or longitude is outside [-180, 180], the parser should reject the row with a descriptive error message.
**Validates: Requirements 1.2, 1.3**

**Property 3: Positive numeric validation**
*For any* CSV row, if any dimension (length, width, height) or weight value is less than or equal to zero, the parser should reject the row with a descriptive error message identifying the invalid field.
**Validates: Requirements 1.4, 1.5**

**Property 4: Dimension conversion**
*For any* valid dimension value in centimeters, the parsed output should contain the value divided by 100 (converted to meters).
**Validates: Requirements 1.6**

**Property 5: Case-insensitive boolean parsing**
*For any* Fragile or This Side Up column value that is a case variation of "Yes" or "No" (e.g., "YES", "yes", "No", "NO"), the parser should successfully parse it to the appropriate boolean value.
**Validates: Requirements 1.7, 1.8**

**Property 6: Missing column error reporting**
*For any* CSV file missing one or more required columns, the parser should return an error message that lists all missing column names.
**Validates: Requirements 1.11**

**Property 7: Invalid data error reporting**
*For any* CSV row containing non-numeric values in numeric fields, the parser should return an error message identifying the row number and the invalid field name.
**Validates: Requirements 1.12**

**Property 8: Weight aggregation by destination**
*For any* set of packages with the same destination name, the aggregated destination weight should equal the sum of all individual package weights for that destination.
**Validates: Requirements 1.13**

**Property 9: Package detail preservation**
*For any* package in the input CSV, all of its attributes (order_id, dimensions, weight, constraints) should be retrievable from the parsed output with identical values.
**Validates: Requirements 1.14**

### Financial Engine Properties

**Property 10: Fuel cost calculation**
*For any* route with distance D km, vehicle with fuel efficiency E km/L, and fuel price P per liter, the calculated fuel cost should equal (D / E) * P.
**Validates: Requirements 2.2**

**Property 11: Labor cost calculation**
*For any* route with time T hours and driver wage W per hour, the calculated labor cost should equal T * W.
**Validates: Requirements 2.3**

**Property 12: Total cost composition**
*For any* route, the total cost should equal the sum of its fuel cost and labor cost.
**Validates: Requirements 2.4**

**Property 13: Vehicle-specific fuel efficiency usage**
*For any* route assigned to a specific vehicle, the fuel cost calculation should use that vehicle's fuel efficiency value, not any other vehicle's efficiency.
**Validates: Requirements 2.5**

**Property 14: Fuel consumption reporting**
*For any* route cost calculation, the output should include the fuel consumed in liters, calculated as distance_km / fuel_efficiency_km_per_L.
**Validates: Requirements 2.6, 2.8**

**Property 15: Financial report completeness**
*For any* financial report generated from multiple routes, the report should include fuel efficiency data for each distinct vehicle type used in those routes.
**Validates: Requirements 2.7**

### LIFO Packing Engine Properties

**Property 16: Coordinate system consistency**
*For any* placed package, its coordinates should satisfy: x >= 0, y >= 0, z >= 0, and x + package.length <= vehicle.length_m (door at max X).
**Validates: Requirements 3.1**

**Property 17: Primary sort by reverse stop order**
*For any* two packages A and B where A's stop number is greater than B's stop number, package A should be considered for placement before package B (LIFO ordering).
**Validates: Requirements 3.2**

**Property 18: Secondary sort by volume**
*For any* two packages A and B with the same stop number, if A's volume is greater than B's volume, package A should be considered for placement before package B.
**Validates: Requirements 3.3**

**Property 19: Placement progression toward door**
*For any* sequence of successfully placed packages sorted by placement order, the general trend should show X coordinates increasing (packages fill from back toward door).
**Validates: Requirements 3.4**

**Property 20: Fragile stacking constraint**
*For any* fragile package placed at position (x, y, z) with dimensions (l, w, h), no other package should occupy space where its bottom surface (z_min) is greater than z and its (x, y) footprint overlaps the fragile package's footprint.
**Validates: Requirements 3.5**

**Property 21: Orientation lock constraint**
*For any* package marked with this_side_up=True, the placed package's dimensions should match the original package dimensions without X/Y dimension swapping.
**Validates: Requirements 3.6**

**Property 22: Surface support requirement**
*For any* placed package, either its z coordinate equals 0 (on floor) or there exists at least one other package beneath it providing support.
**Validates: Requirements 3.7**

**Property 23: Stability percentage requirement**
*For any* placed package not on the floor (z > 0), the overlapping area between its base and supporting packages should be at least 60% of its base area.
**Validates: Requirements 3.8**

**Property 24: Visualization coordinate system**
*For any* packing visualization data, the back wall should be represented at X=0 and all package X coordinates should be non-negative with packages extending toward positive X (door direction).
**Validates: Requirements 3.10**

### Driver Manifest Properties

**Property 25: Route order preservation**
*For any* manifest generated from a route, the stops should be listed in sequential order matching the route's stop sequence.
**Validates: Requirements 4.1**

**Property 26: Complete package information**
*For any* package in the manifest, the output should include source name, destination name, dimensions (length, width, height), and weight.
**Validates: Requirements 4.2, 4.3, 4.5, 4.6**

**Property 27: Conditional special handling indicators**
*For any* package in the manifest, if fragile=True then the output should contain "⚠️ FRAGILE", and if this_side_up=True then the output should contain "⬆️ THIS SIDE UP".
**Validates: Requirements 4.7, 4.8**

**Property 28: CSV manifest structure**
*For any* manifest exported to CSV format, the CSV should be parseable and contain columns named "Source Name" and "Destination Name".
**Validates: Requirements 4.9, 4.12**

**Property 29: PDF manifest generation**
*For any* manifest data, the PDF generation should produce a valid PDF file (verifiable by PDF header signature).
**Validates: Requirements 4.10**

## Error Handling

### CSV Parser Error Handling

**Validation Errors**:
- Missing required columns → Return error listing all missing columns
- Invalid coordinates → Return error with row number and field name
- Invalid dimensions/weight → Return error with row number and field name
- Invalid boolean values → Return error with row number and acceptable values

**Error Message Format**:
```python
{
    "success": False,
    "error_type": "ValidationError",
    "message": "Detailed error description",
    "row_number": 5,  # if applicable
    "field_name": "Latitude",  # if applicable
    "invalid_value": "invalid_data"  # if applicable
}
```

### Packing Engine Error Handling

**Constraint Violations**:
- Package doesn't fit → Add to failed_packages list with reason
- Fragile constraint violated → Try alternative positions, then fail if none found
- Stability constraint violated → Try alternative positions, then fail if none found

**Graceful Degradation**:
- If some packages cannot be placed, return partial result with:
  - Successfully placed packages
  - List of failed packages with reasons
  - Utilization percentage based on placed packages

### Financial Engine Error Handling

**Invalid Input Handling**:
- Negative distance/time → Raise ValueError with descriptive message
- Zero fuel efficiency → Raise ValueError (division by zero prevention)
- Missing vehicle data → Raise KeyError with vehicle name

### Manifest Builder Error Handling

**Generation Failures**:
- Empty route → Generate manifest with header only and warning message
- Missing package data → Skip package with warning in manifest
- PDF generation failure → Fall back to CSV only with error notification

## Testing Strategy

### Dual Testing Approach

This feature requires both unit tests and property-based tests for comprehensive coverage:

**Unit Tests** focus on:
- Specific example CSV files with known outputs
- Edge cases (empty files, single package, missing optional columns)
- Error conditions (malformed CSV, invalid data types)
- Integration between components (parser → solver → packer → manifest)

**Property-Based Tests** focus on:
- Universal properties across all valid inputs
- Validation rules that must hold for any data
- Mathematical formulas that must be correct for all values
- Constraint satisfaction across random package configurations

### Property-Based Testing Configuration

**Framework**: Hypothesis (Python)

**Configuration**:
- Minimum 100 iterations per property test
- Each test tagged with: `# Feature: realistic-data-physics-upgrade, Property N: [property text]`
- Custom generators for:
  - Valid CSV data with random packages
  - Geographic coordinates within valid ranges
  - Package dimensions and weights
  - Vehicle configurations with fuel efficiency
  - Route sequences

**Example Test Structure**:
```python
from hypothesis import given, strategies as st
import hypothesis

# Feature: realistic-data-physics-upgrade, Property 8: Weight aggregation by destination
@given(packages=st.lists(package_strategy(), min_size=1))
@hypothesis.settings(max_examples=100)
def test_weight_aggregation_property(packages):
    """For any set of packages with the same destination, 
    aggregated weight equals sum of individual weights"""
    parser = CSVParser()
    destinations = parser.aggregate_by_destination(packages)
    
    for dest in destinations:
        expected_weight = sum(p.weight_kg for p in dest.packages)
        assert abs(dest.total_weight_kg - expected_weight) < 0.001
```

### Unit Testing Strategy

**CSV Parser Tests**:
- Test with sample CSV files (valid and invalid)
- Test missing column defaults
- Test error message formats
- Test dimension conversion accuracy

**Financial Engine Tests**:
- Test with known distance/efficiency/price combinations
- Test cost breakdown components
- Test report generation with multiple vehicles
- Test edge cases (zero distance, very high efficiency)

**Packing Engine Tests**:
- Test LIFO sorting with known package sets
- Test fragile constraint enforcement
- Test orientation lock enforcement
- Test stability calculations
- Test visualization coordinate generation

**Manifest Builder Tests**:
- Test CSV generation with sample routes
- Test PDF generation (verify file is valid PDF)
- Test special handling icon insertion
- Test default source name handling

### Integration Testing

**End-to-End Workflow**:
1. Upload sample CSV → Parse → Verify destinations created
2. Configure fleet → Solve routes → Verify routes generated
3. Calculate costs → Verify vehicle-specific fuel usage
4. Pack routes → Verify LIFO ordering and constraints
5. Generate manifests → Verify CSV and PDF outputs

**Test Data Sets**:
- Small dataset (5 packages, 3 destinations, 1 vehicle)
- Medium dataset (50 packages, 10 destinations, 3 vehicles)
- Large dataset (500 packages, 50 destinations, 10 vehicles)
- Edge cases (all fragile, all this_side_up, mixed constraints)

## Implementation Notes

### Performance Considerations

**CSV Parsing**:
- Use pandas for efficient CSV reading
- Validate in single pass to minimize iterations
- Cache parsed results to avoid re-parsing

**Packing Algorithm**:
- Current O(n²) complexity acceptable for typical package counts (< 1000)
- Future optimization: spatial indexing for collision detection
- Consider parallel packing for multiple routes

**Manifest Generation**:
- PDF generation can be slow for large routes
- Consider async generation for better UX
- Cache generated manifests to avoid regeneration

### Dependencies

**New Python Packages**:
- `pandas`: CSV parsing and data manipulation
- `reportlab`: PDF generation
- `hypothesis`: Property-based testing

**Existing Dependencies**:
- `streamlit`: Dashboard framework
- `plotly`: 3D visualization
- `pytest`: Unit testing framework

### Migration Path

**Phase 1**: CSV Parser and validation (standalone, testable)
**Phase 2**: Financial Engine with fuel efficiency (extends existing)
**Phase 3**: LIFO Packing Engine (replaces existing packing logic)
**Phase 4**: Manifest Builder (new feature)
**Phase 5**: Dashboard integration (wire all components together)

Each phase should be fully tested before proceeding to the next.
