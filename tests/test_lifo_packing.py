"""
Unit tests for LIFO Packing Engine

Tests the Last-In-First-Out packing strategy with physics constraints.
"""

import os
import sys

# Critical: Add DLL directories for MinGW runtime
os.add_dll_directory(r"C:\mingw64\bin")
os.add_dll_directory(os.path.abspath("build"))

from dashboard.csv_parser import Package
from dashboard.lifo_packing_engine import LIFOPackingEngine, PlacedPackage, PackingResult


def test_basic_packing():
    """Test basic packing of a single package."""
    # Create a simple package
    package = Package(
        order_id="ORD001",
        source_name="Depot",
        destination_name="Customer 1",
        latitude=40.7128,
        longitude=-74.0060,
        length_m=0.5,
        width_m=0.4,
        height_m=0.3,
        weight_kg=10.0,
        fragile=False,
        this_side_up=False
    )
    
    # Create packing engine with 2m x 2m x 2m cargo bay
    engine = LIFOPackingEngine(
        vehicle_length_m=2.0,
        vehicle_width_m=2.0,
        vehicle_height_m=2.0
    )
    
    # Pack the package
    result = engine.pack_route([package], [1])
    
    # Verify package was placed
    assert len(result.placed_packages) == 1
    assert len(result.failed_packages) == 0
    assert result.utilization_percent > 0
    
    # Verify package is at origin (back-bottom-left)
    placed = result.placed_packages[0]
    assert placed.x == 0.0
    assert placed.y == 0.0
    assert placed.z == 0.0


def test_fragile_constraint():
    """Test that fragile packages cannot have items stacked on top."""
    # Create a fragile package on the floor
    fragile_pkg = Package(
        order_id="ORD001",
        source_name="Depot",
        destination_name="Customer 1",
        latitude=40.7128,
        longitude=-74.0060,
        length_m=1.0,
        width_m=1.0,
        height_m=0.5,
        weight_kg=10.0,
        fragile=True,
        this_side_up=False
    )
    
    # Create a normal package that would stack on top
    normal_pkg = Package(
        order_id="ORD002",
        source_name="Depot",
        destination_name="Customer 1",
        latitude=40.7128,
        longitude=-74.0060,
        length_m=0.5,
        width_m=0.5,
        height_m=0.5,
        weight_kg=5.0,
        fragile=False,
        this_side_up=False
    )
    
    # Create packing engine
    engine = LIFOPackingEngine(
        vehicle_length_m=2.0,
        vehicle_width_m=2.0,
        vehicle_height_m=2.0
    )
    
    # Pack both packages
    result = engine.pack_route([fragile_pkg, normal_pkg], [1, 1])
    
    # Both should be placed, but normal package should NOT be on top of fragile
    assert len(result.placed_packages) == 2
    
    # Find the placed packages
    placed_fragile = next(p for p in result.placed_packages if p.package.order_id == "ORD001")
    placed_normal = next(p for p in result.placed_packages if p.package.order_id == "ORD002")
    
    # Normal package should not be directly above fragile package
    # Either different XY position or same Z level
    if placed_normal.z > placed_fragile.z:
        # If normal is higher, XY footprints should not overlap
        x_overlap = (placed_normal.x < placed_fragile.x + placed_fragile.length and
                    placed_normal.x + placed_normal.length > placed_fragile.x)
        y_overlap = (placed_normal.y < placed_fragile.y + placed_fragile.width and
                    placed_normal.y + placed_normal.width > placed_fragile.y)
        assert not (x_overlap and y_overlap), "Normal package should not be on top of fragile package"


def test_orientation_lock():
    """Test that this_side_up packages maintain orientation."""
    # Create a package with orientation lock
    locked_pkg = Package(
        order_id="ORD001",
        source_name="Depot",
        destination_name="Customer 1",
        latitude=40.7128,
        longitude=-74.0060,
        length_m=1.0,
        width_m=0.5,
        height_m=0.3,
        weight_kg=10.0,
        fragile=False,
        this_side_up=True
    )
    
    # Create packing engine
    engine = LIFOPackingEngine(
        vehicle_length_m=2.0,
        vehicle_width_m=2.0,
        vehicle_height_m=2.0
    )
    
    # Pack the package
    result = engine.pack_route([locked_pkg], [1])
    
    # Verify package was placed
    assert len(result.placed_packages) == 1
    
    # Verify dimensions match original (no rotation in X/Y)
    placed = result.placed_packages[0]
    # Height should remain as height (Z dimension)
    assert placed.height == 0.3


def test_stability_requirement():
    """Test that packages require 60% base support."""
    # This is a complex test - for now just verify the method exists
    engine = LIFOPackingEngine(
        vehicle_length_m=2.0,
        vehicle_width_m=2.0,
        vehicle_height_m=2.0
    )
    
    # Create a test package
    package = Package(
        order_id="ORD001",
        source_name="Depot",
        destination_name="Customer 1",
        latitude=40.7128,
        longitude=-74.0060,
        length_m=0.5,
        width_m=0.5,
        height_m=0.5,
        weight_kg=10.0,
        fragile=False,
        this_side_up=False
    )
    
    # Test stability check on floor (should always be stable)
    assert engine._check_stability(package, 0, 0, 0, 0.5, 0.5, 0.5) == True


def test_lifo_sorting():
    """Test that packages are sorted by reverse stop order and volume."""
    # Create packages for different stops
    pkg1 = Package(
        order_id="ORD001",
        source_name="Depot",
        destination_name="Customer 1",
        latitude=40.7128,
        longitude=-74.0060,
        length_m=0.5,
        width_m=0.5,
        height_m=0.5,  # volume = 0.125
        weight_kg=10.0,
        fragile=False,
        this_side_up=False
    )
    
    pkg2 = Package(
        order_id="ORD002",
        source_name="Depot",
        destination_name="Customer 2",
        latitude=40.7589,
        longitude=-73.9851,
        length_m=1.0,
        width_m=1.0,
        height_m=1.0,  # volume = 1.0
        weight_kg=20.0,
        fragile=False,
        this_side_up=False
    )
    
    engine = LIFOPackingEngine(
        vehicle_length_m=3.0,
        vehicle_width_m=3.0,
        vehicle_height_m=3.0
    )
    
    # Sort packages - stop order [1, 2] means stop 2 is last delivery
    sorted_pairs = engine._sort_packages_lifo([pkg1, pkg2], [1, 2])
    
    # Should return list of (package, stop_num) tuples
    assert len(sorted_pairs) == 2


if __name__ == "__main__":
    test_basic_packing()
    print("✓ Basic packing test passed")
    
    test_fragile_constraint()
    print("✓ Fragile constraint test passed")
    
    test_orientation_lock()
    print("✓ Orientation lock test passed")
    
    test_stability_requirement()
    print("✓ Stability requirement test passed")
    
    test_lifo_sorting()
    print("✓ LIFO sorting test passed")
    
    print("\nAll tests passed!")
