"""
Tests for 3D Load Optimization - Core Packing Algorithm

This test file validates the core packing engine functionality including:
- Package data model
- VehicleProfile with cargo bay dimensions
- PackageGenerator
- FirstFitDecreasingPacker algorithm
- PackingResult
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dashboard.packing_engine import (
    Package,
    VehicleProfile,
    PackageGenerator,
    FirstFitDecreasingPacker,
    PackingResult
)


class TestPackage:
    """Test Package data model."""
    
    def test_package_creation(self):
        """Test basic package creation with all attributes."""
        pkg = Package(
            package_id=1,
            customer_id=10,
            length=0.5,
            width=0.4,
            height=0.3
        )
        
        assert pkg.package_id == 1
        assert pkg.customer_id == 10
        assert pkg.length == 0.5
        assert pkg.width == 0.4
        assert pkg.height == 0.3
        assert pkg.color is not None  # Color should be auto-generated
        assert pkg.x is None  # Not placed yet
        assert pkg.y is None
        assert pkg.z is None
        assert pkg.is_placed is False
    
    def test_package_volume(self):
        """Test volume calculation."""
        pkg = Package(1, 10, 0.5, 0.4, 0.3)
        expected_volume = 0.5 * 0.4 * 0.3
        assert abs(pkg.volume() - expected_volume) < 0.001
    
    def test_color_consistency(self):
        """Test that same customer ID generates same color."""
        pkg1 = Package(1, 10, 0.5, 0.4, 0.3)
        pkg2 = Package(2, 10, 0.6, 0.5, 0.4)
        pkg3 = Package(3, 20, 0.5, 0.4, 0.3)
        
        assert pkg1.color == pkg2.color  # Same customer
        assert pkg1.color != pkg3.color  # Different customer


class TestVehicleProfile:
    """Test VehicleProfile with cargo bay dimensions."""
    
    def test_vehicle_with_explicit_dimensions(self):
        """Test vehicle profile with explicit cargo dimensions."""
        vehicle = VehicleProfile(
            vehicle_type="Tempo",
            capacity=1000.0,
            cargo_length=3.0,
            cargo_width=2.0,
            cargo_height=2.0
        )
        
        assert vehicle.vehicle_type == "Tempo"
        assert vehicle.capacity == 1000.0
        assert vehicle.cargo_length == 3.0
        assert vehicle.cargo_width == 2.0
        assert vehicle.cargo_height == 2.0
    
    def test_vehicle_default_dimensions_tempo(self):
        """Test default dimensions for Tempo vehicle type."""
        vehicle = VehicleProfile(vehicle_type="Tempo", capacity=1000.0)
        
        assert vehicle.cargo_length == 2.5
        assert vehicle.cargo_width == 1.5
        assert vehicle.cargo_height == 1.5
    
    def test_vehicle_default_dimensions_truck(self):
        """Test default dimensions for Truck vehicle type."""
        vehicle = VehicleProfile(vehicle_type="Truck", capacity=2000.0)
        
        assert vehicle.cargo_length == 4.0
        assert vehicle.cargo_width == 2.0
        assert vehicle.cargo_height == 2.5
    
    def test_cargo_volume_calculation(self):
        """Test cargo bay volume calculation."""
        vehicle = VehicleProfile(
            vehicle_type="Tempo",
            capacity=1000.0,
            cargo_length=3.0,
            cargo_width=2.0,
            cargo_height=2.0
        )
        
        expected_volume = 3.0 * 2.0 * 2.0
        assert abs(vehicle.cargo_volume() - expected_volume) < 0.001


class TestPackageGenerator:
    """Test PackageGenerator."""
    
    def test_generate_packages_count(self):
        """Test that generator creates correct number of packages."""
        generator = PackageGenerator(random_seed=42)
        customer_demands = [(1, 3), (2, 2), (3, 1)]  # Total 6 packages
        
        packages = generator.generate_packages(customer_demands)
        
        assert len(packages) == 6
    
    def test_generate_packages_customer_assignment(self):
        """Test that packages are assigned to correct customers."""
        generator = PackageGenerator(random_seed=42)
        customer_demands = [(1, 2), (2, 3)]
        
        packages = generator.generate_packages(customer_demands)
        
        # First 2 packages should be for customer 1
        assert packages[0].customer_id == 1
        assert packages[1].customer_id == 1
        
        # Next 3 packages should be for customer 2
        assert packages[2].customer_id == 2
        assert packages[3].customer_id == 2
        assert packages[4].customer_id == 2
    
    def test_generate_packages_dimension_bounds(self):
        """Test that generated dimensions are within bounds."""
        generator = PackageGenerator(min_dimension=0.3, max_dimension=0.8, random_seed=42)
        customer_demands = [(1, 10)]
        
        packages = generator.generate_packages(customer_demands)
        
        for pkg in packages:
            assert 0.3 <= pkg.length <= 0.8
            assert 0.3 <= pkg.width <= 0.8
            assert 0.3 <= pkg.height <= 0.8
    
    def test_deterministic_generation(self):
        """Test that same seed produces same packages."""
        generator1 = PackageGenerator(random_seed=42)
        generator2 = PackageGenerator(random_seed=42)
        customer_demands = [(1, 5)]
        
        packages1 = generator1.generate_packages(customer_demands)
        packages2 = generator2.generate_packages(customer_demands)
        
        assert len(packages1) == len(packages2)
        for p1, p2 in zip(packages1, packages2):
            assert abs(p1.length - p2.length) < 0.001
            assert abs(p1.width - p2.width) < 0.001
            assert abs(p1.height - p2.height) < 0.001


class TestFirstFitDecreasingPacker:
    """Test FirstFitDecreasingPacker algorithm."""
    
    def test_pack_empty_list(self):
        """Test packing with no packages."""
        packer = FirstFitDecreasingPacker(
            cargo_length=2.5,
            cargo_width=1.5,
            cargo_height=1.5
        )
        
        result = packer.pack([])
        
        assert len(result.placed) == 0
        assert len(result.overflow) == 0
        assert result.utilization == 0.0
        assert result.is_feasible() is True
    
    def test_pack_single_package_fits(self):
        """Test packing single package that fits."""
        packer = FirstFitDecreasingPacker(
            cargo_length=2.5,
            cargo_width=1.5,
            cargo_height=1.5
        )
        
        pkg = Package(1, 10, 0.5, 0.4, 0.3)
        result = packer.pack([pkg])
        
        assert len(result.placed) == 1
        assert len(result.overflow) == 0
        assert result.placed[0].is_placed is True
        assert result.placed[0].x is not None
        assert result.placed[0].y is not None
        assert result.placed[0].z is not None
        assert result.is_feasible() is True
    
    def test_pack_package_too_large(self):
        """Test packing package that doesn't fit."""
        packer = FirstFitDecreasingPacker(
            cargo_length=1.0,
            cargo_width=1.0,
            cargo_height=1.0
        )
        
        # Package larger than cargo bay
        pkg = Package(1, 10, 2.0, 2.0, 2.0)
        result = packer.pack([pkg])
        
        assert len(result.placed) == 0
        assert len(result.overflow) == 1
        assert result.overflow[0].is_placed is False
        assert result.is_feasible() is False
    
    def test_pack_multiple_packages(self):
        """Test packing multiple packages."""
        packer = FirstFitDecreasingPacker(
            cargo_length=2.5,
            cargo_width=1.5,
            cargo_height=1.5
        )
        
        packages = [
            Package(1, 10, 0.5, 0.4, 0.3),
            Package(2, 10, 0.6, 0.5, 0.4),
            Package(3, 20, 0.4, 0.3, 0.3)
        ]
        
        result = packer.pack(packages)
        
        # All should fit in a 2.5x1.5x1.5 cargo bay
        assert len(result.placed) == 3
        assert len(result.overflow) == 0
        assert result.is_feasible() is True
    
    def test_volume_based_sorting(self):
        """Test that packages are sorted by volume (largest first)."""
        packer = FirstFitDecreasingPacker(
            cargo_length=5.0,
            cargo_width=5.0,
            cargo_height=5.0
        )
        
        # Create packages with different volumes
        small = Package(1, 10, 0.3, 0.3, 0.3)  # Volume: 0.027
        medium = Package(2, 20, 0.5, 0.5, 0.5)  # Volume: 0.125
        large = Package(3, 30, 0.8, 0.8, 0.8)  # Volume: 0.512
        
        # Pack in random order
        result = packer.pack([small, large, medium])
        
        # Verify all placed
        assert len(result.placed) == 3
        
        # The largest package should be placed first (at origin)
        # Find which package is at origin
        origin_pkg = None
        for pkg in result.placed:
            if pkg.x == 0.0 and pkg.y == 0.0 and pkg.z == 0.0:
                origin_pkg = pkg
                break
        
        assert origin_pkg is not None
        # The package at origin should be the largest one (customer 30)
        assert origin_pkg.customer_id == 30
    
    def test_no_package_overlap(self):
        """Test that placed packages don't overlap."""
        packer = FirstFitDecreasingPacker(
            cargo_length=3.0,
            cargo_width=2.0,
            cargo_height=2.0
        )
        
        packages = [
            Package(i, 10, 0.5, 0.5, 0.5)
            for i in range(5)
        ]
        
        result = packer.pack(packages)
        
        # Check all placed packages for overlap
        for i, pkg1 in enumerate(result.placed):
            for pkg2 in result.placed[i+1:]:
                # Check if boxes overlap
                x_overlap = (pkg1.x < pkg2.x + pkg2.length) and (pkg1.x + pkg1.length > pkg2.x)
                y_overlap = (pkg1.y < pkg2.y + pkg2.width) and (pkg1.y + pkg1.width > pkg2.y)
                z_overlap = (pkg1.z < pkg2.z + pkg2.height) and (pkg1.z + pkg1.height > pkg2.z)
                
                overlap = x_overlap and y_overlap and z_overlap
                assert not overlap, f"Packages {pkg1.package_id} and {pkg2.package_id} overlap"
    
    def test_cargo_bay_boundaries(self):
        """Test that all placed packages are within cargo bay boundaries."""
        cargo_length = 2.5
        cargo_width = 1.5
        cargo_height = 1.5
        
        packer = FirstFitDecreasingPacker(cargo_length, cargo_width, cargo_height)
        
        packages = [
            Package(i, 10, 0.5, 0.4, 0.3)
            for i in range(10)
        ]
        
        result = packer.pack(packages)
        
        # Check all placed packages are within boundaries
        for pkg in result.placed:
            assert pkg.x + pkg.length <= cargo_length, f"Package {pkg.package_id} exceeds length boundary"
            assert pkg.y + pkg.width <= cargo_width, f"Package {pkg.package_id} exceeds width boundary"
            assert pkg.z + pkg.height <= cargo_height, f"Package {pkg.package_id} exceeds height boundary"


class TestPackingResult:
    """Test PackingResult."""
    
    def test_packing_result_summary(self):
        """Test summary statistics generation."""
        placed = [Package(i, 10, 0.5, 0.4, 0.3) for i in range(3)]
        overflow = [Package(i, 20, 0.6, 0.5, 0.4) for i in range(3, 5)]
        
        result = PackingResult(placed, overflow, 45.5)
        summary = result.summary()
        
        assert summary["total_packages"] == 5
        assert summary["placed_packages"] == 3
        assert summary["overflow_packages"] == 2
        assert summary["utilization_percent"] == 45.5
        assert summary["is_feasible"] is False
    
    def test_is_feasible_true(self):
        """Test feasibility check when all packages placed."""
        placed = [Package(i, 10, 0.5, 0.4, 0.3) for i in range(3)]
        result = PackingResult(placed, [], 45.5)
        
        assert result.is_feasible() is True
    
    def test_is_feasible_false(self):
        """Test feasibility check when overflow exists."""
        placed = [Package(i, 10, 0.5, 0.4, 0.3) for i in range(3)]
        overflow = [Package(3, 20, 0.6, 0.5, 0.4)]
        result = PackingResult(placed, overflow, 45.5)
        
        assert result.is_feasible() is False
