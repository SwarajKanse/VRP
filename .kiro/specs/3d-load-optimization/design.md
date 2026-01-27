# Design Document: 3D Load Optimization (Bin Packing)

## Overview

This design extends the existing VRP solver with 3D bin packing capabilities to validate that routed packages physically fit inside vehicle cargo bays. The system introduces a packing engine that converts abstract demand units into physical boxes, applies a First-Fit Decreasing (FFD) heuristic to position them in 3D space, and provides interactive visualization through the Streamlit dashboard.

The design follows a layered architecture:
1. **Data Layer**: Extended vehicle and package models with 3D dimensions
2. **Packing Engine**: FFD algorithm implementation for 3D box placement
3. **Validation Layer**: Integration with VRP solver for capacity checking
4. **Visualization Layer**: Plotly-based 3D rendering in Streamlit

This feature is implemented primarily in Python (dashboard layer) with potential future optimization in C++ for the packing algorithm if performance becomes critical.

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                 Streamlit Dashboard (app.py)                 │
│  ┌────────────────┐  ┌──────────────┐  ┌─────────────────┐ │
│  │ Fleet Composer │  │ Route Solver │  │ Cargo Loading   │ │
│  │   (Sidebar)    │  │   (Main)     │  │  Plan (Tab)     │ │
│  └────────┬───────┘  └──────┬───────┘  └────────┬────────┘ │
└───────────┼──────────────────┼───────────────────┼──────────┘
            │                  │                   │
            ▼                  ▼                   ▼
┌───────────────────────────────────────────────────────────┐
│      Packing Engine (dashboard/packing_engine.py)          │
│  ┌──────────────────┐  ┌────────────────────────────────┐ │
│  │ Package Generator│  │  First-Fit Decreasing Packer   │ │
│  │  - Dimensions    │  │  - Sort by volume              │ │
│  │  - Colors        │  │  - Collision detection         │ │
│  │  - Random seed   │  │  - Position calculation        │ │
│  └──────────────────┘  └────────────────────────────────┘ │
└───────────────────────────────────────────────────────────┘
            │                                      │
            ▼                                      ▼
┌─────────────────────────┐        ┌──────────────────────────┐
│   Data Models           │        │  Visualization Renderer  │
│  - VehicleProfile       │        │  - Plotly 3D Scene       │
│  - Package              │        │  - Wireframe cargo bay   │
│  - PackingResult        │        │  - Solid package cubes   │
└─────────────────────────┘        └──────────────────────────┘
```

### Data Flow

1. **Configuration Phase**: User defines vehicle profiles with cargo bay dimensions in Streamlit sidebar
2. **Problem Setup**: VRP solver receives customers with demand units
3. **Route Generation**: Existing VRP solver creates routes based on weight capacity
4. **Package Generation**: System converts demand units to physical packages with random dimensions
5. **Packing Validation**: FFD algorithm attempts to pack packages into cargo bays
6. **Visualization**: Streamlit renders 3D scene using `st.plotly_chart()` with packed boxes and overflow indicators

### Integration Points

- **VRP Solver Integration**: Hooks into the existing `solve()` workflow after route generation
- **Dashboard Integration**: Adds new tab to existing Streamlit layout using `st.tabs()`
- **Data Model Extension**: Extends vehicle profiles without breaking existing functionality
- **Module Organization**: New `dashboard/packing_engine.py` module for packing logic

## Components and Interfaces

### 1. Extended Vehicle Profile

```python
class VehicleProfile:
    """Extended vehicle configuration with 3D cargo bay dimensions."""
    
    def __init__(
        self,
        vehicle_type: str,
        capacity: float,
        cargo_length: float = None,
        cargo_width: float = None,
        cargo_height: float = None
    ):
        self.vehicle_type = vehicle_type
        self.capacity = capacity  # Weight capacity (existing)
        
        # New 3D dimensions with defaults
        self.cargo_length = cargo_length or self._default_length()
        self.cargo_width = cargo_width or self._default_width()
        self.cargo_height = cargo_height or self._default_height()
    
    def _default_length(self) -> float:
        """Return default length based on vehicle type."""
        defaults = {"Tempo": 2.5, "Truck": 4.0, "Van": 3.0}
        return defaults.get(self.vehicle_type, 2.5)
    
    def _default_width(self) -> float:
        """Return default width based on vehicle type."""
        defaults = {"Tempo": 1.5, "Truck": 2.0, "Van": 1.8}
        return defaults.get(self.vehicle_type, 1.5)
    
    def _default_height(self) -> float:
        """Return default height based on vehicle type."""
        defaults = {"Tempo": 1.5, "Truck": 2.5, "Van": 1.8}
        return defaults.get(self.vehicle_type, 1.5)
    
    def cargo_volume(self) -> float:
        """Calculate total cargo bay volume in cubic meters."""
        return self.cargo_length * self.cargo_width * self.cargo_height
```

### 2. Package Data Model

```python
class Package:
    """Represents a physical package with 3D dimensions."""
    
    def __init__(
        self,
        package_id: int,
        customer_id: int,
        length: float,
        width: float,
        height: float,
        color: str = None
    ):
        self.package_id = package_id
        self.customer_id = customer_id
        self.length = length
        self.width = width
        self.height = height
        self.color = color or self._generate_color(customer_id)
        
        # Placement coordinates (set by packing algorithm)
        self.x: float = None
        self.y: float = None
        self.z: float = None
        self.is_placed: bool = False
    
    def volume(self) -> float:
        """Calculate package volume in cubic meters."""
        return self.length * self.width * self.height
    
    def _generate_color(self, customer_id: int) -> str:
        """Generate consistent color based on customer ID."""
        # Use hash to generate RGB values
        import hashlib
        hash_val = int(hashlib.md5(str(customer_id).encode()).hexdigest()[:6], 16)
        r = (hash_val >> 16) & 0xFF
        g = (hash_val >> 8) & 0xFF
        b = hash_val & 0xFF
        return f"rgb({r},{g},{b})"
```

### 3. Package Generator

```python
class PackageGenerator:
    """Generates physical packages from demand units."""
    
    def __init__(
        self,
        min_dimension: float = 0.3,
        max_dimension: float = 0.8,
        random_seed: int = None
    ):
        self.min_dimension = min_dimension
        self.max_dimension = max_dimension
        self.random_seed = random_seed
        self._rng = random.Random(random_seed)
    
    def generate_packages(
        self,
        customer_demands: List[Tuple[int, int]]  # [(customer_id, demand), ...]
    ) -> List[Package]:
        """Generate packages from customer demands.
        
        Args:
            customer_demands: List of (customer_id, demand_units) tuples
            
        Returns:
            List of Package objects with random dimensions
        """
        packages = []
        package_id = 0
        
        for customer_id, demand in customer_demands:
            for _ in range(demand):
                length = self._rng.uniform(self.min_dimension, self.max_dimension)
                width = self._rng.uniform(self.min_dimension, self.max_dimension)
                height = self._rng.uniform(self.min_dimension, self.max_dimension)
                
                package = Package(
                    package_id=package_id,
                    customer_id=customer_id,
                    length=length,
                    width=width,
                    height=height
                )
                packages.append(package)
                package_id += 1
        
        return packages
```

### 4. First-Fit Decreasing Packer

```python
class FirstFitDecreasingPacker:
    """3D bin packing using First-Fit Decreasing heuristic."""
    
    def __init__(
        self,
        cargo_length: float,
        cargo_width: float,
        cargo_height: float
    ):
        self.cargo_length = cargo_length
        self.cargo_width = cargo_width
        self.cargo_height = cargo_height
        self.placed_packages: List[Package] = []
    
    def pack(self, packages: List[Package]) -> PackingResult:
        """Pack packages into cargo bay using FFD algorithm.
        
        Args:
            packages: List of Package objects to pack
            
        Returns:
            PackingResult with placed and overflow packages
        """
        # Sort by volume (largest first)
        sorted_packages = sorted(packages, key=lambda p: p.volume(), reverse=True)
        
        placed = []
        overflow = []
        
        for package in sorted_packages:
            position = self._find_first_fit(package)
            
            if position is not None:
                package.x, package.y, package.z = position
                package.is_placed = True
                placed.append(package)
                self.placed_packages.append(package)
            else:
                overflow.append(package)
        
        return PackingResult(
            placed=placed,
            overflow=overflow,
            utilization=self._calculate_utilization()
        )
    
    def _find_first_fit(self, package: Package) -> Optional[Tuple[float, float, float]]:
        """Find first available position for package.
        
        Tries all 6 orientations of the package and searches for valid placement.
        
        Returns:
            (x, y, z) coordinates if fit found, None otherwise
        """
        orientations = self._get_orientations(package)
        
        for length, width, height in orientations:
            # Try placing at grid positions
            for x in self._generate_x_positions():
                for y in self._generate_y_positions():
                    for z in self._generate_z_positions():
                        if self._can_place(x, y, z, length, width, height):
                            # Update package dimensions to match orientation
                            package.length = length
                            package.width = width
                            package.height = height
                            return (x, y, z)
        
        return None
    
    def _get_orientations(self, package: Package) -> List[Tuple[float, float, float]]:
        """Generate all 6 possible orientations of a package."""
        l, w, h = package.length, package.width, package.height
        return [
            (l, w, h), (l, h, w),
            (w, l, h), (w, h, l),
            (h, l, w), (h, w, l)
        ]
    
    def _generate_x_positions(self) -> List[float]:
        """Generate candidate x positions based on placed packages."""
        positions = [0.0]
        for pkg in self.placed_packages:
            positions.append(pkg.x + pkg.length)
        return sorted(set(positions))
    
    def _generate_y_positions(self) -> List[float]:
        """Generate candidate y positions based on placed packages."""
        positions = [0.0]
        for pkg in self.placed_packages:
            positions.append(pkg.y + pkg.width)
        return sorted(set(positions))
    
    def _generate_z_positions(self) -> List[float]:
        """Generate candidate z positions based on placed packages."""
        positions = [0.0]
        for pkg in self.placed_packages:
            positions.append(pkg.z + pkg.height)
        return sorted(set(positions))
    
    def _can_place(
        self,
        x: float,
        y: float,
        z: float,
        length: float,
        width: float,
        height: float
    ) -> bool:
        """Check if package can be placed at given position.
        
        Validates:
        1. Package fits within cargo bay boundaries
        2. No collision with already placed packages
        """
        # Check cargo bay boundaries
        if x + length > self.cargo_length:
            return False
        if y + width > self.cargo_width:
            return False
        if z + height > self.cargo_height:
            return False
        
        # Check collision with placed packages
        for pkg in self.placed_packages:
            if self._boxes_overlap(
                x, y, z, length, width, height,
                pkg.x, pkg.y, pkg.z, pkg.length, pkg.width, pkg.height
            ):
                return False
        
        return True
    
    def _boxes_overlap(
        self,
        x1: float, y1: float, z1: float, l1: float, w1: float, h1: float,
        x2: float, y2: float, z2: float, l2: float, w2: float, h2: float
    ) -> bool:
        """Check if two 3D boxes overlap."""
        # Boxes overlap if they overlap in all three dimensions
        x_overlap = (x1 < x2 + l2) and (x1 + l1 > x2)
        y_overlap = (y1 < y2 + w2) and (y1 + w1 > y2)
        z_overlap = (z1 < z2 + h2) and (z1 + h1 > z2)
        
        return x_overlap and y_overlap and z_overlap
    
    def _calculate_utilization(self) -> float:
        """Calculate cargo bay volume utilization percentage."""
        total_volume = self.cargo_length * self.cargo_width * self.cargo_height
        used_volume = sum(pkg.volume() for pkg in self.placed_packages)
        return (used_volume / total_volume) * 100.0 if total_volume > 0 else 0.0
```

### 5. Packing Result

```python
class PackingResult:
    """Result of packing operation."""
    
    def __init__(
        self,
        placed: List[Package],
        overflow: List[Package],
        utilization: float
    ):
        self.placed = placed
        self.overflow = overflow
        self.utilization = utilization
    
    def is_feasible(self) -> bool:
        """Check if all packages were successfully placed."""
        return len(self.overflow) == 0
    
    def summary(self) -> dict:
        """Generate summary statistics."""
        return {
            "total_packages": len(self.placed) + len(self.overflow),
            "placed_packages": len(self.placed),
            "overflow_packages": len(self.overflow),
            "utilization_percent": round(self.utilization, 2),
            "is_feasible": self.is_feasible()
        }
```

### 6. Visualization Renderer

```python
class CargoVisualizationRenderer:
    """Renders 3D cargo loading visualization using Plotly."""
    
    def render(
        self,
        vehicle_profile: VehicleProfile,
        packing_result: PackingResult,
        vehicle_id: str = "Vehicle"
    ) -> go.Figure:
        """Create 3D visualization of cargo loading.
        
        Args:
            vehicle_profile: Vehicle with cargo bay dimensions
            packing_result: Result of packing operation
            vehicle_id: Identifier for display title
            
        Returns:
            Plotly Figure object
        """
        fig = go.Figure()
        
        # Add cargo bay wireframe
        self._add_cargo_bay_wireframe(fig, vehicle_profile)
        
        # Add placed packages as solid cubes
        for package in packing_result.placed:
            self._add_package_cube(fig, package)
        
        # Add overflow packages (if any) in separate area
        if packing_result.overflow:
            self._add_overflow_section(fig, packing_result.overflow)
        
        # Configure layout
        fig.update_layout(
            title=f"Cargo Loading Plan - {vehicle_id}",
            scene=dict(
                xaxis_title="Length (m)",
                yaxis_title="Width (m)",
                zaxis_title="Height (m)",
                aspectmode="data"
            ),
            showlegend=True
        )
        
        return fig
    
    def _add_cargo_bay_wireframe(
        self,
        fig: go.Figure,
        vehicle_profile: VehicleProfile
    ):
        """Add wireframe box representing cargo bay boundaries."""
        l = vehicle_profile.cargo_length
        w = vehicle_profile.cargo_width
        h = vehicle_profile.cargo_height
        
        # Define 12 edges of the box
        edges = [
            # Bottom face
            ([0, l], [0, 0], [0, 0]),
            ([l, l], [0, w], [0, 0]),
            ([l, 0], [w, w], [0, 0]),
            ([0, 0], [w, 0], [0, 0]),
            # Top face
            ([0, l], [0, 0], [h, h]),
            ([l, l], [0, w], [h, h]),
            ([l, 0], [w, w], [h, h]),
            ([0, 0], [w, 0], [h, h]),
            # Vertical edges
            ([0, 0], [0, 0], [0, h]),
            ([l, l], [0, 0], [0, h]),
            ([l, l], [w, w], [0, h]),
            ([0, 0], [w, w], [0, h])
        ]
        
        for x, y, z in edges:
            fig.add_trace(go.Scatter3d(
                x=x, y=y, z=z,
                mode="lines",
                line=dict(color="black", width=2),
                showlegend=False,
                hoverinfo="skip"
            ))
    
    def _add_package_cube(self, fig: go.Figure, package: Package):
        """Add solid cube representing a package."""
        x, y, z = package.x, package.y, package.z
        l, w, h = package.length, package.width, package.height
        
        # Define 8 vertices of the cube
        vertices = [
            [x, y, z],
            [x+l, y, z],
            [x+l, y+w, z],
            [x, y+w, z],
            [x, y, z+h],
            [x+l, y, z+h],
            [x+l, y+w, z+h],
            [x, y+w, z+h]
        ]
        
        # Define 6 faces using vertex indices
        faces = [
            [0, 1, 2, 3],  # Bottom
            [4, 5, 6, 7],  # Top
            [0, 1, 5, 4],  # Front
            [2, 3, 7, 6],  # Back
            [0, 3, 7, 4],  # Left
            [1, 2, 6, 5]   # Right
        ]
        
        # Create mesh for solid cube
        fig.add_trace(go.Mesh3d(
            x=[v[0] for v in vertices],
            y=[v[1] for v in vertices],
            z=[v[2] for v in vertices],
            i=[f[0] for f in faces],
            j=[f[1] for f in faces],
            k=[f[2] for f in faces],
            color=package.color,
            opacity=0.7,
            name=f"Customer {package.customer_id}",
            hovertext=f"Package {package.package_id}<br>"
                     f"Customer: {package.customer_id}<br>"
                     f"Dimensions: {l:.2f}×{w:.2f}×{h:.2f}m<br>"
                     f"Volume: {package.volume():.3f}m³",
            hoverinfo="text"
        ))
    
    def _add_overflow_section(self, fig: go.Figure, overflow: List[Package]):
        """Add visual indicator for overflow packages."""
        # Display overflow packages in a separate area (e.g., to the right)
        offset_x = 5.0  # Offset from main cargo bay
        
        for i, package in enumerate(overflow):
            # Stack overflow packages vertically
            x = offset_x
            y = 0
            z = i * 1.0  # Stack with 1m spacing
            
            fig.add_trace(go.Scatter3d(
                x=[x], y=[y], z=[z],
                mode="markers+text",
                marker=dict(size=10, color="red"),
                text=f"Overflow {i+1}",
                textposition="top center",
                name="Overflow",
                hovertext=f"Package {package.package_id}<br>"
                         f"Customer: {package.customer_id}<br>"
                         f"Dimensions: {package.length:.2f}×{package.width:.2f}×{package.height:.2f}m<br>"
                         f"OVERFLOW - Could not fit",
                hoverinfo="text"
            ))
```

## Data Models

### Vehicle Profile Extension

The existing `VehicleProfile` class (or dictionary) in the dashboard will be extended with three new fields:

```python
{
    "vehicle_type": str,      # Existing: "Tempo", "Truck", "Van"
    "capacity": float,        # Existing: Weight capacity in kg
    "cargo_length": float,    # New: Length in meters
    "cargo_width": float,     # New: Width in meters
    "cargo_height": float     # New: Height in meters
}
```

### Package Model

New data structure representing physical packages:

```python
{
    "package_id": int,        # Unique identifier
    "customer_id": int,       # Destination customer
    "length": float,          # Dimension in meters
    "width": float,           # Dimension in meters
    "height": float,          # Dimension in meters
    "color": str,             # RGB color string
    "x": float,               # Placement coordinate (nullable)
    "y": float,               # Placement coordinate (nullable)
    "z": float,               # Placement coordinate (nullable)
    "is_placed": bool         # Placement status
}
```

### Packing Result Model

```python
{
    "placed": List[Package],      # Successfully placed packages
    "overflow": List[Package],    # Packages that couldn't fit
    "utilization": float,         # Volume utilization percentage
    "is_feasible": bool          # True if no overflow
}
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Default Dimensions by Vehicle Type

*For any* vehicle type with a defined default, creating a vehicle profile without specifying dimensions should result in the profile having the correct default dimensions for that vehicle type.

**Validates: Requirements 1.2**

### Property 2: Dimension Validation

*For any* set of dimension inputs (length, width, height), the system should accept the values if and only if all three are positive numbers greater than zero.

**Validates: Requirements 1.3**

### Property 3: Vehicle Profile Persistence Round Trip

*For any* vehicle profile with cargo bay dimensions, saving the profile and then loading it should produce a profile with identical dimension values.

**Validates: Requirements 1.5**

### Property 4: Demand to Package Count Invariant

*For any* list of customer demands, the total number of generated packages should equal the sum of all demand units.

**Validates: Requirements 2.1**

### Property 5: Package Dimension Bounds

*For any* generated package, all three dimensions (length, width, height) should fall within the configured minimum and maximum dimension range.

**Validates: Requirements 2.2**

### Property 6: Package Structural Completeness

*For any* generated package, it should have all three dimension fields (length, width, height) populated with valid positive numbers.

**Validates: Requirements 2.3**

### Property 7: Color Consistency by Customer

*For any* set of packages, all packages with the same customer ID should have identical color values, and packages with different customer IDs should have different colors.

**Validates: Requirements 2.4, 2.5**

### Property 8: Deterministic Generation with Seed

*For any* random seed value and customer demand list, generating packages twice with the same seed should produce packages with identical dimensions in the same order.

**Validates: Requirements 2.6**

### Property 9: Volume-Based Sorting

*For any* list of packages, after applying the FFD sorting step, the packages should be ordered by volume in descending order (largest first).

**Validates: Requirements 3.1**

### Property 10: No Package Overlap

*For any* packing result, no two placed packages should overlap in 3D space (their bounding boxes should not intersect).

**Validates: Requirements 3.3**

### Property 11: Package Classification Completeness

*For any* packing operation, every input package should appear in exactly one of two lists: either in the placed packages list (with valid x, y, z coordinates) or in the overflow list.

**Validates: Requirements 3.4, 3.7**

### Property 12: Cargo Bay Boundary Compliance

*For any* placed package in a packing result, the package's position plus its dimensions should not exceed the cargo bay boundaries in any dimension (x+length ≤ cargo_length, y+width ≤ cargo_width, z+height ≤ cargo_height).

**Validates: Requirements 3.5**

### Property 13: Visualization Completeness for Placed Packages

*For any* packing result with placed packages, the generated Plotly figure should contain mesh traces for all placed packages, with each trace using the package's assigned color.

**Validates: Requirements 4.4**

### Property 14: Overflow Visualization Distinctness

*For any* packing result with overflow packages, the generated Plotly figure should contain distinct visual markers (e.g., red scatter points) for all overflow packages.

**Validates: Requirements 4.7**

### Property 15: Package Hover Information Completeness

*For any* package in the visualization, the hover text should contain the package ID, customer ID, dimensions, and volume information.

**Validates: Requirements 4.8**

### Property 16: Utilization Calculation Accuracy

*For any* packing result, the utilization percentage should equal (sum of placed package volumes / cargo bay volume) × 100, within a small tolerance for floating-point precision.

**Validates: Requirements 5.3**

### Property 17: Summary Statistics Completeness

*For any* packing result, the summary should contain all required fields: total_packages, placed_packages, overflow_packages, utilization_percent, and is_feasible, with values that are mathematically consistent (total = placed + overflow).

**Validates: Requirements 5.5**

## Error Handling

### Input Validation Errors

**Invalid Dimensions**:
- **Condition**: User provides zero, negative, or non-numeric dimension values
- **Response**: Reject input with clear error message indicating valid range (positive numbers)
- **Recovery**: Prompt user to provide valid dimensions or use defaults

**Invalid Package Range**:
- **Condition**: Min dimension > max dimension in package generator configuration
- **Response**: Raise `ValueError` with descriptive message
- **Recovery**: Swap values or prompt for correction

### Packing Errors

**Overflow Condition**:
- **Condition**: One or more packages cannot fit in cargo bay
- **Response**: Mark packages as overflow, continue packing remaining packages
- **Recovery**: Report overflow to user with suggestions (use larger vehicle, reduce demand)
- **Note**: This is not an error but an expected condition that should be handled gracefully

**Empty Package List**:
- **Condition**: Attempting to pack with no packages
- **Response**: Return empty packing result with 0% utilization
- **Recovery**: No action needed, valid edge case

### Visualization Errors

**Missing Data**:
- **Condition**: Attempting to visualize before packing is complete
- **Response**: Display placeholder message "No packing data available"
- **Recovery**: Ensure packing runs before visualization

**Invalid Vehicle Selection**:
- **Condition**: User selects vehicle ID that doesn't exist in solution
- **Response**: Display error message and default to first vehicle
- **Recovery**: Update vehicle selector to show only valid options

### Integration Errors

**VRP Solver Failure**:
- **Condition**: VRP solver fails to generate routes
- **Response**: Skip packing validation, display solver error
- **Recovery**: Fix VRP solver issue before attempting packing

**Missing Vehicle Profile**:
- **Condition**: Route references vehicle type without defined cargo dimensions
- **Response**: Use default dimensions with warning message
- **Recovery**: Prompt user to define vehicle profile properly

## Testing Strategy

### Dual Testing Approach

This feature requires both unit tests and property-based tests for comprehensive coverage:

- **Unit tests**: Verify specific examples, edge cases, and error conditions
- **Property tests**: Verify universal properties across all inputs using randomized testing

Together, these approaches ensure both concrete correctness (unit tests catch specific bugs) and general correctness (property tests verify behavior across the input space).

### Property-Based Testing Configuration

**Library Selection**: Use `hypothesis` for Python property-based testing

**Test Configuration**:
- Minimum 100 iterations per property test (due to randomization)
- Each property test must reference its design document property
- Tag format: `# Feature: 3d-load-optimization, Property {number}: {property_text}`

**Example Property Test Structure**:

```python
from hypothesis import given, strategies as st
import pytest

@given(
    vehicle_type=st.sampled_from(["Tempo", "Truck", "Van"]),
)
def test_default_dimensions_by_vehicle_type(vehicle_type):
    """
    Feature: 3d-load-optimization, Property 1: Default Dimensions by Vehicle Type
    
    For any vehicle type with a defined default, creating a vehicle profile
    without specifying dimensions should result in the profile having the
    correct default dimensions for that vehicle type.
    """
    profile = VehicleProfile(vehicle_type=vehicle_type, capacity=1000.0)
    
    # Verify dimensions are set to defaults
    assert profile.cargo_length > 0
    assert profile.cargo_width > 0
    assert profile.cargo_height > 0
    
    # Verify correct defaults for known types
    expected_defaults = {
        "Tempo": (2.5, 1.5, 1.5),
        "Truck": (4.0, 2.0, 2.5),
        "Van": (3.0, 1.8, 1.8)
    }
    
    if vehicle_type in expected_defaults:
        expected_l, expected_w, expected_h = expected_defaults[vehicle_type]
        assert profile.cargo_length == expected_l
        assert profile.cargo_width == expected_w
        assert profile.cargo_height == expected_h
```

### Unit Testing Focus Areas

**Specific Examples**:
- Test packing a known set of packages into a known cargo bay
- Verify specific overflow scenarios (e.g., one package too large)
- Test visualization rendering with sample data

**Edge Cases**:
- Empty package list (zero demand)
- Single package that exactly fills cargo bay
- All packages overflow (cargo bay too small)
- Packages with identical dimensions
- Very small packages (near minimum dimension)
- Very large packages (near cargo bay size)

**Error Conditions**:
- Invalid dimension inputs (negative, zero, non-numeric)
- Invalid package range (min > max)
- Missing vehicle profile data
- Malformed packing results

**Integration Points**:
- VRP solver to packing engine integration
- Packing engine to visualization integration
- Dashboard UI component interactions

### Test Organization

```
tests/
├── test_vehicle_profile.py          # Vehicle profile tests
├── test_package_generator.py        # Package generation tests
├── test_packing_algorithm.py        # FFD packing tests
├── test_visualization.py            # Visualization rendering tests
├── test_integration.py              # End-to-end integration tests
└── test_properties.py               # Property-based tests
```

### Coverage Goals

- **Line Coverage**: Minimum 90% for core packing logic
- **Branch Coverage**: Minimum 85% for conditional logic
- **Property Coverage**: All 17 correctness properties implemented as tests
- **Edge Case Coverage**: All identified edge cases have explicit unit tests

### Performance Testing

While not part of the initial implementation, future performance testing should validate:

- Packing time scales reasonably with package count (target: < 1 second for 100 packages)
- Visualization rendering time is acceptable (target: < 2 seconds for 50 packages)
- Memory usage remains bounded for large problem instances

### Test Execution

```bash
# Run all tests
python -m pytest tests/ -v

# Run property-based tests with more iterations
python -m pytest tests/test_properties.py -v --hypothesis-profile=thorough

# Run specific test file
python -m pytest tests/test_packing_algorithm.py -v

# Run with coverage report
python -m pytest tests/ --cov=dashboard --cov-report=html
```
