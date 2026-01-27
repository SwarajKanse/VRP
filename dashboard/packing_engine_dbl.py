"""
DBL (Deepest-Bottom-Left) Packing Engine Module

This module implements a gravity-driven packing algorithm with strict physics constraints.
The DBL approach places packages as close as possible to the back-bottom-left corner (0,0,0)
while enforcing 80% support rules and weight constraints.
"""

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
        """Calculate package volume in cubic meters"""
        return self.length_m * self.width_m * self.height_m
    
    @property
    def base_area_m2(self) -> float:
        """Calculate base area in square meters"""
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
        """Maximum X coordinate (right edge)"""
        return self.x + self.length
    
    @property
    def y_max(self) -> float:
        """Maximum Y coordinate (front edge)"""
        return self.y + self.width
    
    @property
    def z_max(self) -> float:
        """Maximum Z coordinate (top surface)"""
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


class DBLPackingEngine:
    """Deepest-Bottom-Left packing engine with gravity constraints"""
    
    def __init__(self, vehicle_length_m: float, vehicle_width_m: float, 
                 vehicle_height_m: float, max_contact_points: Optional[int] = None):
        """
        Initialize DBL packing engine with vehicle cargo bay dimensions.
        
        Args:
            vehicle_length_m: Length of cargo bay (X dimension, back to door)
            vehicle_width_m: Width of cargo bay (Y dimension)
            vehicle_height_m: Height of cargo bay (Z dimension)
            max_contact_points: Optional limit on number of contact points to maintain.
                              If specified, only the top N contact points (by distance)
                              are kept after each placement. This can improve performance
                              for large package sets at the cost of potentially reduced
                              packing quality. If None (default), no limit is applied.
            
        Raises:
            ValueError: If any vehicle dimension is not positive or max_contact_points is invalid
        """
        # Validate vehicle dimensions
        if vehicle_length_m <= 0:
            raise ValueError(f"Vehicle length must be positive, got {vehicle_length_m}")
        if vehicle_width_m <= 0:
            raise ValueError(f"Vehicle width must be positive, got {vehicle_width_m}")
        if vehicle_height_m <= 0:
            raise ValueError(f"Vehicle height must be positive, got {vehicle_height_m}")
        
        # Validate max_contact_points if specified
        if max_contact_points is not None and max_contact_points < 1:
            raise ValueError(f"max_contact_points must be at least 1, got {max_contact_points}")
        
        self.vehicle_length_m = vehicle_length_m  # X dimension (back to door)
        self.vehicle_width_m = vehicle_width_m    # Y dimension
        self.vehicle_height_m = vehicle_height_m  # Z dimension
        self.max_contact_points = max_contact_points  # Optional performance limit
        self.placed_packages: List[PlacedPackage] = []
        self.contact_points: List[ContactPoint] = []

    def _euclidean_distance(self, x: float, y: float, z: float) -> float:
        """
        Calculate Euclidean distance from a 3D point to the origin (0,0,0).
        
        Args:
            x: X coordinate
            y: Y coordinate
            z: Z coordinate
            
        Returns:
            Distance from origin calculated as √(x² + y² + z²)
        """
        return math.sqrt(x**2 + y**2 + z**2)

    def _update_contact_points(self, package: Package, x: float, y: float, z: float):
        """
        Generate new contact points from a placed package and update the contact point list.
        
        This method:
        1. Removes the contact point that was just used for placement
        2. Generates three new contact points from the placed package:
           - Right edge: (x + length, y, z)
           - Front edge: (x, y + width, z)
           - Top corner: (x, y, z + height)
        3. Filters out points outside vehicle boundaries
        4. Filters out points occupied by existing packages
        5. If max_contact_points is set, keeps only the top N points by distance
        
        Args:
            package: The package that was just placed
            x: X coordinate where package was placed
            y: Y coordinate where package was placed
            z: Z coordinate where package was placed
        """
        # Remove the occupied contact point (within tolerance)
        self.contact_points = [cp for cp in self.contact_points 
                              if not (abs(cp.x - x) < 0.001 and 
                                     abs(cp.y - y) < 0.001 and 
                                     abs(cp.z - z) < 0.001)]
        
        # Generate three new contact points from the placed package
        new_points = [
            # Right edge
            ContactPoint(
                x + package.length_m, 
                y, 
                z, 
                self._euclidean_distance(x + package.length_m, y, z)
            ),
            # Front edge
            ContactPoint(
                x, 
                y + package.width_m, 
                z,
                self._euclidean_distance(x, y + package.width_m, z)
            ),
            # Top corner
            ContactPoint(
                x, 
                y, 
                z + package.height_m,
                self._euclidean_distance(x, y, z + package.height_m)
            )
        ]
        
        # Filter out points outside boundaries or occupied by existing packages
        for point in new_points:
            if self._is_valid_contact_point(point):
                self.contact_points.append(point)
        
        # Apply contact point limit if configured
        if self.max_contact_points is not None and len(self.contact_points) > self.max_contact_points:
            # Sort by distance (DBL heuristic) and keep only top N
            self.contact_points.sort()
            self.contact_points = self.contact_points[:self.max_contact_points]
    
    def _is_valid_contact_point(self, cp: ContactPoint) -> bool:
        """
        Check if a contact point is valid (within boundaries and not occupied).
        
        Args:
            cp: Contact point to validate
            
        Returns:
            True if the contact point is valid, False otherwise
        """
        # Check boundaries - point must be strictly within vehicle dimensions
        if (cp.x >= self.vehicle_length_m or 
            cp.y >= self.vehicle_width_m or 
            cp.z >= self.vehicle_height_m):
            return False
        
        # Check if occupied by existing package
        # A contact point is occupied if it lies inside any placed package's volume
        for placed in self.placed_packages:
            if (placed.x <= cp.x < placed.x_max and
                placed.y <= cp.y < placed.y_max and
                placed.z <= cp.z < placed.z_max):
                return False
        
        return True

    def _check_boundaries(self, package: Package, x: float, y: float, z: float) -> bool:
        """
        Check if a package fits within vehicle boundaries at the given position.
        
        Validates that the package's dimensions do not exceed the vehicle's cargo space
        when placed at position (x, y, z).
        
        Args:
            package: Package to check
            x: X coordinate of placement position (back-bottom-left corner)
            y: Y coordinate of placement position
            z: Z coordinate of placement position
            
        Returns:
            True if package fits within boundaries, False otherwise
        """
        return (x + package.length_m <= self.vehicle_length_m and
                y + package.width_m <= self.vehicle_width_m and
                z + package.height_m <= self.vehicle_height_m)

    def _packages_overlap_3d(self, p1: PlacedPackage, p2: PlacedPackage) -> bool:
        """
        Check if two packages overlap in 3D space.
        
        Two packages overlap if their volumes intersect in all three dimensions (X, Y, Z).
        Uses axis-aligned bounding box (AABB) intersection test.
        
        Args:
            p1: First placed package
            p2: Second placed package
            
        Returns:
            True if packages overlap, False otherwise
        """
        x_overlap = not (p1.x_max <= p2.x or p2.x_max <= p1.x)
        y_overlap = not (p1.y_max <= p2.y or p2.y_max <= p1.y)
        z_overlap = not (p1.z_max <= p2.z or p2.z_max <= p1.z)
        return x_overlap and y_overlap and z_overlap

    def _check_overlap(self, package: Package, x: float, y: float, z: float) -> bool:
        """
        Check if a package would overlap with any already-placed package.
        
        Creates a test PlacedPackage at the proposed position and checks for
        3D intersection with all existing placed packages.
        
        Args:
            package: Package to check
            x: X coordinate of proposed placement position
            y: Y coordinate of proposed placement position
            z: Z coordinate of proposed placement position
            
        Returns:
            True if package overlaps with any placed package, False otherwise
        """
        test_package = PlacedPackage(
            package, x, y, z, 
            package.length_m, package.width_m, package.height_m
        )
        
        for placed in self.placed_packages:
            if self._packages_overlap_3d(test_package, placed):
                return True
        
        return False

    def _check_support(self, package: Package, x: float, y: float, z: float) -> bool:
        """
        Check if a package has at least 80% of its base area supported.
        
        This method enforces the gravity constraint by ensuring packages don't "float".
        A package must have at least 80% of its bottom surface area supported by
        packages directly below it (packages whose top surface touches this package's bottom).
        
        Floor placement (z = 0) is exempt from this check.
        
        Bridge support is allowed: a package can sit across multiple packages with gaps
        between them, as long as the total support area is >= 80%.
        
        Args:
            package: Package to check
            x: X coordinate of proposed placement position
            y: Y coordinate of proposed placement position
            z: Z coordinate of proposed placement position
            
        Returns:
            True if package has sufficient support (or is on floor), False otherwise
        """
        # Floor placement exemption - packages on the floor don't need support
        if z == 0:
            return True
        
        # Create test package to calculate support areas
        test_package = PlacedPackage(
            package, x, y, z,
            package.length_m, package.width_m, package.height_m
        )
        
        # Calculate total support area from all packages directly below
        total_support_area = 0.0
        for placed in self.placed_packages:
            # Check if this package is directly below (its top surface touches our bottom)
            if placed.z_max == z:
                support_area = test_package.get_support_area(placed)
                total_support_area += support_area
        
        # Calculate required support (80% of base area)
        required_support = package.base_area_m2 * 0.80
        
        # Return True if we have sufficient support
        return total_support_area >= required_support

    def _check_weight_constraint(self, package: Package, x: float, y: float, z: float) -> bool:
        """
        Check if weight constraint is satisfied for all supporting packages.
        
        This method enforces the stackability rule: a package can only be placed on top
        of another package if its weight is at most 1.5 times the weight of the supporting
        package. This prevents heavy packages from crushing lighter ones.
        
        Floor placement (z = 0) is exempt from this check.
        
        For bridge support (package sits on multiple packages), the weight constraint
        must be satisfied for ALL supporting packages.
        
        Args:
            package: Package to check
            x: X coordinate of proposed placement position
            y: Y coordinate of proposed placement position
            z: Z coordinate of proposed placement position
            
        Returns:
            True if weight constraint is satisfied for all supports (or on floor), False otherwise
        """
        # Floor placement exemption - no weight constraint on the floor
        if z == 0:
            return True
        
        # Create test package to check XY overlap with supporting packages
        test_package = PlacedPackage(
            package, x, y, z,
            package.length_m, package.width_m, package.height_m
        )
        
        # Find all packages that would support this package
        # A package supports if: its top surface touches our bottom AND XY footprints overlap
        for placed in self.placed_packages:
            if placed.z_max == z and test_package.overlaps_xy(placed):
                # Check weight ratio: package.weight <= placed.weight * 1.5
                if package.weight_kg > placed.package.weight_kg * 1.5:
                    return False
        
        return True

    def _can_place_at(self, package: Package, x: float, y: float, z: float) -> bool:
        """
        Validate all placement constraints for a package at a given position.
        
        This method integrates all constraint checks in the proper sequence:
        1. Boundary check - package must fit within vehicle dimensions
        2. Overlap check - package must not intersect with existing packages
        3. Support check - package must have 80% support (if not on floor)
        4. Weight check - package must satisfy weight ratio constraint (if not on floor)
        
        The checks are performed in order of computational efficiency, with early
        exit on first failure.
        
        Args:
            package: Package to validate
            x: X coordinate of proposed placement position
            y: Y coordinate of proposed placement position
            z: Z coordinate of proposed placement position
            
        Returns:
            True if all constraints pass, False if any constraint fails
        """
        # 1. Boundary check - fast, check first
        if not self._check_boundaries(package, x, y, z):
            return False
        
        # 2. Overlap check - relatively fast
        if self._check_overlap(package, x, y, z):
            return False
        
        # 3. Support check - more expensive (area calculations)
        if z > 0 and not self._check_support(package, x, y, z):
            return False
        
        # 4. Weight check - check last
        if not self._check_weight_constraint(package, x, y, z):
            return False
        
        return True

    def _sort_packages_lifo(self, packages: List[Package]) -> List[Package]:
        """
        Sort packages by LIFO (Last-In-First-Out) priority for delivery operations.
        
        This sorting ensures that packages for later stops are loaded first (and thus
        accessible first during unloading). Within each stop, heavier packages are
        prioritized to enable bottom-heavy stacking.
        
        Sorting criteria:
        1. Primary: Reverse stop order (higher stop number first)
           - Stop 5 packages before Stop 4, Stop 4 before Stop 3, etc.
        2. Secondary: Weight descending (heavier first within same stop)
           - Enables heavier packages to be placed at the bottom
        
        Args:
            packages: List of packages to sort
            
        Returns:
            Sorted list of packages in LIFO order
        """
        return sorted(packages, key=lambda p: (-p.stop_number, -p.weight_kg))

    def _validate_package(self, package: Package) -> None:
        """
        Validate package data for correctness.
        
        Ensures that package dimensions, weight, and stop number are valid.
        
        Args:
            package: Package to validate
            
        Raises:
            ValueError: If any package attribute is invalid
        """
        # Validate dimensions are positive
        if package.length_m <= 0:
            raise ValueError(
                f"Package {package.order_id}: length must be positive, got {package.length_m}"
            )
        if package.width_m <= 0:
            raise ValueError(
                f"Package {package.order_id}: width must be positive, got {package.width_m}"
            )
        if package.height_m <= 0:
            raise ValueError(
                f"Package {package.order_id}: height must be positive, got {package.height_m}"
            )
        
        # Validate weight is positive
        if package.weight_kg <= 0:
            raise ValueError(
                f"Package {package.order_id}: weight must be positive, got {package.weight_kg}"
            )
        
        # Validate stop number is positive
        if package.stop_number < 1:
            raise ValueError(
                f"Package {package.order_id}: stop number must be at least 1, got {package.stop_number}"
            )

    def _try_place_package(self, package: Package) -> bool:
        """
        Attempt to place a package at the best available contact point.
        
        This method implements the core DBL (Deepest-Bottom-Left) placement logic:
        1. Sort contact points by DBL heuristic (distance, then Z, then X, then Y)
        2. Try each contact point in order
        3. For each contact point, validate all placement constraints
        4. Place at first valid position found
        5. Update contact points after successful placement
        
        Args:
            package: Package to place
            
        Returns:
            True if package was successfully placed, False if no valid position found
        """
        # Sort contact points by DBL heuristic (ContactPoint.__lt__ handles this)
        sorted_points = sorted(self.contact_points)
        
        # Try each contact point until we find a valid placement
        for cp in sorted_points:
            if self._can_place_at(package, cp.x, cp.y, cp.z):
                # Valid placement found - place the package
                self._place_package_at(package, cp.x, cp.y, cp.z)
                # Update contact points with new candidates from this placement
                self._update_contact_points(package, cp.x, cp.y, cp.z)
                return True
        
        # No valid contact point found
        return False

    def _place_package_at(self, package: Package, x: float, y: float, z: float):
        """
        Add a package to the placed packages list at the specified position.
        
        This method creates a PlacedPackage object with the package's final position
        and dimensions, then adds it to the internal list of placed packages.
        
        Args:
            package: Package to place
            x: X coordinate of placement position (back-bottom-left corner)
            y: Y coordinate of placement position
            z: Z coordinate of placement position
        """
        placed = PlacedPackage(
            package, x, y, z,
            package.length_m, package.width_m, package.height_m
        )
        self.placed_packages.append(placed)

    def _get_failure_reason(self, package: Package) -> str:
        """
        Determine why a package couldn't be placed.
        
        This method diagnoses placement failures by checking various conditions:
        - Package too large for vehicle (volume or dimension constraints)
        - Stability or weight constraints preventing placement
        
        Args:
            package: Package that failed to place
            
        Returns:
            Descriptive error message explaining why placement failed
        """
        # Check if package volume exceeds vehicle volume
        vehicle_volume = (self.vehicle_length_m * 
                         self.vehicle_width_m * 
                         self.vehicle_height_m)
        if package.volume_m3 > vehicle_volume:
            return "Package too large for vehicle"
        
        # Check if any dimension exceeds vehicle dimensions
        if (package.length_m > self.vehicle_length_m or
            package.width_m > self.vehicle_width_m or
            package.height_m > self.vehicle_height_m):
            return "Package dimension exceeds vehicle dimension"
        
        # Otherwise, likely stability or weight constraint failure
        return "Failed stability or weight constraints"

    def _calculate_utilization(self) -> float:
        """
        Calculate volume utilization percentage.
        
        Computes the percentage of vehicle cargo space occupied by placed packages.
        
        Returns:
            Utilization percentage (0-100)
        """
        vehicle_volume = (self.vehicle_length_m * 
                         self.vehicle_width_m * 
                         self.vehicle_height_m)
        
        if vehicle_volume == 0:
            return 0.0
        
        used_volume = sum(p.package.volume_m3 for p in self.placed_packages)
        return (used_volume / vehicle_volume) * 100.0

    def pack_route(self, packages: List[Package]) -> PackingResult:
        """
        Pack packages using DBL algorithm with LIFO sorting.
        
        This is the main entry point for the packing engine. It implements the complete
        DBL packing workflow:
        
        1. Validate all package data
        2. Sort packages by LIFO priority (reverse stop order, then weight)
        3. Initialize contact points with origin (0,0,0)
        4. For each package in sorted order:
           a. Try to place at best available contact point
           b. If successful, update contact points
           c. If failed, collect failure reason
        5. Calculate utilization and total weight
        6. Return comprehensive packing result
        
        Args:
            packages: List of packages to pack
            
        Returns:
            PackingResult containing:
            - placed_packages: Successfully placed packages with positions
            - failed_packages: Packages that couldn't be placed with reasons
            - utilization_percent: Cargo space utilization (0-100)
            - total_weight_kg: Total weight of placed packages
            
        Raises:
            ValueError: If any package has invalid data
        """
        # Validate all packages before processing
        for package in packages:
            self._validate_package(package)
        
        # Sort packages using LIFO strategy (reverse stop order, then weight)
        sorted_packages = self._sort_packages_lifo(packages)
        
        # Initialize with origin contact point
        self.contact_points = [ContactPoint(0, 0, 0, 0)]
        self.placed_packages = []
        failed_packages = []
        
        # Try to place each package in sorted order
        for package in sorted_packages:
            placed = self._try_place_package(package)
            if not placed:
                # Package couldn't be placed - diagnose why
                reason = self._get_failure_reason(package)
                failed_packages.append((package, reason))
        
        # Calculate final metrics
        utilization = self._calculate_utilization()
        total_weight = sum(p.package.weight_kg for p in self.placed_packages)
        
        return PackingResult(
            placed_packages=self.placed_packages,
            failed_packages=failed_packages,
            utilization_percent=utilization,
            total_weight_kg=total_weight
        )
