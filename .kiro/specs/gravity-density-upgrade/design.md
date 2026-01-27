# Design Document: Gravity & Density Upgrade

## Overview

This design enhances the existing LIFO packing engine with a Gravity-Driven Deepest-Bottom-Left (DBL) algorithm that enforces strict physics constraints while maintaining the critical LIFO (Last-In-First-Out) delivery order. The DBL approach replaces the simple First-Fit placement strategy with an intelligent contact point-based system that maximizes cargo density by placing packages as close as possible to the back-bottom-left corner (0,0,0) of the vehicle.

The implementation preserves the existing LIFO sorting logic (reverse stop order with weight-based secondary sort) while introducing three key enhancements:

1. **Contact Point Strategy**: Instead of scanning a grid, the system generates candidate placement positions from the corners and edges of already-placed packages
2. **Strict Gravity Enforcement**: Packages must have at least 80% of their base area supported by packages below (no floating boxes)
3. **Stackability Rules**: Heavy packages cannot be placed on lighter packages (weight ratio constraint of 1.5x)

The design maintains compatibility with the existing Python dashboard and C++ VRP solver core, implementing the new packing logic entirely in Python for rapid iteration and testing.

## Architecture

### System Context

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit Dashboard                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ CSV Upload   │  │ Fleet Config │  │ Visualization│      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │              │
│  ┌──────▼──────────────────▼──────────────────▼───────┐    │
│  │           Route Planning & Packing Layer            │    │
│  │  • VRP Solver  • DBL Packing Engine  • Visualizer  │    │
│  └──────┬──────────────────┬──────────────────┬───────┘    │
│         │                  │                  │              │
└─────────┼──────────────────┼──────────────────┼──────────────┘
          │                  │                  │
┌─────────▼──────────────────▼──────────────────▼──────────────┐
│              Core Processing Components                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ VRP Solver   │  │ DBL Packing  │  │ Contact Point│      │
│  │ (C++ Core)   │  │ Engine       │  │ Generator    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└───────────────────────────────────────────────────────────────┘
```

### Component Interaction Flow

```
Packages + Route Order
         ↓
[LIFO Sorter]
  • Primary: Reverse stop order
  • Secondary: Weight descending
         ↓
Sorted Package Queue
         ↓
[DBL Placement Loop] ←──────┐
         ↓                   │
[Contact Point Generator]   │
         ↓                   │
Candidate Positions         │
         ↓                   │
[Placement Validator]       │
  • Boundary check          │
  • Overlap check           │
  • Support check (80%)     │
  • Weight check (1.5x)     │
         ↓                   │
Valid Position?             │
  Yes → Place Package ──────┘
  No  → Try Next Contact Point
         ↓
All Packages Processed
         ↓
Packing Result (placed + failed)
```

## Components and Interfaces

### 1. DBL Packing Engine (Enhanced)

**Location**: `dashboard/packing_engine.py` (replaces/enhances existing LIFOPackingEngine)

**Data Structures**:
```python
from dataclasses import dataclass
from typing import List, Tuple, Optional
import math

@dataclass
class Package:
    """Package with physical properties and constraints"""
    order_id: str
    length_m: float
    width_m: float
    height_m: float
    weight_kg: float
    stop_number: int
    fragile: bool = False
    this_side_up: bool = False
    
    @property
    def volume_m3(self) -> float:
        return self.length_m * self.width_m * self.height_m
    
    @property
    def base_area_m2(self) -> float:
        return self.length_m * self.width_m

@dataclass
class ContactPoint:
    """Candidate placement position in 3D space"""
    x: float
    y: float
    z: float
    euclidean_distance: float  # Distance from origin (0,0,0)
    
    def __lt__(self, other):
        """Sort by distance, then Z, then X, then Y"""
        if abs(self.euclidean_distance - other.euclidean_distance) < 0.001:
            if abs(self.z - other.z) < 0.001:
                if abs(self.x - other.x) < 0.001:
                    return self.y < other.y
                return self.x < other.x
            return self.z < other.z
        return self.euclidean_distance < other.euclidean_distance

@dataclass
class PlacedPackage:
    """Package with its final 3D position"""
    package: Package
    x: float  # back-bottom-left corner
    y: float
    z: float
    length: float  # actual dimensions (may be rotated)
    width: float
    height: float
    
    @property
    def x_max(self) -> float:
        return self.x + self.length
    
    @property
    def y_max(self) -> float:
        return self.y + self.width
    
    @property
    def z_max(self) -> float:
        return self.z + self.height
    
    def overlaps_xy(self, other: 'PlacedPackage') -> bool:
        """Check if XY footprints overlap"""
        return not (self.x_max <= other.x or other.x_max <= self.x or
                   self.y_max <= other.y or other.y_max <= self.y)
    
    def get_support_area(self, other: 'PlacedPackage') -> float:
        """Calculate overlapping area with another package below"""
        if self.z != other.z_max:
            return 0.0
        
        # Calculate rectangle intersection
        x_overlap = max(0, min(self.x_max, other.x_max) - max(self.x, other.x))
        y_overlap = max(0, min(self.y_max, other.y_max) - max(self.y, other.y))
        return x_overlap * y_overlap

@dataclass
class PackingResult:
    """Result of packing operation"""
    placed_packages: List[PlacedPackage]
    failed_packages: List[Tuple[Package, str]]  # (package, failure_reason)
    utilization_percent: float
    total_weight_kg: float
```

**Main Interface**:
```python
class DBLPackingEngine:
    """Deepest-Bottom-Left packing engine with gravity constraints"""
    
    def __init__(self, vehicle_length_m: float, vehicle_width_m: float, 
                 vehicle_height_m: float):
        self.vehicle_length_m = vehicle_length_m  # X dimension (back to door)
        self.vehicle_width_m = vehicle_width_m    # Y dimension
        self.vehicle_height_m = vehicle_height_m  # Z dimension
        self.placed_packages: List[PlacedPackage] = []
        self.contact_points: List[ContactPoint] = []
    
    def pack_route(self, packages: List[Package]) -> PackingResult:
        """
        Pack packages using DBL algorithm with LIFO sorting.
        
        Algorithm:
        1. Sort packages by LIFO priority (reverse stop, then weight)
        2. Initialize contact points with origin (0,0,0)
        3. For each package:
           a. Generate/update contact points
           b. Try each contact point (sorted by distance)
           c. Validate placement (boundary, overlap, support, weight)
           d. Place at first valid position
           e. Update contact points
        4. Return placed and failed packages
        """
        # Sort packages using LIFO strategy
        sorted_packages = self._sort_packages_lifo(packages)
        
        # Initialize with origin
        self.contact_points = [ContactPoint(0, 0, 0, 0)]
        self.placed_packages = []
        failed_packages = []
        
        for package in sorted_packages:
            placed = self._try_place_package(package)
            if not placed:
                reason = self._get_failure_reason(package)
                failed_packages.append((package, reason))
        
        # Calculate utilization
        utilization = self._calculate_utilization()
        total_weight = sum(p.package.weight_kg for p in self.placed_packages)
        
        return PackingResult(
            placed_packages=self.placed_packages,
            failed_packages=failed_packages,
            utilization_percent=utilization,
            total_weight_kg=total_weight
        )
    
    def _sort_packages_lifo(self, packages: List[Package]) -> List[Package]:
        """
        Sort packages by LIFO priority:
        1. Primary: Reverse stop order (higher stop number first)
        2. Secondary: Weight descending (heavier first within same stop)
        """
        return sorted(packages, 
                     key=lambda p: (-p.stop_number, -p.weight_kg))
    
    def _try_place_package(self, package: Package) -> bool:
        """Try to place package at best available contact point"""
        # Sort contact points by DBL heuristic
        sorted_points = sorted(self.contact_points)
        
        for cp in sorted_points:
            if self._can_place_at(package, cp.x, cp.y, cp.z):
                self._place_package_at(package, cp.x, cp.y, cp.z)
                self._update_contact_points(package, cp.x, cp.y, cp.z)
                return True
        
        return False
    
    def _can_place_at(self, package: Package, x: float, y: float, z: float) -> bool:
        """Validate all placement constraints"""
        # 1. Boundary check
        if not self._check_boundaries(package, x, y, z):
            return False
        
        # 2. Overlap check
        if self._check_overlap(package, x, y, z):
            return False
        
        # 3. Support check (if not on floor)
        if z > 0 and not self._check_support(package, x, y, z):
            return False
        
        # 4. Weight check (stackability)
        if not self._check_weight_constraint(package, x, y, z):
            return False
        
        return True
    
    def _check_boundaries(self, package: Package, x: float, y: float, z: float) -> bool:
        """Check if package fits within vehicle boundaries"""
        return (x + package.length_m <= self.vehicle_length_m and
                y + package.width_m <= self.vehicle_width_m and
                z + package.height_m <= self.vehicle_height_m)
    
    def _check_overlap(self, package: Package, x: float, y: float, z: float) -> bool:
        """Check if package overlaps with any placed package"""
        test_package = PlacedPackage(package, x, y, z, 
                                    package.length_m, package.width_m, package.height_m)
        
        for placed in self.placed_packages:
            if self._packages_overlap_3d(test_package, placed):
                return True
        
        return False
    
    def _packages_overlap_3d(self, p1: PlacedPackage, p2: PlacedPackage) -> bool:
        """Check if two packages overlap in 3D space"""
        x_overlap = not (p1.x_max <= p2.x or p2.x_max <= p1.x)
        y_overlap = not (p1.y_max <= p2.y or p2.y_max <= p1.y)
        z_overlap = not (p1.z_max <= p2.z or p2.z_max <= p1.z)
        return x_overlap and y_overlap and z_overlap
    
    def _check_support(self, package: Package, x: float, y: float, z: float) -> bool:
        """
        Check 80% support rule.
        Package must have at least 80% of base area supported by packages below.
        """
        test_package = PlacedPackage(package, x, y, z,
                                    package.length_m, package.width_m, package.height_m)
        
        total_support_area = 0.0
        for placed in self.placed_packages:
            if placed.z_max == z:  # Package directly below
                support_area = test_package.get_support_area(placed)
                total_support_area += support_area
        
        required_support = package.base_area_m2 * 0.80
        return total_support_area >= required_support
    
    def _check_weight_constraint(self, package: Package, x: float, y: float, z: float) -> bool:
        """
        Check stackability: Weight(above) <= Weight(below) * 1.5
        Must hold for all supporting packages.
        """
        if z == 0:  # On floor, no weight constraint
            return True
        
        test_package = PlacedPackage(package, x, y, z,
                                    package.length_m, package.width_m, package.height_m)
        
        # Find all packages that would support this package
        for placed in self.placed_packages:
            if placed.z_max == z and test_package.overlaps_xy(placed):
                # Check weight ratio
                if package.weight_kg > placed.package.weight_kg * 1.5:
                    return False
        
        return True
    
    def _place_package_at(self, package: Package, x: float, y: float, z: float):
        """Add package to placed list"""
        placed = PlacedPackage(package, x, y, z,
                              package.length_m, package.width_m, package.height_m)
        self.placed_packages.append(placed)
    
    def _update_contact_points(self, package: Package, x: float, y: float, z: float):
        """Generate new contact points from placed package"""
        # Remove occupied contact point
        self.contact_points = [cp for cp in self.contact_points 
                              if not (abs(cp.x - x) < 0.001 and 
                                     abs(cp.y - y) < 0.001 and 
                                     abs(cp.z - z) < 0.001)]
        
        # Add new contact points
        new_points = [
            # Right edge
            ContactPoint(x + package.length_m, y, z, 
                        self._euclidean_distance(x + package.length_m, y, z)),
            # Front edge
            ContactPoint(x, y + package.width_m, z,
                        self._euclidean_distance(x, y + package.width_m, z)),
            # Top corner
            ContactPoint(x, y, z + package.height_m,
                        self._euclidean_distance(x, y, z + package.height_m))
        ]
        
        # Filter out points outside boundaries or occupied
        for point in new_points:
            if self._is_valid_contact_point(point):
                self.contact_points.append(point)
    
    def _is_valid_contact_point(self, cp: ContactPoint) -> bool:
        """Check if contact point is within boundaries and not occupied"""
        # Check boundaries
        if (cp.x >= self.vehicle_length_m or 
            cp.y >= self.vehicle_width_m or 
            cp.z >= self.vehicle_height_m):
            return False
        
        # Check if occupied by existing package
        for placed in self.placed_packages:
            if (placed.x <= cp.x < placed.x_max and
                placed.y <= cp.y < placed.y_max and
                placed.z <= cp.z < placed.z_max):
                return False
        
        return True
    
    def _euclidean_distance(self, x: float, y: float, z: float) -> float:
        """Calculate distance from origin"""
        return math.sqrt(x**2 + y**2 + z**2)
    
    def _calculate_utilization(self) -> float:
        """Calculate volume utilization percentage"""
        vehicle_volume = (self.vehicle_length_m * 
                         self.vehicle_width_m * 
                         self.vehicle_height_m)
        
        if vehicle_volume == 0:
            return 0.0
        
        used_volume = sum(p.package.volume_m3 for p in self.placed_packages)
        return (used_volume / vehicle_volume) * 100.0
    
    def _get_failure_reason(self, package: Package) -> str:
        """Determine why package couldn't be placed"""
        # Try to diagnose the failure
        if package.volume_m3 > (self.vehicle_length_m * 
                               self.vehicle_width_m * 
                               self.vehicle_height_m):
            return "Package too large for vehicle"
        
        # Check if any dimension exceeds vehicle
        if (package.length_m > self.vehicle_length_m or
            package.width_m > self.vehicle_width_m or
            package.height_m > self.vehicle_height_m):
            return "Package dimension exceeds vehicle dimension"
        
        # Otherwise, likely stability or weight constraint
        return "Failed stability or weight constraints"
```

### 2. Contact Point Generator

**Integrated into DBLPackingEngine** (see `_update_contact_points` method above)

**Algorithm**:
```
For each placed package P at position (x, y, z):
  Generate three new contact points:
    1. Right edge: (x + P.length, y, z)
    2. Front edge: (x, y + P.width, z)
    3. Top corner: (x, y, z + P.height)
  
  Filter contact points:
    - Remove if outside vehicle boundaries
    - Remove if occupied by existing package
    - Remove if duplicate (within tolerance)
```

### 3. Placement Validator

**Integrated into DBLPackingEngine** (see `_can_place_at` and related methods)

**Validation Sequence**:
```
1. Boundary Check:
   x + package.length <= vehicle.length
   y + package.width <= vehicle.width
   z + package.height <= vehicle.height

2. Overlap Check:
   For each placed package:
     Check 3D intersection
     If overlap detected → FAIL

3. Support Check (if z > 0):
   Find all packages with z_max == current_z
   Calculate total overlapping area
   If total_area < 0.80 * package.base_area → FAIL

4. Weight Check:
   For each supporting package:
     If package.weight > support.weight * 1.5 → FAIL
```

## Data Models

### Package Data Flow

```
CSV Input (from realistic-data-physics-upgrade)
         ↓
Package Objects (with stop_number assigned)
         ↓
[LIFO Sorter]
         ↓
Sorted Package Queue
         ↓
[DBL Packing Engine]
         ↓
PlacedPackage Objects (with x, y, z coordinates)
         ↓
Visualization / Manifest Generation
```

### Coordinate System

```
Vehicle Coordinate System:
  Origin (0,0,0) = Back-Bottom-Left corner
  X-axis: Back (0) → Door (max)
  Y-axis: Left (0) → Right (max)
  Z-axis: Floor (0) → Ceiling (max)

Example 3m x 2m x 2m vehicle:
  Back wall: X = 0
  Door: X = 3.0
  Left wall: Y = 0
  Right wall: Y = 2.0
  Floor: Z = 0
  Ceiling: Z = 2.0
```

### Contact Point Priority

```
Contact points sorted by:
  1. Euclidean Distance (ascending) - closer to origin preferred
  2. Z coordinate (ascending) - lower preferred (tie-breaker)
  3. X coordinate (ascending) - back preferred (tie-breaker)
  4. Y coordinate (ascending) - left preferred (tie-breaker)

Example:
  CP1: (0.5, 0.5, 0.0) → distance = 0.707
  CP2: (1.0, 0.0, 0.0) → distance = 1.000
  CP3: (0.0, 1.0, 0.0) → distance = 1.000
  CP4: (0.0, 0.0, 1.0) → distance = 1.000
  
  Order: CP1, CP2, CP3, CP4
  (CP2, CP3, CP4 have same distance, so Z breaks tie: CP2 and CP3 at Z=0 win)
  (CP2 and CP3 have same Z, so X breaks tie: CP2 at X=1.0 vs CP3 at X=0.0 → CP3 wins)
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*


### Support and Gravity Properties

**Property 1: 80% Support Threshold**
*For any* package placed at height z > 0, the placement should be accepted if and only if at least 80% of the package's bottom surface area is supported by packages below it.
**Validates: Requirements 1.1, 1.2**

**Property 2: Floor Placement Exemption**
*For any* package placed at z = 0 (floor level), the placement should be accepted without support validation, regardless of what packages are around it.
**Validates: Requirements 1.3**

**Property 3: Bridge Support Calculation**
*For any* package placed across multiple supporting packages (with gaps between them), the total support area should equal the sum of all individual overlapping areas with supporting packages, and placement should succeed if this total is ≥ 80% of the package's base area.
**Validates: Requirements 1.4, 1.5**

### DBL Heuristic Properties

**Property 4: Euclidean Distance Calculation**
*For any* contact point at position (x, y, z), the calculated Euclidean distance should equal √(x² + y² + z²) within floating-point tolerance.
**Validates: Requirements 2.3**

**Property 5: Minimum Distance Selection**
*For any* package placement, if multiple valid contact points exist, the selected placement position should have the minimum Euclidean distance to the origin among all valid positions.
**Validates: Requirements 2.4**

**Property 6: Distance Tie-Breaking**
*For any* two valid contact points with equal Euclidean distances (within tolerance), the selected position should have lower Z coordinate; if Z is also equal, lower X coordinate; if X is also equal, lower Y coordinate.
**Validates: Requirements 2.5**

**Property 7: Placement Failure Reporting**
*For any* package that cannot be placed at any contact point, the packing result should include that package in the failed list with a non-empty failure reason.
**Validates: Requirements 2.6**

### LIFO Sorting Properties

**Property 8: Primary Sort by Reverse Stop Order**
*For any* two packages A and B where A's stop number is greater than B's stop number, package A should appear before package B in the sorted package queue (LIFO ordering).
**Validates: Requirements 3.1**

**Property 9: Secondary Sort by Weight**
*For any* two packages A and B with the same stop number, if A's weight is greater than B's weight, package A should appear before package B in the sorted package queue.
**Validates: Requirements 3.2**

### Stackability Properties

**Property 10: Weight Ratio Constraint**
*For any* package A placed on top of package B (where B's top surface supports A's bottom surface), the weight of A should be less than or equal to 1.5 times the weight of B.
**Validates: Requirements 3.3, 3.5**

### Contact Point Generation Properties

**Property 11: Initial Contact Point**
*For any* empty cargo space (no packages placed), the contact point list should contain exactly one point at the origin (0, 0, 0).
**Validates: Requirements 4.1**

**Property 12: Contact Point Generation from Placed Package**
*For any* package P placed at position (x, y, z) with dimensions (length, width, height), the system should generate three new contact points at: (x + length, y, z), (x, y + width, z), and (x, y, z + height), subject to boundary and occupancy filtering.
**Validates: Requirements 4.2**

**Property 13: Boundary Filtering**
*For any* generated contact point (x, y, z), if x ≥ vehicle_length or y ≥ vehicle_width or z ≥ vehicle_height, that contact point should not appear in the valid contact point list.
**Validates: Requirements 4.3**

**Property 14: Occupancy Filtering**
*For any* generated contact point (x, y, z), if that point lies inside the 3D volume of an already-placed package, that contact point should not appear in the valid contact point list.
**Validates: Requirements 4.4**

### Error Reporting Properties

**Property 15: Failure Reason Reporting**
*For any* package in the failed packages list, the associated failure reason should be a non-empty string describing why the package couldn't be placed.
**Validates: Requirements 5.3**

**Property 16: Failure Type Categorization**
*For any* package that fails to place, if any dimension exceeds the corresponding vehicle dimension, the failure reason should indicate "size overflow"; otherwise, if the package fails support or weight constraints, the failure reason should indicate "stability constraints".
**Validates: Requirements 5.4**

## Error Handling

### Placement Validation Errors

**Constraint Violation Handling**:
- **Boundary Violation**: Package dimensions exceed vehicle dimensions → Add to failed list with reason "Package dimension exceeds vehicle dimension"
- **Overlap Violation**: Package would intersect with existing package → Try next contact point
- **Support Violation**: Package has < 80% support → Try next contact point
- **Weight Violation**: Package exceeds 1.5x weight ratio → Try next contact point

**Graceful Degradation**:
- If a package cannot be placed at any contact point, add to failed list with diagnostic reason
- Continue processing remaining packages
- Return partial result with both placed and failed packages

### Contact Point Generation Errors

**Invalid Contact Point Handling**:
- Contact point outside boundaries → Filter out, don't add to list
- Contact point occupied by existing package → Filter out, don't add to list
- Duplicate contact point (within tolerance) → Keep only one instance

### Input Validation Errors

**Invalid Package Data**:
- Negative dimensions → Raise ValueError with descriptive message
- Zero dimensions → Raise ValueError with descriptive message
- Negative weight → Raise ValueError with descriptive message
- Invalid stop number → Raise ValueError with descriptive message

**Invalid Vehicle Configuration**:
- Zero or negative vehicle dimensions → Raise ValueError
- Vehicle dimensions too small for any package → Warning in packing result

## Testing Strategy

### Dual Testing Approach

This feature requires both unit tests and property-based tests for comprehensive coverage:

**Unit Tests** focus on:
- Specific packing scenarios with known outcomes
- Edge cases (single package, empty vehicle, oversized package)
- Error conditions (invalid dimensions, constraint violations)
- Integration with existing LIFO packing engine
- Visualization data generation

**Property-Based Tests** focus on:
- Universal properties across all valid inputs
- Support calculation correctness for random configurations
- DBL heuristic behavior with random package sets
- LIFO sorting correctness for random stop orders
- Constraint validation across random placements

### Property-Based Testing Configuration

**Framework**: Hypothesis (Python)

**Configuration**:
- Minimum 100 iterations per property test
- Each test tagged with: `# Feature: gravity-density-upgrade, Property N: [property text]`
- Custom generators for:
  - Valid packages with random dimensions, weights, and stop numbers
  - Vehicle configurations with random dimensions
  - Placement positions within vehicle boundaries
  - Contact point configurations

**Example Test Structure**:
```python
from hypothesis import given, strategies as st
import hypothesis

# Feature: gravity-density-upgrade, Property 1: 80% Support Threshold
@given(
    package=package_strategy(),
    supporting_packages=st.lists(placed_package_strategy(), min_size=1, max_size=5),
    z_position=st.floats(min_value=0.1, max_value=2.0)
)
@hypothesis.settings(max_examples=100)
def test_support_threshold_property(package, supporting_packages, z_position):
    """For any package at z > 0, placement accepted iff support >= 80%"""
    engine = DBLPackingEngine(3.0, 2.0, 2.0)
    
    # Pre-place supporting packages
    for sp in supporting_packages:
        engine.placed_packages.append(sp)
    
    # Calculate expected support
    test_placed = PlacedPackage(package, 0, 0, z_position,
                               package.length_m, package.width_m, package.height_m)
    total_support = sum(test_placed.get_support_area(sp) for sp in supporting_packages
                       if sp.z_max == z_position)
    support_ratio = total_support / package.base_area_m2
    
    # Test placement
    can_place = engine._check_support(package, 0, 0, z_position)
    
    # Verify property
    if support_ratio >= 0.80:
        assert can_place, f"Should accept with {support_ratio:.2%} support"
    else:
        assert not can_place, f"Should reject with {support_ratio:.2%} support"
```

**Custom Generators**:
```python
import hypothesis.strategies as st

@st.composite
def package_strategy(draw):
    """Generate random valid package"""
    return Package(
        order_id=draw(st.text(min_size=1, max_size=10)),
        length_m=draw(st.floats(min_value=0.1, max_value=2.0)),
        width_m=draw(st.floats(min_value=0.1, max_value=2.0)),
        height_m=draw(st.floats(min_value=0.1, max_value=2.0)),
        weight_kg=draw(st.floats(min_value=0.1, max_value=100.0)),
        stop_number=draw(st.integers(min_value=1, max_value=10)),
        fragile=draw(st.booleans()),
        this_side_up=draw(st.booleans())
    )

@st.composite
def placed_package_strategy(draw):
    """Generate random placed package"""
    package = draw(package_strategy())
    return PlacedPackage(
        package=package,
        x=draw(st.floats(min_value=0.0, max_value=2.0)),
        y=draw(st.floats(min_value=0.0, max_value=1.5)),
        z=draw(st.floats(min_value=0.0, max_value=1.5)),
        length=package.length_m,
        width=package.width_m,
        height=package.height_m
    )

@st.composite
def contact_point_strategy(draw):
    """Generate random contact point"""
    x = draw(st.floats(min_value=0.0, max_value=3.0))
    y = draw(st.floats(min_value=0.0, max_value=2.0))
    z = draw(st.floats(min_value=0.0, max_value=2.0))
    return ContactPoint(x, y, z, math.sqrt(x**2 + y**2 + z**2))
```

### Unit Testing Strategy

**Support Calculation Tests**:
- Test with single supporting package (100% support)
- Test with multiple supporting packages (bridge scenario)
- Test with partial support (< 80%)
- Test with no support (floating package)
- Test floor placement (z = 0)

**DBL Heuristic Tests**:
- Test with empty vehicle (should place at origin)
- Test with one package placed (should use generated contact points)
- Test with multiple packages (should select minimum distance)
- Test tie-breaking with equal distances

**LIFO Sorting Tests**:
- Test with packages from different stops (verify reverse order)
- Test with packages from same stop (verify weight order)
- Test with mixed stops and weights

**Weight Constraint Tests**:
- Test valid stacking (light on heavy)
- Test invalid stacking (heavy on light beyond 1.5x)
- Test bridge stacking (multiple supports)
- Test floor placement (no weight constraint)

**Contact Point Generation Tests**:
- Test initial state (origin only)
- Test after placing one package (three new points)
- Test boundary filtering (points outside vehicle)
- Test occupancy filtering (points inside packages)

**Error Handling Tests**:
- Test oversized package (dimension exceeds vehicle)
- Test package too large by volume
- Test all contact points invalid (stability failure)
- Test failure reason reporting

### Integration Testing

**End-to-End Packing Workflow**:
1. Create package set with multiple stops
2. Configure vehicle dimensions
3. Run packing algorithm
4. Verify LIFO ordering preserved
5. Verify all placed packages satisfy constraints
6. Verify failed packages have reasons
7. Verify utilization calculation

**Compatibility Testing**:
- Test with existing CSV parser output
- Test with existing visualization system
- Test with existing manifest generator
- Verify coordinate system consistency

**Performance Testing**:
- Test with 10 packages (should complete quickly)
- Test with 50 packages (should complete in < 1 second)
- Test with 100 packages (should complete in < 5 seconds)
- Measure contact point generation overhead

## Implementation Notes

### Performance Considerations

**Contact Point Management**:
- Current approach generates O(3N) contact points for N packages
- Filtering and sorting adds O(N log N) overhead
- Acceptable for typical package counts (< 100 per route)
- Future optimization: spatial indexing (octree) for large package counts

**Support Calculation**:
- Rectangle intersection is O(1) per pair
- Checking all supporting packages is O(N) per placement
- Total complexity: O(N²) for N packages
- Acceptable for typical use cases

**Placement Validation**:
- Each validation checks O(N) existing packages
- Trying O(N) contact points per package
- Total complexity: O(N³) worst case
- Mitigated by early termination (first valid position)

### Algorithm Optimizations

**Early Termination**:
- Stop trying contact points once valid placement found
- Skip contact points that are obviously invalid (outside boundaries)
- Cache support calculations for repeated queries

**Contact Point Pruning**:
- Remove dominated contact points (strictly worse in all dimensions)
- Merge duplicate contact points (within tolerance)
- Limit maximum contact points per package (e.g., top 10 by distance)

**Spatial Indexing** (future enhancement):
- Use octree or grid to accelerate overlap detection
- Reduce overlap checks from O(N) to O(log N)
- Significant benefit for large package counts (> 200)

### Compatibility with Existing System

**Integration Points**:
- **Input**: Receives Package objects from CSV parser (existing)
- **Output**: Returns PlacedPackage objects for visualization (existing format)
- **Configuration**: Uses VehicleType dimensions from fleet composer (existing)
- **Coordinate System**: Maintains X=0 (back) to X=max (door) convention (existing)

**Migration Strategy**:
- Implement DBLPackingEngine as new class
- Keep existing LIFOPackingEngine for comparison
- Add configuration flag to switch between engines
- Run both engines in parallel during testing phase
- Deprecate old engine once DBL is validated

**Backward Compatibility**:
- Maintain same API signatures
- Return same data structures
- Support same visualization format
- Preserve LIFO ordering guarantee

### Dependencies

**Existing Dependencies**:
- `dataclasses`: For data structures
- `typing`: For type hints
- `math`: For Euclidean distance calculation

**New Dependencies**:
- None (uses only Python standard library)

**Testing Dependencies**:
- `hypothesis`: Property-based testing framework
- `pytest`: Unit testing framework
- `pytest-cov`: Code coverage reporting

### Configuration Options

**Packing Engine Configuration**:
```python
class PackingConfig:
    support_threshold: float = 0.80  # 80% support requirement
    weight_ratio_max: float = 1.5    # Maximum weight ratio for stacking
    tolerance: float = 0.001         # Floating-point comparison tolerance
    max_contact_points: int = 100    # Limit contact points for performance
    enable_rotation: bool = False    # Future: allow package rotation
```

**Usage Example**:
```python
# Configure packing engine
config = PackingConfig(
    support_threshold=0.75,  # Relax to 75% for testing
    weight_ratio_max=2.0     # Allow 2x weight ratio
)

engine = DBLPackingEngine(
    vehicle_length_m=3.0,
    vehicle_width_m=2.0,
    vehicle_height_m=2.0,
    config=config
)

# Pack route
result = engine.pack_route(packages)
```

### Future Enhancements

**Package Rotation**:
- Allow rotation of packages (swap length/width)
- Respect `this_side_up` constraint
- Try all valid orientations at each contact point
- Select orientation that maximizes utilization

**Multi-Vehicle Packing**:
- Extend to pack across multiple vehicles
- Balance load across vehicles
- Minimize number of vehicles used
- Respect vehicle capacity constraints

**Advanced Heuristics**:
- Implement genetic algorithm for global optimization
- Add simulated annealing for better local search
- Consider load balancing (weight distribution)
- Optimize for center of gravity

**Visualization Enhancements**:
- Show contact points in 3D view
- Animate packing sequence
- Highlight constraint violations
- Display support areas visually

**Performance Profiling**:
- Add timing instrumentation
- Identify bottlenecks
- Optimize hot paths
- Benchmark against existing engine
