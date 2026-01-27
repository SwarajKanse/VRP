"""
Checkpoint Tests for DBL Packing Engine - Constraint Validation

This test suite validates constraint validation methods implemented in tasks 1-3.
Feature: gravity-density-upgrade
"""

import os
import sys

# Critical: Add DLL directories for MinGW runtime
os.add_dll_directory(r"C:\mingw64\bin")
os.add_dll_directory(os.path.abspath("build"))

import pytest
import math

from dashboard.packing_engine_dbl import (
    Package,
    ContactPoint,
    PlacedPackage,
    DBLPackingEngine
)


def test_check_boundaries_valid():
    """Test boundary check with package that fits"""
    engine = DBLPackingEngine(3.0, 2.0, 2.0)
    package = Package("P1", 1.0, 0.5, 0.3, 10.0, 1)
    
    assert engine._check_boundaries(package, 0.0, 0.0, 0.0)
    assert engine._check_boundaries(package, 2.0, 1.5, 1.7)


def test_check_boundaries_invalid():
    """Test boundary check with package that doesn't fit"""
    engine = DBLPackingEngine(3.0, 2.0, 2.0)
    package = Package("P1", 1.0, 0.5, 0.3, 10.0, 1)
    
    assert not engine._check_boundaries(package, 2.5, 0.0, 0.0)
    assert not engine._check_boundaries(package, 0.0, 1.8, 0.0)
    assert not engine._check_boundaries(package, 0.0, 0.0, 1.8)


def test_check_overlap_no_overlap():
    """Test overlap check when packages don't overlap"""
    engine = DBLPackingEngine(3.0, 2.0, 2.0)
    
    pkg1 = Package("P1", 1.0, 0.5, 0.3, 10.0, 1)
    engine.placed_packages.append(
        PlacedPackage(pkg1, 0.0, 0.0, 0.0, 1.0, 0.5, 0.3)
    )
    
    pkg2 = Package("P2", 1.0, 0.5, 0.3, 10.0, 1)
    assert not engine._check_overlap(pkg2, 1.5, 0.0, 0.0)
    assert not engine._check_overlap(pkg2, 0.0, 1.0, 0.0)
    assert not engine._check_overlap(pkg2, 0.0, 0.0, 0.5)


def test_check_overlap_with_overlap():
    """Test overlap check when packages do overlap"""
    engine = DBLPackingEngine(3.0, 2.0, 2.0)
    
    pkg1 = Package("P1", 1.0, 1.0, 0.5, 10.0, 1)
    engine.placed_packages.append(
        PlacedPackage(pkg1, 0.0, 0.0, 0.0, 1.0, 1.0, 0.5)
    )
    
    pkg2 = Package("P2", 1.0, 1.0, 0.5, 10.0, 1)
    assert engine._check_overlap(pkg2, 0.5, 0.5, 0.0)
    assert engine._check_overlap(pkg2, 0.0, 0.0, 0.2)


def test_check_support_floor_placement():
    """Test that floor placement (z=0) is always supported"""
    engine = DBLPackingEngine(3.0, 2.0, 2.0)
    package = Package("P1", 1.0, 0.5, 0.3, 10.0, 1)
    
    assert engine._check_support(package, 0.0, 0.0, 0.0)
    assert engine._check_support(package, 1.0, 1.0, 0.0)


def test_check_support_full_support():
    """Test support check with 100% support"""
    engine = DBLPackingEngine(3.0, 2.0, 2.0)
    
    support_pkg = Package("P1", 1.0, 1.0, 0.5, 20.0, 1)
    engine.placed_packages.append(
        PlacedPackage(support_pkg, 0.0, 0.0, 0.0, 1.0, 1.0, 0.5)
    )
    
    top_pkg = Package("P2", 0.5, 0.5, 0.3, 5.0, 1)
    assert engine._check_support(top_pkg, 0.0, 0.0, 0.5)


def test_check_support_insufficient():
    """Test support check with less than 80% support"""
    engine = DBLPackingEngine(3.0, 2.0, 2.0)
    
    support_pkg = Package("P1", 0.5, 0.5, 0.5, 20.0, 1)
    engine.placed_packages.append(
        PlacedPackage(support_pkg, 0.0, 0.0, 0.0, 0.5, 0.5, 0.5)
    )
    
    top_pkg = Package("P2", 1.0, 1.0, 0.3, 5.0, 1)
    assert not engine._check_support(top_pkg, 0.0, 0.0, 0.5)


def test_check_weight_constraint_floor():
    """Test that floor placement has no weight constraint"""
    engine = DBLPackingEngine(3.0, 2.0, 2.0)
    
    heavy_pkg = Package("P1", 1.0, 0.5, 0.3, 100.0, 1)
    assert engine._check_weight_constraint(heavy_pkg, 0.0, 0.0, 0.0)


def test_check_weight_constraint_valid():
    """Test weight constraint with valid stacking (light on heavy)"""
    engine = DBLPackingEngine(3.0, 2.0, 2.0)
    
    heavy_pkg = Package("P1", 1.0, 1.0, 0.5, 20.0, 1)
    engine.placed_packages.append(
        PlacedPackage(heavy_pkg, 0.0, 0.0, 0.0, 1.0, 1.0, 0.5)
    )
    
    light_pkg = Package("P2", 0.5, 0.5, 0.3, 10.0, 1)
    assert engine._check_weight_constraint(light_pkg, 0.0, 0.0, 0.5)


def test_check_weight_constraint_invalid():
    """Test weight constraint with invalid stacking (heavy on light)"""
    engine = DBLPackingEngine(3.0, 2.0, 2.0)
    
    light_pkg = Package("P1", 1.0, 1.0, 0.5, 10.0, 1)
    engine.placed_packages.append(
        PlacedPackage(light_pkg, 0.0, 0.0, 0.0, 1.0, 1.0, 0.5)
    )
    
    heavy_pkg = Package("P2", 0.5, 0.5, 0.3, 20.0, 1)
    assert not engine._check_weight_constraint(heavy_pkg, 0.0, 0.0, 0.5)


def test_contact_point_generation():
    """Test that contact points are generated correctly from placed packages"""
    engine = DBLPackingEngine(3.0, 2.0, 2.0)
    
    engine.contact_points = [ContactPoint(0, 0, 0, 0)]
    
    pkg = Package("P1", 1.0, 0.5, 0.3, 10.0, 1)
    engine.placed_packages.append(
        PlacedPackage(pkg, 0.0, 0.0, 0.0, 1.0, 0.5, 0.3)
    )
    engine._update_contact_points(pkg, 0.0, 0.0, 0.0)
    
    assert len(engine.contact_points) == 3
    
    points_coords = [(cp.x, cp.y, cp.z) for cp in engine.contact_points]
    assert (1.0, 0.0, 0.0) in points_coords
    assert (0.0, 0.5, 0.0) in points_coords
    assert (0.0, 0.0, 0.3) in points_coords


def test_euclidean_distance_calculation():
    """Test Euclidean distance calculation"""
    engine = DBLPackingEngine(3.0, 2.0, 2.0)
    
    assert engine._euclidean_distance(0, 0, 0) == 0.0
    assert abs(engine._euclidean_distance(1, 0, 0) - 1.0) < 0.001
    assert abs(engine._euclidean_distance(3, 4, 0) - 5.0) < 0.001
    assert abs(engine._euclidean_distance(1, 1, 1) - math.sqrt(3)) < 0.001


def test_can_place_at_all_constraints():
    """Test integrated constraint validation"""
    engine = DBLPackingEngine(3.0, 2.0, 2.0)
    
    support_pkg = Package("P1", 1.0, 1.0, 0.5, 20.0, 1)
    engine.placed_packages.append(
        PlacedPackage(support_pkg, 0.0, 0.0, 0.0, 1.0, 1.0, 0.5)
    )
    
    valid_pkg = Package("P2", 0.8, 0.8, 0.3, 15.0, 1)
    assert engine._can_place_at(valid_pkg, 0.0, 0.0, 0.5)
    
    assert not engine._can_place_at(valid_pkg, 2.5, 0.0, 0.5)
    assert not engine._can_place_at(valid_pkg, 0.5, 0.5, 0.0)
    
    small_pkg = Package("P3", 1.5, 1.5, 0.3, 10.0, 1)
    assert not engine._can_place_at(small_pkg, 0.0, 0.0, 0.5)
    
    heavy_pkg = Package("P4", 0.8, 0.8, 0.3, 35.0, 1)
    assert not engine._can_place_at(heavy_pkg, 0.0, 0.0, 0.5)


def test_vehicle_validation_negative_length():
    """Test that negative vehicle length raises ValueError"""
    with pytest.raises(ValueError, match="Vehicle length must be positive"):
        DBLPackingEngine(-1.0, 2.0, 2.0)


def test_vehicle_validation_zero_width():
    """Test that zero vehicle width raises ValueError"""
    with pytest.raises(ValueError, match="Vehicle width must be positive"):
        DBLPackingEngine(3.0, 0.0, 2.0)


def test_vehicle_validation_negative_height():
    """Test that negative vehicle height raises ValueError"""
    with pytest.raises(ValueError, match="Vehicle height must be positive"):
        DBLPackingEngine(3.0, 2.0, -0.5)


def test_package_validation_negative_length():
    """Test that negative package length raises ValueError"""
    engine = DBLPackingEngine(3.0, 2.0, 2.0)
    invalid_pkg = Package("P1", -1.0, 0.5, 0.3, 10.0, 1)
    
    with pytest.raises(ValueError, match="P1.*length must be positive"):
        engine.pack_route([invalid_pkg])


def test_package_validation_zero_width():
    """Test that zero package width raises ValueError"""
    engine = DBLPackingEngine(3.0, 2.0, 2.0)
    invalid_pkg = Package("P1", 1.0, 0.0, 0.3, 10.0, 1)
    
    with pytest.raises(ValueError, match="P1.*width must be positive"):
        engine.pack_route([invalid_pkg])


def test_package_validation_negative_height():
    """Test that negative package height raises ValueError"""
    engine = DBLPackingEngine(3.0, 2.0, 2.0)
    invalid_pkg = Package("P1", 1.0, 0.5, -0.3, 10.0, 1)
    
    with pytest.raises(ValueError, match="P1.*height must be positive"):
        engine.pack_route([invalid_pkg])


def test_package_validation_zero_weight():
    """Test that zero package weight raises ValueError"""
    engine = DBLPackingEngine(3.0, 2.0, 2.0)
    invalid_pkg = Package("P1", 1.0, 0.5, 0.3, 0.0, 1)
    
    with pytest.raises(ValueError, match="P1.*weight must be positive"):
        engine.pack_route([invalid_pkg])


def test_package_validation_negative_weight():
    """Test that negative package weight raises ValueError"""
    engine = DBLPackingEngine(3.0, 2.0, 2.0)
    invalid_pkg = Package("P1", 1.0, 0.5, 0.3, -10.0, 1)
    
    with pytest.raises(ValueError, match="P1.*weight must be positive"):
        engine.pack_route([invalid_pkg])


def test_package_validation_invalid_stop_number():
    """Test that invalid stop number raises ValueError"""
    engine = DBLPackingEngine(3.0, 2.0, 2.0)
    invalid_pkg = Package("P1", 1.0, 0.5, 0.3, 10.0, 0)
    
    with pytest.raises(ValueError, match="P1.*stop number must be at least 1"):
        engine.pack_route([invalid_pkg])


def test_package_validation_negative_stop_number():
    """Test that negative stop number raises ValueError"""
    engine = DBLPackingEngine(3.0, 2.0, 2.0)
    invalid_pkg = Package("P1", 1.0, 0.5, 0.3, 10.0, -1)
    
    with pytest.raises(ValueError, match="P1.*stop number must be at least 1"):
        engine.pack_route([invalid_pkg])


def test_package_validation_valid_package():
    """Test that valid package passes validation"""
    engine = DBLPackingEngine(3.0, 2.0, 2.0)
    valid_pkg = Package("P1", 1.0, 0.5, 0.3, 10.0, 1)
    
    # Should not raise any exception
    result = engine.pack_route([valid_pkg])
    assert len(result.placed_packages) == 1


def test_failure_reason_too_large_volume():
    """Test failure reason for package with volume exceeding vehicle"""
    engine = DBLPackingEngine(1.0, 1.0, 1.0)
    large_pkg = Package("P1", 2.0, 2.0, 2.0, 10.0, 1)
    
    reason = engine._get_failure_reason(large_pkg)
    assert "too large for vehicle" in reason.lower()


def test_failure_reason_dimension_exceeds():
    """Test failure reason for package with dimension exceeding vehicle"""
    engine = DBLPackingEngine(3.0, 2.0, 2.0)
    tall_pkg = Package("P1", 0.5, 0.5, 3.0, 10.0, 1)
    
    reason = engine._get_failure_reason(tall_pkg)
    assert "dimension exceeds" in reason.lower()


def test_failure_reason_stability():
    """Test failure reason for package failing stability constraints"""
    engine = DBLPackingEngine(3.0, 2.0, 2.0)
    
    # Place a small package first
    small_pkg = Package("P1", 0.5, 0.5, 0.5, 10.0, 1)
    engine.placed_packages.append(
        PlacedPackage(small_pkg, 0.0, 0.0, 0.0, 0.5, 0.5, 0.5)
    )
    
    # Try to place a large package that would need more support
    large_pkg = Package("P2", 1.0, 1.0, 0.3, 5.0, 1)
    reason = engine._get_failure_reason(large_pkg)
    assert "stability" in reason.lower() or "weight" in reason.lower()


def test_calculate_utilization_empty():
    """Test utilization calculation with no packages"""
    engine = DBLPackingEngine(3.0, 2.0, 2.0)
    utilization = engine._calculate_utilization()
    assert utilization == 0.0


def test_calculate_utilization_partial():
    """Test utilization calculation with some packages"""
    engine = DBLPackingEngine(3.0, 2.0, 2.0)
    
    # Vehicle volume = 3 * 2 * 2 = 12 m³
    # Package volume = 1 * 1 * 1 = 1 m³
    # Utilization = 1/12 * 100 = 8.33%
    pkg = Package("P1", 1.0, 1.0, 1.0, 10.0, 1)
    engine.placed_packages.append(
        PlacedPackage(pkg, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0)
    )
    
    utilization = engine._calculate_utilization()
    expected = (1.0 / 12.0) * 100.0
    assert abs(utilization - expected) < 0.01


def test_calculate_utilization_full():
    """Test utilization calculation with full vehicle"""
    engine = DBLPackingEngine(2.0, 2.0, 2.0)
    
    # Fill entire vehicle with one package
    pkg = Package("P1", 2.0, 2.0, 2.0, 10.0, 1)
    engine.placed_packages.append(
        PlacedPackage(pkg, 0.0, 0.0, 0.0, 2.0, 2.0, 2.0)
    )
    
    utilization = engine._calculate_utilization()
    assert abs(utilization - 100.0) < 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
