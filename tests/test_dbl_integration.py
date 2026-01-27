"""
Integration tests for DBL packing engine with CSV parser and existing systems.

This test module validates that the DBL packing engine integrates correctly with:
- CSV parser output (realistic-data-physics-upgrade)
- Existing visualization system
- Dashboard configuration system
"""

import os
import sys
import pytest

# Add dashboard directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'dashboard'))

from csv_parser import CSVParser
from packing_engine_dbl import (
    DBLPackingEngine, Package, PlacedPackage, PackingResult
)


class TestCSVParserIntegration:
    """Test integration between CSV parser and DBL packing engine."""
    
    def test_load_sample_csv_and_pack(self):
        """
        Task 8.1: Load sample CSV from realistic-data-physics-upgrade,
        parse packages, assign stop numbers, run DBL packing engine,
        and verify results are valid.
        
        Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.3, 2.4, 2.5, 2.6,
                     3.1, 3.2, 3.3, 3.5, 4.1, 4.2, 4.3, 4.4, 5.3, 5.4
        """
        # Load sample CSV
        parser = CSVParser()
        csv_path = os.path.join(os.path.dirname(__file__), '..', 'sample_manifest.csv')
        destinations, error = parser.parse_manifest(csv_path)
        
        # Verify CSV loaded successfully
        assert error is None, f"CSV parsing failed: {error}"
        assert len(destinations) > 0, "No destinations found in CSV"
        
        # Convert CSV packages to DBL Package format with stop numbers
        dbl_packages = []
        stop_number = 1
        
        for destination in destinations:
            for csv_package in destination.packages:
                # Create DBL Package with stop number assigned
                dbl_package = Package(
                    order_id=csv_package.order_id,
                    length_m=csv_package.length_m,
                    width_m=csv_package.width_m,
                    height_m=csv_package.height_m,
                    weight_kg=csv_package.weight_kg,
                    stop_number=stop_number,
                    fragile=csv_package.fragile,
                    this_side_up=csv_package.this_side_up
                )
                dbl_packages.append(dbl_package)
            stop_number += 1
        
        # Verify packages were created
        assert len(dbl_packages) > 0, "No packages created from CSV"
        
        # Create DBL packing engine with standard vehicle dimensions
        # Using a medium-sized van: 3m x 2m x 2m
        engine = DBLPackingEngine(
            vehicle_length_m=3.0,
            vehicle_width_m=2.0,
            vehicle_height_m=2.0
        )
        
        # Run DBL packing algorithm
        result = engine.pack_route(dbl_packages)
        
        # Verify result structure is valid
        assert isinstance(result, PackingResult), "Result should be PackingResult"
        assert isinstance(result.placed_packages, list), "placed_packages should be a list"
        assert isinstance(result.failed_packages, list), "failed_packages should be a list"
        assert isinstance(result.utilization_percent, float), "utilization should be float"
        assert isinstance(result.total_weight_kg, float), "total_weight should be float"
        
        # Verify all packages are accounted for
        total_packages = len(result.placed_packages) + len(result.failed_packages)
        assert total_packages == len(dbl_packages), \
            f"Package count mismatch: {total_packages} != {len(dbl_packages)}"
        
        # Verify utilization is in valid range
        assert 0.0 <= result.utilization_percent <= 100.0, \
            f"Utilization out of range: {result.utilization_percent}"
        
        # Verify placed packages have valid positions
        for placed in result.placed_packages:
            assert isinstance(placed, PlacedPackage), "Should be PlacedPackage"
            assert placed.x >= 0, f"X coordinate should be non-negative: {placed.x}"
            assert placed.y >= 0, f"Y coordinate should be non-negative: {placed.y}"
            assert placed.z >= 0, f"Z coordinate should be non-negative: {placed.z}"
            
            # Verify package fits within vehicle boundaries
            assert placed.x + placed.length <= 3.0, \
                f"Package exceeds vehicle length: {placed.x + placed.length}"
            assert placed.y + placed.width <= 2.0, \
                f"Package exceeds vehicle width: {placed.y + placed.width}"
            assert placed.z + placed.height <= 2.0, \
                f"Package exceeds vehicle height: {placed.z + placed.height}"
        
        # Verify failed packages have reasons
        for package, reason in result.failed_packages:
            assert isinstance(package, Package), "Should be Package"
            assert isinstance(reason, str), "Reason should be string"
            assert len(reason) > 0, "Reason should not be empty"
        
        # Print summary for manual verification
        print(f"\n=== DBL Packing Integration Test Results ===")
        print(f"Total packages: {len(dbl_packages)}")
        print(f"Placed packages: {len(result.placed_packages)}")
        print(f"Failed packages: {len(result.failed_packages)}")
        print(f"Utilization: {result.utilization_percent:.2f}%")
        print(f"Total weight: {result.total_weight_kg:.2f} kg")
        
        if result.failed_packages:
            print(f"\nFailed packages:")
            for pkg, reason in result.failed_packages:
                print(f"  - {pkg.order_id}: {reason}")
    
    def test_csv_to_dbl_package_conversion(self):
        """
        Verify that CSV packages can be correctly converted to DBL Package format.
        
        This test ensures data integrity during conversion from CSV parser output
        to DBL packing engine input format.
        """
        # Load sample CSV
        parser = CSVParser()
        csv_path = os.path.join(os.path.dirname(__file__), '..', 'sample_manifest.csv')
        destinations, error = parser.parse_manifest(csv_path)
        
        assert error is None, f"CSV parsing failed: {error}"
        assert len(destinations) > 0, "No destinations found"
        
        # Take first package from first destination
        csv_package = destinations[0].packages[0]
        
        # Convert to DBL Package
        dbl_package = Package(
            order_id=csv_package.order_id,
            length_m=csv_package.length_m,
            width_m=csv_package.width_m,
            height_m=csv_package.height_m,
            weight_kg=csv_package.weight_kg,
            stop_number=1,
            fragile=csv_package.fragile,
            this_side_up=csv_package.this_side_up
        )
        
        # Verify all fields transferred correctly
        assert dbl_package.order_id == csv_package.order_id
        assert dbl_package.length_m == csv_package.length_m
        assert dbl_package.width_m == csv_package.width_m
        assert dbl_package.height_m == csv_package.height_m
        assert dbl_package.weight_kg == csv_package.weight_kg
        assert dbl_package.fragile == csv_package.fragile
        assert dbl_package.this_side_up == csv_package.this_side_up
        assert dbl_package.stop_number == 1
        
        # Verify calculated properties work
        assert dbl_package.volume_m3 > 0
        assert dbl_package.base_area_m2 > 0
    
    def test_multiple_stops_lifo_ordering(self):
        """
        Verify that packages from multiple stops are processed in LIFO order.
        
        This test ensures that the DBL engine respects the LIFO constraint
        when packing packages from multiple delivery stops.
        """
        # Create packages for 3 different stops
        packages = [
            # Stop 1 (should be loaded last)
            Package("PKG1-1", 0.5, 0.4, 0.3, 10.0, 1),
            Package("PKG1-2", 0.4, 0.4, 0.3, 8.0, 1),
            # Stop 2 (should be loaded second)
            Package("PKG2-1", 0.5, 0.5, 0.4, 15.0, 2),
            Package("PKG2-2", 0.3, 0.3, 0.3, 5.0, 2),
            # Stop 3 (should be loaded first - highest stop number)
            Package("PKG3-1", 0.6, 0.5, 0.5, 20.0, 3),
            Package("PKG3-2", 0.4, 0.3, 0.3, 7.0, 3),
        ]
        
        # Create engine
        engine = DBLPackingEngine(3.0, 2.0, 2.0)
        
        # Pack packages
        result = engine.pack_route(packages)
        
        # Verify LIFO ordering: Stop 3 packages should be placed first
        # (they will have lower indices in placed_packages list)
        placed_stop_numbers = [p.package.stop_number for p in result.placed_packages]
        
        # Find indices of each stop's first package
        stop3_indices = [i for i, sn in enumerate(placed_stop_numbers) if sn == 3]
        stop2_indices = [i for i, sn in enumerate(placed_stop_numbers) if sn == 2]
        stop1_indices = [i for i, sn in enumerate(placed_stop_numbers) if sn == 1]
        
        # Verify stop 3 packages come before stop 2 packages
        if stop3_indices and stop2_indices:
            assert max(stop3_indices) < min(stop2_indices), \
                "Stop 3 packages should be placed before Stop 2 packages (LIFO)"
        
        # Verify stop 2 packages come before stop 1 packages
        if stop2_indices and stop1_indices:
            assert max(stop2_indices) < min(stop1_indices), \
                "Stop 2 packages should be placed before Stop 1 packages (LIFO)"
        
        print(f"\n=== LIFO Ordering Test ===")
        print(f"Placement order (by stop): {placed_stop_numbers}")
    
    def test_weight_based_secondary_sort(self):
        """
        Verify that within the same stop, heavier packages are placed first.
        
        This test validates the secondary sort criterion (weight descending)
        within each stop group.
        """
        # Create packages for same stop with different weights
        packages = [
            Package("LIGHT", 0.3, 0.3, 0.3, 5.0, 1),   # Light
            Package("HEAVY", 0.3, 0.3, 0.3, 20.0, 1),  # Heavy
            Package("MEDIUM", 0.3, 0.3, 0.3, 12.0, 1), # Medium
        ]
        
        # Create engine
        engine = DBLPackingEngine(3.0, 2.0, 2.0)
        
        # Pack packages
        result = engine.pack_route(packages)
        
        # All should be placed (small packages)
        assert len(result.placed_packages) == 3, "All packages should fit"
        
        # Extract placement order by weight
        placed_weights = [p.package.weight_kg for p in result.placed_packages]
        
        # Verify heavier packages are placed first (descending weight order)
        # HEAVY (20kg) should come before MEDIUM (12kg) should come before LIGHT (5kg)
        assert placed_weights[0] == 20.0, "Heaviest package should be placed first"
        assert placed_weights[1] == 12.0, "Medium package should be placed second"
        assert placed_weights[2] == 5.0, "Lightest package should be placed last"
        
        print(f"\n=== Weight-Based Sort Test ===")
        print(f"Placement order (by weight): {placed_weights}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])



class TestVisualizationCompatibility:
    """Test compatibility between DBL packing engine and visualization system."""
    
    def test_placed_package_format_compatibility(self):
        """
        Task 8.2: Verify that PlacedPackage objects from DBL engine
        are compatible with the existing visualization system.
        
        Requirements: 1.1, 1.2, 1.3, 1.4, 1.5
        """
        # Create a simple package and place it
        package = Package("TEST001", 0.5, 0.4, 0.3, 10.0, 1)
        
        # Create engine and pack
        engine = DBLPackingEngine(3.0, 2.0, 2.0)
        result = engine.pack_route([package])
        
        # Verify package was placed
        assert len(result.placed_packages) == 1, "Package should be placed"
        
        placed = result.placed_packages[0]
        
        # Verify PlacedPackage has all required attributes for visualization
        assert hasattr(placed, 'x'), "PlacedPackage should have x coordinate"
        assert hasattr(placed, 'y'), "PlacedPackage should have y coordinate"
        assert hasattr(placed, 'z'), "PlacedPackage should have z coordinate"
        assert hasattr(placed, 'length'), "PlacedPackage should have length"
        assert hasattr(placed, 'width'), "PlacedPackage should have width"
        assert hasattr(placed, 'height'), "PlacedPackage should have height"
        assert hasattr(placed, 'package'), "PlacedPackage should have package reference"
        
        # Verify coordinate properties work
        assert hasattr(placed, 'x_max'), "PlacedPackage should have x_max property"
        assert hasattr(placed, 'y_max'), "PlacedPackage should have y_max property"
        assert hasattr(placed, 'z_max'), "PlacedPackage should have z_max property"
        
        # Verify max coordinates are calculated correctly
        assert placed.x_max == placed.x + placed.length
        assert placed.y_max == placed.y + placed.width
        assert placed.z_max == placed.z + placed.height
        
        print(f"\n=== Visualization Compatibility Test ===")
        print(f"Package position: ({placed.x:.2f}, {placed.y:.2f}, {placed.z:.2f})")
        print(f"Package dimensions: {placed.length:.2f} x {placed.width:.2f} x {placed.height:.2f}")
        print(f"Package bounds: x=[{placed.x:.2f}, {placed.x_max:.2f}], "
              f"y=[{placed.y:.2f}, {placed.y_max:.2f}], "
              f"z=[{placed.z:.2f}, {placed.z_max:.2f}]")
    
    def test_coordinate_system_convention(self):
        """
        Verify that DBL engine uses the correct coordinate system convention:
        X=0 is back, X=max is door (matches existing system).
        
        This ensures visualization will render packages in the correct orientation.
        """
        # Create packages that will be placed at different positions
        packages = [
            Package("FIRST", 0.5, 0.5, 0.5, 10.0, 1),
            Package("SECOND", 0.5, 0.5, 0.5, 10.0, 1),
        ]
        
        # Create engine
        engine = DBLPackingEngine(3.0, 2.0, 2.0)
        
        # Pack packages
        result = engine.pack_route(packages)
        
        # Both should be placed
        assert len(result.placed_packages) == 2, "Both packages should fit"
        
        # Verify coordinate system:
        # - First package should be at origin (0, 0, 0) - back of vehicle
        # - Second package should be placed to the right or front (X or Y increases)
        first = result.placed_packages[0]
        second = result.placed_packages[1]
        
        # First package should start at origin
        assert first.x == 0.0, "First package should be at X=0 (back)"
        assert first.y == 0.0, "First package should be at Y=0 (left)"
        assert first.z == 0.0, "First package should be at Z=0 (floor)"
        
        # Second package should be placed adjacent (not overlapping)
        # It should be at (0.5, 0, 0) or (0, 0.5, 0) or (0, 0, 0.5)
        assert (second.x >= first.x_max or 
                second.y >= first.y_max or 
                second.z >= first.z_max), \
            "Second package should not overlap with first"
        
        # Verify all coordinates are non-negative (no packages behind/below origin)
        assert second.x >= 0.0, "X coordinate should be non-negative"
        assert second.y >= 0.0, "Y coordinate should be non-negative"
        assert second.z >= 0.0, "Z coordinate should be non-negative"
        
        print(f"\n=== Coordinate System Test ===")
        print(f"First package: ({first.x:.2f}, {first.y:.2f}, {first.z:.2f})")
        print(f"Second package: ({second.x:.2f}, {second.y:.2f}, {second.z:.2f})")
        print(f"Coordinate system: X=0 is back, Y=0 is left, Z=0 is floor")
    
    def test_visualization_data_structure(self):
        """
        Verify that DBL packing results can be converted to visualization format.
        
        This test ensures the data structure is compatible with the existing
        CargoVisualizationRenderer from packing_engine.py.
        """
        # Import the old packing engine's Package class for comparison
        from packing_engine import Package as OldPackage
        
        # Create DBL packages
        dbl_packages = [
            Package("PKG1", 0.5, 0.4, 0.3, 10.0, 1),
            Package("PKG2", 0.4, 0.4, 0.4, 8.0, 1),
        ]
        
        # Pack with DBL engine
        engine = DBLPackingEngine(3.0, 2.0, 2.0)
        result = engine.pack_route(dbl_packages)
        
        # Verify we can extract visualization data from DBL PlacedPackages
        for placed in result.placed_packages:
            # Check that we can access all fields needed for visualization
            viz_data = {
                'x': placed.x,
                'y': placed.y,
                'z': placed.z,
                'length': placed.length,
                'width': placed.width,
                'height': placed.height,
                'order_id': placed.package.order_id,
                'weight': placed.package.weight_kg,
            }
            
            # Verify all fields are valid
            assert all(isinstance(v, (int, float, str)) for v in viz_data.values()), \
                "All visualization data should be primitive types"
            
            # Verify numeric fields are non-negative
            for key in ['x', 'y', 'z', 'length', 'width', 'height', 'weight']:
                assert viz_data[key] >= 0, f"{key} should be non-negative"
        
        print(f"\n=== Visualization Data Structure Test ===")
        print(f"Successfully extracted visualization data for {len(result.placed_packages)} packages")
    
    def test_packing_result_compatibility(self):
        """
        Verify that PackingResult from DBL engine has the same structure
        as the old packing engine's result format.
        """
        # Create packages
        packages = [
            Package("PKG1", 0.5, 0.4, 0.3, 10.0, 1),
            Package("PKG2", 0.4, 0.4, 0.4, 8.0, 1),
            Package("OVERSIZED", 5.0, 5.0, 5.0, 100.0, 1),  # Won't fit
        ]
        
        # Pack with DBL engine
        engine = DBLPackingEngine(3.0, 2.0, 2.0)
        result = engine.pack_route(packages)
        
        # Verify PackingResult has expected structure
        assert hasattr(result, 'placed_packages'), "Result should have placed_packages"
        assert hasattr(result, 'failed_packages'), "Result should have failed_packages"
        assert hasattr(result, 'utilization_percent'), "Result should have utilization_percent"
        assert hasattr(result, 'total_weight_kg'), "Result should have total_weight_kg"
        
        # Verify types
        assert isinstance(result.placed_packages, list)
        assert isinstance(result.failed_packages, list)
        assert isinstance(result.utilization_percent, float)
        assert isinstance(result.total_weight_kg, float)
        
        # Verify failed packages have reasons
        assert len(result.failed_packages) > 0, "Oversized package should fail"
        for pkg, reason in result.failed_packages:
            assert isinstance(pkg, Package)
            assert isinstance(reason, str)
            assert len(reason) > 0
        
        print(f"\n=== Packing Result Compatibility Test ===")
        print(f"Placed: {len(result.placed_packages)}, Failed: {len(result.failed_packages)}")
        print(f"Utilization: {result.utilization_percent:.2f}%")
        print(f"Total weight: {result.total_weight_kg:.2f} kg")



class TestPackingEngineConfiguration:
    """Test configuration system for switching between packing engines."""
    
    def test_packing_config_creation(self):
        """
        Task 8.3: Create PackingConfig dataclass with engine selection.
        
        Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.3, 2.4, 2.5, 2.6,
                     3.1, 3.2, 3.3, 3.5, 4.1, 4.2, 4.3, 4.4, 5.3, 5.4
        """
        from packing_config import PackingConfig, PackingEngineType
        
        # Test default configuration (DBL)
        config = PackingConfig()
        assert config.engine_type == PackingEngineType.DBL
        assert config.support_threshold == 0.80
        assert config.weight_ratio_max == 1.5
        assert config.tolerance == 0.001
        assert config.max_contact_points is None  # Default is unlimited
        
        # Test LIFO configuration
        lifo_config = PackingConfig.create_lifo_config()
        assert lifo_config.engine_type == PackingEngineType.LIFO
        
        # Test custom DBL configuration
        custom_config = PackingConfig.create_dbl_config(
            support_threshold=0.75,
            weight_ratio_max=2.0
        )
        assert custom_config.engine_type == PackingEngineType.DBL
        assert custom_config.support_threshold == 0.75
        assert custom_config.weight_ratio_max == 2.0
        
        print(f"\n=== Packing Config Test ===")
        print(f"Default engine: {config.get_display_name()}")
        print(f"LIFO engine: {lifo_config.get_display_name()}")
        print(f"Custom DBL: support={custom_config.support_threshold}, "
              f"weight_ratio={custom_config.weight_ratio_max}")
    
    def test_config_validation(self):
        """Verify that PackingConfig validates parameters correctly."""
        from packing_config import PackingConfig, PackingEngineType
        
        # Valid configuration should work
        config = PackingConfig(
            engine_type=PackingEngineType.DBL,
            support_threshold=0.75,
            weight_ratio_max=2.0,
            tolerance=0.01,
            max_contact_points=50
        )
        assert config.support_threshold == 0.75
        
        # Invalid support threshold (too low)
        with pytest.raises(ValueError, match="support_threshold"):
            PackingConfig(support_threshold=0.0)
        
        # Invalid support threshold (too high)
        with pytest.raises(ValueError, match="support_threshold"):
            PackingConfig(support_threshold=1.5)
        
        # Invalid weight ratio
        with pytest.raises(ValueError, match="weight_ratio_max"):
            PackingConfig(weight_ratio_max=-1.0)
        
        # Invalid tolerance
        with pytest.raises(ValueError, match="tolerance"):
            PackingConfig(tolerance=-0.001)
        
        # Invalid max contact points
        with pytest.raises(ValueError, match="max_contact_points"):
            PackingConfig(max_contact_points=0)
        
        print(f"\n=== Config Validation Test ===")
        print(f"All validation checks passed")
    
    def test_engine_comparison(self):
        """
        Task 8.3: Run both engines in parallel for comparison.
        
        This test compares LIFO and DBL engines on the same package set
        to demonstrate their different behaviors.
        """
        from packing_engine import FirstFitDecreasingPacker, Package as OldPackage
        from packing_config import PackingConfig, PackingEngineType
        
        # Create test packages (same for both engines)
        # Using packages that will test gravity constraints
        test_packages_dbl = [
            Package("PKG1", 0.5, 0.5, 0.5, 20.0, 1),  # Heavy base
            Package("PKG2", 0.5, 0.5, 0.5, 5.0, 1),   # Light on top
            Package("PKG3", 0.4, 0.4, 0.4, 15.0, 2),
            Package("PKG4", 0.3, 0.3, 0.3, 8.0, 2),
        ]
        
        # Convert to old package format for LIFO engine
        test_packages_lifo = [
            OldPackage(i, 1, pkg.length_m, pkg.width_m, pkg.height_m)
            for i, pkg in enumerate(test_packages_dbl)
        ]
        
        # Vehicle dimensions
        vehicle_length = 3.0
        vehicle_width = 2.0
        vehicle_height = 2.0
        
        # Run DBL engine
        dbl_engine = DBLPackingEngine(vehicle_length, vehicle_width, vehicle_height)
        dbl_result = dbl_engine.pack_route(test_packages_dbl)
        
        # Run LIFO engine
        lifo_engine = FirstFitDecreasingPacker(vehicle_length, vehicle_width, vehicle_height)
        lifo_result = lifo_engine.pack(test_packages_lifo)
        
        # Compare results
        print(f"\n=== Engine Comparison Test ===")
        print(f"\nDBL Engine (Gravity-Aware):")
        print(f"  Placed: {len(dbl_result.placed_packages)}")
        print(f"  Failed: {len(dbl_result.failed_packages)}")
        print(f"  Utilization: {dbl_result.utilization_percent:.2f}%")
        print(f"  Total weight: {dbl_result.total_weight_kg:.2f} kg")
        
        print(f"\nLIFO Engine (First-Fit Decreasing):")
        print(f"  Placed: {len(lifo_result.placed)}")
        print(f"  Overflow: {len(lifo_result.overflow)}")
        print(f"  Utilization: {lifo_result.utilization:.2f}%")
        
        # Both engines should place all packages (they're small enough)
        assert len(dbl_result.placed_packages) > 0, "DBL should place some packages"
        assert len(lifo_result.placed) > 0, "LIFO should place some packages"
        
        # Verify DBL respects LIFO ordering (stop 2 before stop 1)
        dbl_stop_order = [p.package.stop_number for p in dbl_result.placed_packages]
        if len(dbl_stop_order) > 1:
            # Find first occurrence of each stop
            stop2_idx = next((i for i, s in enumerate(dbl_stop_order) if s == 2), None)
            stop1_idx = next((i for i, s in enumerate(dbl_stop_order) if s == 1), None)
            
            if stop2_idx is not None and stop1_idx is not None:
                assert stop2_idx < stop1_idx, "DBL should respect LIFO ordering"
                print(f"\n✓ DBL respects LIFO ordering: Stop 2 placed before Stop 1")
    
    def test_config_display_methods(self):
        """Test that configuration provides useful display information."""
        from packing_config import PackingConfig, PackingEngineType
        
        # Test DBL display
        dbl_config = PackingConfig.create_dbl_config()
        assert "DBL" in dbl_config.get_display_name()
        assert "Deepest-Bottom-Left" in dbl_config.get_display_name()
        assert "80%" in dbl_config.get_description()
        assert "1.5x" in dbl_config.get_description()
        
        # Test LIFO display
        lifo_config = PackingConfig.create_lifo_config()
        assert "LIFO" in lifo_config.get_display_name()
        assert "First-Fit" in lifo_config.get_display_name()
        assert "First-Fit Decreasing" in lifo_config.get_description()
        
        print(f"\n=== Config Display Test ===")
        print(f"DBL: {dbl_config.get_display_name()}")
        print(f"     {dbl_config.get_description()}")
        print(f"\nLIFO: {lifo_config.get_display_name()}")
        print(f"      {lifo_config.get_description()}")
    
    def test_default_config_functions(self):
        """Test convenience functions for getting default configurations."""
        from packing_config import get_default_config, get_lifo_config, PackingEngineType
        
        # Test default config (should be DBL)
        default = get_default_config()
        assert default.engine_type == PackingEngineType.DBL
        
        # Test LIFO config
        lifo = get_lifo_config()
        assert lifo.engine_type == PackingEngineType.LIFO
        
        print(f"\n=== Default Config Functions Test ===")
        print(f"Default engine: {default.get_display_name()}")
        print(f"LIFO engine: {lifo.get_display_name()}")
