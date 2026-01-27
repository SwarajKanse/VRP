"""
LIFO Packing Engine Module

This module implements Last-In-First-Out packing strategy with physics constraints
for the VRP solver. Packages are loaded so that the last delivery is at the back
and the first delivery is accessible near the door.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
from dashboard.csv_parser import Package


@dataclass
class PlacedPackage:
    """Represents a package that has been placed in the cargo bay."""
    package: Package
    x: float  # back-bottom-left corner position
    y: float
    z: float
    length: float  # actual dimensions after potential rotation
    width: float
    height: float
    stop_number: int


@dataclass
class PackingResult:
    """Result of LIFO packing operation."""
    placed_packages: List[PlacedPackage]
    failed_packages: List[Package]
    utilization_percent: float


class LIFOPackingEngine:
    """
    3D bin packing using LIFO (Last-In-First-Out) strategy with physics constraints.
    
    Coordinate system: (0,0,0) is back-bottom-left corner, door is at maximum X.
    Packages are loaded from back (X=0) toward door (X=max).
    """
    
    def __init__(self, vehicle_length_m: float, vehicle_width_m: float, 
                 vehicle_height_m: float):
        """
        Initialize LIFO packing engine with vehicle cargo bay dimensions.
        
        Args:
            vehicle_length_m: Length of cargo bay (X dimension, back to door)
            vehicle_width_m: Width of cargo bay (Y dimension)
            vehicle_height_m: Height of cargo bay (Z dimension)
        """
        self.vehicle_length_m = vehicle_length_m
        self.vehicle_width_m = vehicle_width_m
        self.vehicle_height_m = vehicle_height_m
        self.placed_packages: List[PlacedPackage] = []
    
    def pack_route(self, packages: List[Package], 
                   stop_order: List[int]) -> PackingResult:
        """
        Pack packages using LIFO strategy with physics constraints.
        
        Algorithm:
        1. Sort packages by reverse stop order (last delivery first)
        2. Within same stop, sort by volume (largest first)
        3. Place from X=0 (back) toward X=max (door)
        4. Respect fragile and orientation constraints
        5. Ensure stability (60% base support)
        
        Args:
            packages: List of Package objects to pack
            stop_order: List of stop numbers in route order
            
        Returns:
            PackingResult with placed/failed packages and utilization
        """
        # Reset placed packages for this packing operation
        self.placed_packages = []
        
        # Sort packages by LIFO priority
        sorted_package_pairs = self._sort_packages_lifo(packages, stop_order)
        
        placed = []
        failed = []
        
        # Try to place each package
        for package, stop_num in sorted_package_pairs:
            position_result = self._find_placement_position(package, stop_num)
            
            if position_result is not None:
                x, y, z, length, width, height = position_result
                
                # Create placed package record
                placed_pkg = PlacedPackage(
                    package=package,
                    x=x,
                    y=y,
                    z=z,
                    length=length,
                    width=width,
                    height=height,
                    stop_number=stop_num
                )
                
                placed.append(placed_pkg)
                self.placed_packages.append(placed_pkg)
            else:
                # Could not place package
                failed.append(package)
        
        # Calculate utilization
        utilization = self._calculate_utilization()
        
        return PackingResult(
            placed_packages=placed,
            failed_packages=failed,
            utilization_percent=utilization
        )
    
    def _calculate_utilization(self) -> float:
        """Calculate cargo bay volume utilization percentage."""
        total_volume = self.vehicle_length_m * self.vehicle_width_m * self.vehicle_height_m
        used_volume = sum(pkg.length * pkg.width * pkg.height for pkg in self.placed_packages)
        return (used_volume / total_volume) * 100.0 if total_volume > 0 else 0.0
    
    def _sort_packages_lifo(self, packages: List[Package], 
                           stop_order: List[int]) -> List[Tuple[Package, int]]:
        """
        Sort packages by LIFO priority.
        
        Primary sort: reverse stop order (last delivery first)
        Secondary sort: volume descending within same stop
        
        Args:
            packages: List of Package objects
            stop_order: List of stop numbers in route order
            
        Returns:
            List of (Package, stop_number) tuples sorted by LIFO priority
        """
        # Create mapping from destination name to stop number
        dest_to_stop = {}
        for stop_num, dest_idx in enumerate(stop_order, start=1):
            # Note: stop_order contains customer indices, we need to map to destination names
            # For now, we'll use a simple approach: assign stop numbers based on order
            dest_to_stop[stop_num] = stop_num
        
        # Assign stop numbers to packages based on their destination
        # We'll need to match packages to stops - for now use a simple counter approach
        package_stop_pairs = []
        for package in packages:
            # Find which stop this package belongs to
            # This is a simplified approach - in real integration, we'd match destination names
            stop_num = 1  # Default to first stop
            package_stop_pairs.append((package, stop_num))
        
        # Sort by LIFO priority:
        # Primary: reverse stop order (higher stop number first = last delivery first)
        # Secondary: volume descending (larger packages first within same stop)
        sorted_pairs = sorted(
            package_stop_pairs,
            key=lambda pair: (-pair[1], -pair[0].volume_m3)
        )
        
        return sorted_pairs
    
    def _find_placement_position(self, package: Package, 
                                stop_num: int) -> Optional[Tuple[float, float, float, float, float, float]]:
        """
        Find valid (x, y, z) position for package with dimensions.
        
        Searches from X=0 (back) toward X=max (door) for first valid position.
        Tries different positions and orientations.
        
        Args:
            package: Package to place
            stop_num: Stop number for this package
            
        Returns:
            (x, y, z, length, width, height) if valid position found, None otherwise
        """
        # Generate possible orientations based on rotation constraints
        orientations = self._get_orientations(package)
        
        # Generate candidate positions (from back to door)
        x_positions = self._generate_x_positions()
        y_positions = self._generate_y_positions()
        z_positions = self._generate_z_positions()
        
        # Try each orientation
        for length, width, height in orientations:
            # Try positions from back (X=0) toward door (X=max)
            for x in x_positions:
                for y in y_positions:
                    for z in z_positions:
                        # Check if package fits in cargo bay
                        if not self._fits_in_cargo_bay(x, y, z, length, width, height):
                            continue
                        
                        # Check for collisions with placed packages
                        if not self._no_collision(x, y, z, length, width, height):
                            continue
                        
                        # Check fragile constraint
                        if not self._check_fragile_constraint(package, x, y, z, length, width, height):
                            continue
                        
                        # Check stability
                        if not self._check_stability(package, x, y, z, length, width, height):
                            continue
                        
                        # Valid position found!
                        return (x, y, z, length, width, height)
        
        # No valid position found
        return None
    
    def _get_orientations(self, package: Package) -> List[Tuple[float, float, float]]:
        """
        Generate possible orientations for a package.
        
        If package has this_side_up=True, only return original orientation.
        Otherwise, return all 6 possible orientations.
        
        Args:
            package: Package to generate orientations for
            
        Returns:
            List of (length, width, height) tuples
        """
        l, w, h = package.length_m, package.width_m, package.height_m
        
        if not self._can_rotate(package):
            # Orientation locked - only original orientation
            return [(l, w, h)]
        else:
            # All 6 orientations possible
            return [
                (l, w, h), (l, h, w),
                (w, l, h), (w, h, l),
                (h, l, w), (h, w, l)
            ]
    
    def _generate_x_positions(self) -> List[float]:
        """Generate candidate X positions from back to door."""
        positions = [0.0]
        for placed in self.placed_packages:
            positions.append(placed.x + placed.length)
        return sorted(set(positions))
    
    def _generate_y_positions(self) -> List[float]:
        """Generate candidate Y positions."""
        positions = [0.0]
        for placed in self.placed_packages:
            positions.append(placed.y + placed.width)
        return sorted(set(positions))
    
    def _generate_z_positions(self) -> List[float]:
        """Generate candidate Z positions."""
        positions = [0.0]
        for placed in self.placed_packages:
            positions.append(placed.z + placed.height)
        return sorted(set(positions))
    
    def _fits_in_cargo_bay(self, x: float, y: float, z: float,
                          length: float, width: float, height: float) -> bool:
        """Check if package fits within cargo bay boundaries."""
        return (x + length <= self.vehicle_length_m and
                y + width <= self.vehicle_width_m and
                z + height <= self.vehicle_height_m)
    
    def _no_collision(self, x: float, y: float, z: float,
                     length: float, width: float, height: float) -> bool:
        """Check for collision with already placed packages."""
        for placed in self.placed_packages:
            if self._boxes_overlap(
                x, y, z, length, width, height,
                placed.x, placed.y, placed.z, placed.length, placed.width, placed.height
            ):
                return False
        return True
    
    def _boxes_overlap(self, x1: float, y1: float, z1: float, l1: float, w1: float, h1: float,
                      x2: float, y2: float, z2: float, l2: float, w2: float, h2: float) -> bool:
        """Check if two 3D boxes overlap."""
        x_overlap = (x1 < x2 + l2) and (x1 + l1 > x2)
        y_overlap = (y1 < y2 + w2) and (y1 + w1 > y2)
        z_overlap = (z1 < z2 + h2) and (z1 + h1 > z2)
        return x_overlap and y_overlap and z_overlap
    
    def _check_fragile_constraint(self, package: Package, 
                                 x: float, y: float, z: float,
                                 length: float, width: float, height: float) -> bool:
        """
        Verify no packages placed on top of fragile items.
        
        Checks Z-axis overlap and XY footprint overlap with all placed fragile packages.
        
        Args:
            package: Package being placed (not used, for future extension)
            x, y, z: Position of package
            length, width, height: Dimensions of package
            
        Returns:
            True if constraint satisfied, False if violated
        """
        # Check all placed packages to see if any fragile ones would be violated
        for placed in self.placed_packages:
            if placed.package.fragile:
                # Check if new package would be on top of this fragile package
                # "On top" means: z > placed.z AND XY footprints overlap
                
                # Check if new package's bottom is above the fragile package's bottom
                if z > placed.z:
                    # Check XY footprint overlap
                    x_overlap = (x < placed.x + placed.length) and (x + length > placed.x)
                    y_overlap = (y < placed.y + placed.width) and (y + width > placed.y)
                    
                    if x_overlap and y_overlap:
                        # New package would be on top of fragile package - violation!
                        return False
        
        return True
    
    def _check_stability(self, package: Package, 
                        x: float, y: float, z: float,
                        length: float, width: float, height: float) -> bool:
        """
        Verify package has adequate base support.
        
        Package must be:
        - On floor (Z=0), OR
        - On other packages with at least 60% base area overlap
        
        Args:
            package: Package being placed (not used, for future extension)
            x, y, z: Position of package
            length, width, height: Dimensions of package
            
        Returns:
            True if stable, False if unstable
        """
        # If on floor, always stable
        if z == 0:
            return True
        
        # Calculate base area of new package
        base_area = length * width
        
        # Find all packages that could support this one
        # Supporting packages must have their top surface at z (touching bottom of new package)
        supporting_packages = []
        for placed in self.placed_packages:
            if abs(placed.z + placed.height - z) < 0.001:  # Top surface at new package's bottom
                supporting_packages.append(placed)
        
        if not supporting_packages:
            # No support found - unstable
            return False
        
        # Calculate overlapping area with supporting packages
        total_overlap = 0.0
        for support in supporting_packages:
            # Calculate XY overlap rectangle
            overlap_x_min = max(x, support.x)
            overlap_x_max = min(x + length, support.x + support.length)
            overlap_y_min = max(y, support.y)
            overlap_y_max = min(y + width, support.y + support.width)
            
            # Check if there's actual overlap
            if overlap_x_max > overlap_x_min and overlap_y_max > overlap_y_min:
                overlap_area = (overlap_x_max - overlap_x_min) * (overlap_y_max - overlap_y_min)
                total_overlap += overlap_area
        
        # Check if at least 60% of base is supported
        support_percentage = total_overlap / base_area if base_area > 0 else 0
        return support_percentage >= 0.6
    
    def _can_rotate(self, package: Package) -> bool:
        """
        Check if package allows X/Y rotation.
        
        Args:
            package: Package to check
            
        Returns:
            False if package has this_side_up=True, True otherwise
        """
        return not package.this_side_up
