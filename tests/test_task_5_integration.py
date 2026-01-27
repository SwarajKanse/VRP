"""
Integration tests for Task 5: LIFO sorting and DBL placement algorithm

These tests verify the complete pack_route workflow including:
- LIFO sorting (reverse stop order with weight secondary sort)
- DBL placement algorithm
- Contact point generation and management
- Failure handling and diagnostics
"""

import sys
import os

# Add dashboard to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'dashboard'))

from packing_engine_dbl import Package, DBLPackingEngine, ContactPoint


def test_lifo_sorting_primary_stop_order():
    """Test that packages are sorted by reverse stop order (primary criterion)"""
    engine = DBLPackingEngine(3.0, 2.0, 2.0)
    
    packages = [
        Package("P1", 0.5, 0.5, 0.5, 10.0, 1, False, False),
        Package("P2", 0.5, 0.5, 0.5, 10.0, 3, False, False),
        Package("P3", 0.5, 0.5, 0.5, 10.0, 2, False, False),
    ]
    
    sorted_packages = engine._sort_packages_lifo(packages)
    
    # Should be ordered: Stop 3, Stop 2, Stop 1
    assert sorted_packages[0].stop_number == 3
    assert sorted_packages[1].stop_number == 2
    assert sorted_packages[2].stop_number == 1


def test_lifo_sorting_secondary_weight():
    """Test that packages with same stop are sorted by weight (secondary criterion)"""
    engine = DBLPackingEngine(3.0, 2.0, 2.0)
    
    packages = [
        Package("P1", 0.5, 0.5, 0.5, 10.0, 1, False, False),
        Package("P2", 0.5, 0.5, 0.5, 30.0, 1, False, False),
        Package("P3", 0.5, 0.5, 0.5, 20.0, 1, False, False),
    ]
    
    sorted_packages = engine._sort_packages_lifo(packages)
    
    # All same stop, should be ordered by weight descending
    assert sorted_packages[0].weight_kg == 30.0
    assert sorted_packages[1].weight_kg == 20.0
    assert sorted_packages[2].weight_kg == 10.0


def test_pack_route_empty_list():
    """Test pack_route with empty package list"""
    engine = DBLPackingEngine(3.0, 2.0, 2.0)
    
    result = engine.pack_route([])
    
    assert len(result.placed_packages) == 0
    assert len(result.failed_packages) == 0
    assert result.utilization_percent == 0.0
    assert result.total_weight_kg == 0.0


def test_pack_route_single_package():
    """Test pack_route with single package"""
    engine = DBLPackingEngine(3.0, 2.0, 2.0)
    
    packages = [Package("P1", 1.0, 1.0, 1.0, 10.0, 1, False, False)]
    
    result = engine.pack_route(packages)
    
    assert len(result.placed_packages) == 1
    assert len(result.failed_packages) == 0
    assert result.placed_packages[0].x == 0.0
    assert result.placed_packages[0].y == 0.0
    assert result.placed_packages[0].z == 0.0
    assert result.total_weight_kg == 10.0


def test_pack_route_multiple_packages_lifo_order():
    """Test that pack_route respects LIFO ordering"""
    engine = DBLPackingEngine(3.0, 2.0, 2.0)
    
    packages = [
        Package("P1", 0.5, 0.5, 0.5, 10.0, 1, False, False),
        Package("P2", 0.5, 0.5, 0.5, 15.0, 2, False, False),
        Package("P3", 0.5, 0.5, 0.5, 20.0, 3, False, False),
    ]
    
    result = engine.pack_route(packages)
    
    # All should be placed
    assert len(result.placed_packages) == 3
    assert len(result.failed_packages) == 0
    
    # First placed should be from Stop 3 (LIFO)
    assert result.placed_packages[0].package.stop_number == 3
    assert result.placed_packages[1].package.stop_number == 2
    assert result.placed_packages[2].package.stop_number == 1


def test_pack_route_dbl_placement():
    """Test that packages are placed using DBL heuristic (closest to origin)"""
    engine = DBLPackingEngine(3.0, 2.0, 2.0)
    
    packages = [
        Package("P1", 1.0, 1.0, 1.0, 10.0, 1, False, False),
        Package("P2", 0.5, 0.5, 0.5, 5.0, 1, False, False),
    ]
    
    result = engine.pack_route(packages)
    
    assert len(result.placed_packages) == 2
    
    # First package should be at origin
    assert result.placed_packages[0].x == 0.0
    assert result.placed_packages[0].y == 0.0
    assert result.placed_packages[0].z == 0.0
    
    # Second package should be placed at one of the contact points
    # (could be right, front, or top of first package)
    p2 = result.placed_packages[1]
    # Should be at one of: (1.0, 0, 0), (0, 1.0, 0), or (0, 0, 1.0)
    valid_positions = [
        (1.0, 0.0, 0.0),  # Right
        (0.0, 1.0, 0.0),  # Front
        (0.0, 0.0, 1.0),  # Top
    ]
    assert (p2.x, p2.y, p2.z) in valid_positions


def test_pack_route_oversized_package():
    """Test pack_route with package that exceeds vehicle dimensions"""
    engine = DBLPackingEngine(2.0, 2.0, 2.0)
    
    packages = [
        Package("P1", 3.0, 1.0, 1.0, 10.0, 1, False, False),  # Too long
    ]
    
    result = engine.pack_route(packages)
    
    assert len(result.placed_packages) == 0
    assert len(result.failed_packages) == 1
    
    failed_package, reason = result.failed_packages[0]
    assert failed_package.order_id == "P1"
    assert "dimension exceeds" in reason.lower()


def test_pack_route_utilization_calculation():
    """Test that utilization is calculated correctly"""
    engine = DBLPackingEngine(2.0, 2.0, 2.0)  # 8 m³ total
    
    packages = [
        Package("P1", 1.0, 1.0, 1.0, 10.0, 1, False, False),  # 1 m³
        Package("P2", 1.0, 1.0, 1.0, 10.0, 1, False, False),  # 1 m³
    ]
    
    result = engine.pack_route(packages)
    
    # 2 m³ used out of 8 m³ = 25%
    expected_utilization = (2.0 / 8.0) * 100.0
    assert abs(result.utilization_percent - expected_utilization) < 0.01


def test_pack_route_total_weight():
    """Test that total weight is calculated correctly"""
    engine = DBLPackingEngine(3.0, 2.0, 2.0)
    
    packages = [
        Package("P1", 0.5, 0.5, 0.5, 10.0, 1, False, False),
        Package("P2", 0.5, 0.5, 0.5, 15.0, 1, False, False),
        Package("P3", 0.5, 0.5, 0.5, 20.0, 1, False, False),
    ]
    
    result = engine.pack_route(packages)
    
    assert result.total_weight_kg == 45.0


def test_pack_route_contact_point_initialization():
    """Test that contact points are initialized with origin"""
    engine = DBLPackingEngine(3.0, 2.0, 2.0)
    
    packages = [Package("P1", 1.0, 1.0, 1.0, 10.0, 1, False, False)]
    
    # Before packing, contact_points might be empty or stale
    result = engine.pack_route(packages)
    
    # After packing one package, should have 3 contact points
    # (origin removed, 3 new ones added from the placed package)
    assert len(engine.contact_points) == 3


def test_pack_route_mixed_success_and_failure():
    """Test pack_route with some packages that fit and some that don't"""
    engine = DBLPackingEngine(2.0, 2.0, 2.0)
    
    packages = [
        Package("P1", 1.0, 1.0, 1.0, 10.0, 1, False, False),  # Fits
        Package("P2", 3.0, 1.0, 1.0, 15.0, 2, False, False),  # Too long
        Package("P3", 0.5, 0.5, 0.5, 5.0, 1, False, False),   # Fits
    ]
    
    result = engine.pack_route(packages)
    
    # P2 should fail (tried first due to Stop 2), P1 and P3 should succeed
    assert len(result.placed_packages) == 2
    assert len(result.failed_packages) == 1
    
    placed_ids = {p.package.order_id for p in result.placed_packages}
    assert "P1" in placed_ids
    assert "P3" in placed_ids
    
    failed_package, _ = result.failed_packages[0]
    assert failed_package.order_id == "P2"


def test_pack_route_respects_support_constraint():
    """Test that pack_route respects 80% support constraint"""
    engine = DBLPackingEngine(3.0, 2.0, 2.0)
    
    # Place a small package first, then try to place a large package on top
    # The large package should fail support check if not enough support
    packages = [
        Package("P1", 0.3, 0.3, 0.5, 10.0, 2, False, False),  # Small base
        Package("P2", 1.0, 1.0, 0.5, 5.0, 1, False, False),   # Large base
    ]
    
    result = engine.pack_route(packages)
    
    # P1 placed first (Stop 2), P2 should be placed on floor or elsewhere
    # Both should fit since vehicle is large enough
    assert len(result.placed_packages) == 2
    
    # P2 should be on floor (z=0) since it can't be supported by small P1
    p2_placed = [p for p in result.placed_packages if p.package.order_id == "P2"][0]
    assert p2_placed.z == 0.0


def test_pack_route_respects_weight_constraint():
    """Test that pack_route respects weight constraint (1.5x ratio)"""
    engine = DBLPackingEngine(3.0, 2.0, 2.0)
    
    # Try to place heavy package on light package
    packages = [
        Package("P1", 1.0, 1.0, 0.5, 10.0, 2, False, False),   # Light, placed first
        Package("P2", 1.0, 1.0, 0.5, 20.0, 1, False, False),   # Heavy (2x weight)
    ]
    
    result = engine.pack_route(packages)
    
    # Both should be placed, but P2 should not be on top of P1
    # (weight ratio 20/10 = 2.0 > 1.5)
    assert len(result.placed_packages) == 2
    
    # P2 should be on floor or at a different location
    p2_placed = [p for p in result.placed_packages if p.package.order_id == "P2"][0]
    # Either on floor, or not directly above P1
    if p2_placed.z > 0:
        # If not on floor, should not be at z=0.5 (on top of P1)
        assert p2_placed.z != 0.5


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
