"""
3D Load Optimization - Packing Engine Module

This module provides core data models and algorithms for 3D bin packing validation
in the VRP solver. It converts abstract demand units into physical packages and
validates that they can physically fit inside vehicle cargo bays.
"""

import random
import hashlib
from typing import List, Tuple, Optional


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
        hash_val = int(hashlib.md5(str(customer_id).encode()).hexdigest()[:6], 16)
        r = (hash_val >> 16) & 0xFF
        g = (hash_val >> 8) & 0xFF
        b = hash_val & 0xFF
        return f"rgb({r},{g},{b})"


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
        """Initialize vehicle profile with cargo bay dimensions.
        
        Args:
            vehicle_type: Type of vehicle (e.g., "Truck", "Van", "Tempo")
            capacity: Weight capacity in kg
            cargo_length: Length of cargo bay in meters (optional, uses default if None)
            cargo_width: Width of cargo bay in meters (optional, uses default if None)
            cargo_height: Height of cargo bay in meters (optional, uses default if None)
            
        Raises:
            ValueError: If provided cargo dimensions are not positive numbers
        """
        self.vehicle_type = vehicle_type
        self.capacity = capacity  # Weight capacity (existing)
        
        # Task 9.1: Validate cargo dimensions are positive if provided - Requirement 1.3
        if cargo_length is not None:
            if not isinstance(cargo_length, (int, float)):
                raise ValueError(f"cargo_length must be a number, got {type(cargo_length).__name__}")
            if cargo_length <= 0:
                raise ValueError(f"cargo_length must be positive, got {cargo_length}")
        
        if cargo_width is not None:
            if not isinstance(cargo_width, (int, float)):
                raise ValueError(f"cargo_width must be a number, got {type(cargo_width).__name__}")
            if cargo_width <= 0:
                raise ValueError(f"cargo_width must be positive, got {cargo_width}")
        
        if cargo_height is not None:
            if not isinstance(cargo_height, (int, float)):
                raise ValueError(f"cargo_height must be a number, got {type(cargo_height).__name__}")
            if cargo_height <= 0:
                raise ValueError(f"cargo_height must be positive, got {cargo_height}")
        
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


class PackageGenerator:
    """Generates physical packages from demand units."""
    
    def __init__(
        self,
        min_dimension: float = 0.3,
        max_dimension: float = 0.8,
        random_seed: int = None
    ):
        """Initialize package generator with dimension constraints.
        
        Args:
            min_dimension: Minimum dimension for package sides (meters)
            max_dimension: Maximum dimension for package sides (meters)
            random_seed: Optional seed for deterministic generation
            
        Raises:
            ValueError: If dimension inputs are invalid (non-positive or min >= max)
        """
        # Task 9.1: Validate dimension inputs are positive numbers - Requirement 2.2
        if not isinstance(min_dimension, (int, float)):
            raise ValueError(f"min_dimension must be a number, got {type(min_dimension).__name__}")
        if not isinstance(max_dimension, (int, float)):
            raise ValueError(f"max_dimension must be a number, got {type(max_dimension).__name__}")
        
        if min_dimension <= 0:
            raise ValueError(f"min_dimension must be positive, got {min_dimension}")
        if max_dimension <= 0:
            raise ValueError(f"max_dimension must be positive, got {max_dimension}")
        
        # Task 9.1: Validate min dimension < max dimension - Requirement 2.2
        if min_dimension >= max_dimension:
            raise ValueError(
                f"min_dimension must be less than max_dimension, "
                f"got min={min_dimension}, max={max_dimension}"
            )
        
        self.min_dimension = min_dimension
        self.max_dimension = max_dimension
        self.random_seed = random_seed
        self._rng = random.Random(random_seed)
    
    def generate_packages(
        self,
        customer_demands: List[Tuple[int, int]]  # [(customer_id, demand), ...]
    ) -> List[Package]:
        """Generate packages from customer demands.
        
        Converts abstract demand units into physical Package objects with
        random dimensions within the configured range. Each demand unit
        corresponds to exactly one package.
        
        Args:
            customer_demands: List of (customer_id, demand_units) tuples
            
        Returns:
            List of Package objects with random dimensions
        """
        packages = []
        package_id = 0
        
        for customer_id, demand in customer_demands:
            for _ in range(demand):
                # Generate random dimensions within configured range
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


class FirstFitDecreasingPacker:
    """3D bin packing using First-Fit Decreasing heuristic."""
    
    def __init__(
        self,
        cargo_length: float,
        cargo_width: float,
        cargo_height: float
    ):
        """Initialize packer with cargo bay dimensions.
        
        Args:
            cargo_length: Length of cargo bay in meters
            cargo_width: Width of cargo bay in meters
            cargo_height: Height of cargo bay in meters
            
        Raises:
            ValueError: If cargo dimensions are not positive numbers
        """
        # Task 9.1: Validate cargo dimensions are positive - Requirement 1.3
        if not isinstance(cargo_length, (int, float)):
            raise ValueError(f"cargo_length must be a number, got {type(cargo_length).__name__}")
        if not isinstance(cargo_width, (int, float)):
            raise ValueError(f"cargo_width must be a number, got {type(cargo_width).__name__}")
        if not isinstance(cargo_height, (int, float)):
            raise ValueError(f"cargo_height must be a number, got {type(cargo_height).__name__}")
        
        if cargo_length <= 0:
            raise ValueError(f"cargo_length must be positive, got {cargo_length}")
        if cargo_width <= 0:
            raise ValueError(f"cargo_width must be positive, got {cargo_width}")
        if cargo_height <= 0:
            raise ValueError(f"cargo_height must be positive, got {cargo_height}")
        
        self.cargo_length = cargo_length
        self.cargo_width = cargo_width
        self.cargo_height = cargo_height
        self.placed_packages: List[Package] = []
    
    def pack(self, packages: List[Package]) -> PackingResult:
        """Pack packages into cargo bay using FFD algorithm.
        
        The First-Fit Decreasing algorithm:
        1. Sort packages by volume (largest first)
        2. For each package, try all 6 orientations
        3. Place at first available position
        4. Mark as overflow if no position found
        
        Args:
            packages: List of Package objects to pack
            
        Returns:
            PackingResult with placed and overflow packages
            
        Raises:
            ValueError: If packages is None
        """
        # Task 9.2: Handle empty package lists gracefully - Requirement 6.3
        if packages is None:
            raise ValueError("packages cannot be None")
        
        # Handle empty package list - return empty result
        if len(packages) == 0:
            return PackingResult(
                placed=[],
                overflow=[],
                utilization=0.0
            )
        
        # Sort by volume (largest first) - Requirement 3.1
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
        
        Tries all 6 orientations of the package and searches for valid placement
        at candidate positions generated from existing packages.
        
        Args:
            package: Package to place
            
        Returns:
            (x, y, z) coordinates if fit found, None otherwise
        """
        orientations = self._get_orientations(package)
        
        for length, width, height in orientations:
            # Try placing at grid positions generated from existing packages
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
        """Generate all 6 possible orientations of a package.
        
        Args:
            package: Package to generate orientations for
            
        Returns:
            List of (length, width, height) tuples for each orientation
        """
        l, w, h = package.length, package.width, package.height
        return [
            (l, w, h), (l, h, w),
            (w, l, h), (w, h, l),
            (h, l, w), (h, w, l)
        ]
    
    def _generate_x_positions(self) -> List[float]:
        """Generate candidate x positions based on placed packages.
        
        Candidate positions include:
        - Origin (0.0)
        - Right edge of each placed package
        
        Returns:
            Sorted list of unique x coordinates
        """
        positions = [0.0]
        for pkg in self.placed_packages:
            positions.append(pkg.x + pkg.length)
        return sorted(set(positions))
    
    def _generate_y_positions(self) -> List[float]:
        """Generate candidate y positions based on placed packages.
        
        Candidate positions include:
        - Origin (0.0)
        - Front edge of each placed package
        
        Returns:
            Sorted list of unique y coordinates
        """
        positions = [0.0]
        for pkg in self.placed_packages:
            positions.append(pkg.y + pkg.width)
        return sorted(set(positions))
    
    def _generate_z_positions(self) -> List[float]:
        """Generate candidate z positions based on placed packages.
        
        Candidate positions include:
        - Origin (0.0)
        - Top edge of each placed package
        
        Returns:
            Sorted list of unique z coordinates
        """
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
        1. Package fits within cargo bay boundaries (Requirement 3.5)
        2. No collision with already placed packages (Requirement 3.3)
        
        Args:
            x: X coordinate of package corner
            y: Y coordinate of package corner
            z: Z coordinate of package corner
            length: Package length
            width: Package width
            height: Package height
            
        Returns:
            True if package can be placed, False otherwise
        """
        # Check cargo bay boundaries - Requirement 3.5
        if x + length > self.cargo_length:
            return False
        if y + width > self.cargo_width:
            return False
        if z + height > self.cargo_height:
            return False
        
        # Check collision with placed packages - Requirement 3.3
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
        """Check if two 3D boxes overlap.
        
        Two boxes overlap if they overlap in all three dimensions.
        Uses the separating axis theorem: boxes don't overlap if they
        are separated along any axis.
        
        Args:
            x1, y1, z1: Position of first box
            l1, w1, h1: Dimensions of first box
            x2, y2, z2: Position of second box
            l2, w2, h2: Dimensions of second box
            
        Returns:
            True if boxes overlap, False otherwise
        """
        # Boxes overlap if they overlap in all three dimensions
        x_overlap = (x1 < x2 + l2) and (x1 + l1 > x2)
        y_overlap = (y1 < y2 + w2) and (y1 + w1 > y2)
        z_overlap = (z1 < z2 + h2) and (z1 + h1 > z2)
        
        return x_overlap and y_overlap and z_overlap
    
    def _calculate_utilization(self) -> float:
        """Calculate cargo bay volume utilization percentage.
        
        Returns:
            Utilization as percentage (0-100)
        """
        total_volume = self.cargo_length * self.cargo_width * self.cargo_height
        used_volume = sum(pkg.volume() for pkg in self.placed_packages)
        return (used_volume / total_volume) * 100.0 if total_volume > 0 else 0.0


try:
    import plotly.graph_objects as go
except ImportError:
    go = None


class CargoVisualizationRenderer:
    """Renders 3D cargo loading visualization using Plotly."""
    
    def render(
        self,
        vehicle_profile: VehicleProfile,
        packing_result: PackingResult,
        vehicle_id: str = "Vehicle"
    ) -> 'go.Figure':
        """Create 3D visualization of cargo loading.
        
        Generates an interactive 3D scene showing:
        - Wireframe cargo bay boundaries
        - Solid cubes for placed packages (colored by customer)
        - Overflow indicators for packages that couldn't fit
        
        Args:
            vehicle_profile: Vehicle with cargo bay dimensions
            packing_result: Result of packing operation
            vehicle_id: Identifier for display title
            
        Returns:
            Plotly Figure object with 3D scene
            
        Raises:
            ImportError: If plotly is not installed
        """
        if go is None:
            raise ImportError("plotly is required for visualization. Install with: pip install plotly")
        
        fig = go.Figure()
        
        # Add cargo bay wireframe - Requirement 4.3
        self._add_cargo_bay_wireframe(fig, vehicle_profile)
        
        # Add placed packages as solid cubes - Requirement 4.4
        for package in packing_result.placed:
            self._add_package_cube(fig, package)
        
        # Add overflow packages (if any) in separate area - Requirement 4.7
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
        fig: 'go.Figure',
        vehicle_profile: VehicleProfile
    ):
        """Add wireframe box representing cargo bay boundaries.
        
        Draws the 12 edges of the cargo bay as black lines to show
        the physical constraints of the loading space.
        
        Args:
            fig: Plotly Figure to add wireframe to
            vehicle_profile: Vehicle with cargo bay dimensions
        """
        l = vehicle_profile.cargo_length
        w = vehicle_profile.cargo_width
        h = vehicle_profile.cargo_height
        
        # Define 12 edges of the box
        edges = [
            # Bottom face (z=0)
            ([0, l], [0, 0], [0, 0]),  # Front edge
            ([l, l], [0, w], [0, 0]),  # Right edge
            ([l, 0], [w, w], [0, 0]),  # Back edge
            ([0, 0], [w, 0], [0, 0]),  # Left edge
            # Top face (z=h)
            ([0, l], [0, 0], [h, h]),  # Front edge
            ([l, l], [0, w], [h, h]),  # Right edge
            ([l, 0], [w, w], [h, h]),  # Back edge
            ([0, 0], [w, 0], [h, h]),  # Left edge
            # Vertical edges
            ([0, 0], [0, 0], [0, h]),  # Front-left
            ([l, l], [0, 0], [0, h]),  # Front-right
            ([l, l], [w, w], [0, h]),  # Back-right
            ([0, 0], [w, w], [0, h])   # Back-left
        ]
        
        for x, y, z in edges:
            fig.add_trace(go.Scatter3d(
                x=x, y=y, z=z,
                mode="lines",
                line=dict(color="black", width=2),
                showlegend=False,
                hoverinfo="skip"
            ))
    
    def _add_package_cube(self, fig: 'go.Figure', package: Package):
        """Add solid cube representing a package.
        
        Creates a 3D mesh cube with the package's color and dimensions.
        Includes hover information with package details.
        
        Args:
            fig: Plotly Figure to add package to
            package: Package with position and dimensions
        """
        x, y, z = package.x, package.y, package.z
        l, w, h = package.length, package.width, package.height
        
        # Define 8 vertices of the cube
        vertices = [
            [x, y, z],          # 0: Bottom-front-left
            [x+l, y, z],        # 1: Bottom-front-right
            [x+l, y+w, z],      # 2: Bottom-back-right
            [x, y+w, z],        # 3: Bottom-back-left
            [x, y, z+h],        # 4: Top-front-left
            [x+l, y, z+h],      # 5: Top-front-right
            [x+l, y+w, z+h],    # 6: Top-back-right
            [x, y+w, z+h]       # 7: Top-back-left
        ]
        
        # Define 12 triangles (2 per face) using vertex indices
        # Each face is split into 2 triangles
        i_indices = [0, 0, 4, 4, 0, 0, 1, 1, 2, 2, 3, 3]
        j_indices = [1, 3, 5, 7, 1, 3, 5, 2, 6, 3, 7, 0]
        k_indices = [2, 7, 6, 6, 5, 4, 6, 6, 7, 7, 4, 4]
        
        # Create mesh for solid cube - Requirement 4.4
        fig.add_trace(go.Mesh3d(
            x=[v[0] for v in vertices],
            y=[v[1] for v in vertices],
            z=[v[2] for v in vertices],
            i=i_indices,
            j=j_indices,
            k=k_indices,
            color=package.color,
            opacity=0.7,
            name=f"Customer {package.customer_id}",
            hovertext=f"Package {package.package_id}<br>"
                     f"Customer: {package.customer_id}<br>"
                     f"Dimensions: {l:.2f}×{w:.2f}×{h:.2f}m<br>"
                     f"Volume: {package.volume():.3f}m³",
            hoverinfo="text",
            showlegend=True,
            legendgroup=f"customer_{package.customer_id}"
        ))
    
    def _add_overflow_section(self, fig: 'go.Figure', overflow: List[Package]):
        """Add visual indicator for overflow packages.
        
        Displays overflow packages as red markers in a separate area
        to the right of the cargo bay, indicating they couldn't fit.
        
        Args:
            fig: Plotly Figure to add overflow indicators to
            overflow: List of packages that couldn't be placed
        """
        # Display overflow packages in a separate area (to the right)
        offset_x = 5.0  # Offset from main cargo bay
        
        for i, package in enumerate(overflow):
            # Stack overflow packages vertically
            x = offset_x
            y = 0
            z = i * 1.0  # Stack with 1m spacing
            
            # Add red marker for overflow - Requirement 4.7
            fig.add_trace(go.Scatter3d(
                x=[x], y=[y], z=[z],
                mode="markers+text",
                marker=dict(size=10, color="red", symbol="x"),
                text=f"Overflow {i+1}",
                textposition="top center",
                name="Overflow",
                hovertext=f"Package {package.package_id}<br>"
                         f"Customer: {package.customer_id}<br>"
                         f"Dimensions: {package.length:.2f}×{package.width:.2f}×{package.height:.2f}m<br>"
                         f"Volume: {package.volume():.3f}m³<br>"
                         f"<b>OVERFLOW - Could not fit</b>",
                hoverinfo="text",
                showlegend=True,
                legendgroup="overflow"
            ))
