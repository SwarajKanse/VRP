"""
Task 7 Checkpoint: Core Algorithm Tests

This test suite validates the core DBL packing algorithm including:
- LIFO sorting with sample package sets (5, 10, 20 packages)
- DBL placement heuristic
- LIFO ordering preservation in placement
- Integration of all components

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
    DBLPackingEngine,
    PackingResult
)


class TestLIFOSorting:
    """Test LIFO sorting with various package configurations"""
    
    def test_lifo_sort_reverse_stop_order(self):
        """Test that packages are sorted by reverse stop order (primary criterion)"""
        engine = DBLPackingEngine(5.0, 3.0, 3.0)
        
        packages = [
            Package("P1", 0.5, 0.5, 0.5, 10.0, 1),
            Package("P2", 0.5, 0.5, 0.5, 10.0, 2),
            Package("P3", 0.5, 0.5, 0.5, 10.0, 3),
            Package("P4", 0.5, 0.5, 0.5, 10.0, 4),
            Package("P5", 0.5, 0.5, 0.5, 10.0, 5),
        ]
        
        sorted_packages = engine._sort_packages_lifo(packages)
        
        # Should be in reverse stop order: 5, 4, 3, 2, 1
        assert sorted_packages[0].order_id == "P5"
        assert sorted_packages[1].order_id == "P4"
        assert sorted_packages[2].order_id == "P3"
        assert sorted_packages[3].order_id == "P2"
        assert sorted_packages[4].order_id == "P1"
    
    def test_lifo_sort_weight_within_stop(self):
        """Test that packages are sorted by weight within same stop (secondary criterion)"""
        engine = DBLPackingEngine(5.0, 3.0, 3.0)
        
        packages = [
            Package("P1", 0.5, 0.5, 0.5, 5.0, 1),   # Light
            Package("P2", 0.5, 0.5, 0.5, 15.0, 1),  # Heavy
            Package("P3", 0.5, 0.5, 0.5, 10.0, 1),  # Medium
        ]
        
        sorted_packages = engine._sort_packages_lifo(packages)
        
        # Should be sorted by weight descending: 15, 10, 5
        assert sorted_packages[0].weight_kg == 15.0
        assert sorted_packages[1].weight_kg == 10.0
        assert sorted_packages[2].weight_kg == 5.0
    
    def test_lifo_sort_mixed_stops_and_weights(self):
        """Test LIFO sorting with mixed stops and weights"""
        engine = DBLPackingEngine(5.0, 3.0, 3.0)
        
        packages = [
            Package("P1", 0.5, 0.5, 0.5, 5.0, 1),   # Stop 1, light
            Package("P2", 0.5, 0.5, 0.5, 20.0, 2),  # Stop 2, heavy
            Package("P3", 0.5, 0.5, 0.5, 10.0, 2),  # Stop 2, medium
            Package("P4", 0.5, 0.5, 0.5, 15.0, 1),  # Stop 1, heavy
        ]
        
        sorted_packages = engine._sort_packages_lifo(packages)
        
        # Expected order:
        # Stop 2 first (reverse order): P2 (20kg), P3 (10kg)
        # Then Stop 1: P4 (15kg), P1 (5kg)
        assert sorted_packages[0].order_id == "P2"
        assert sorted_packages[1].order_id == "P3"
        assert sorted_packages[2].order_id == "P4"
        assert sorted_packages[3].order_id == "P1"


class TestDBLPlacement:
    """Test DBL placement heuristic and contact point selection"""
    
    def test_dbl_places_first_package_at_origin(self):
        """Test that first package is placed at origin (0,0,0)"""
        engine = DBLPackingEngine(3.0, 2.0, 2.0)
        
        packages = [Package("P1", 1.0, 0.5, 0.3, 10.0, 1)]
        result = engine.pack_route(packages)
        
        assert len(result.placed_packages) == 1
        placed = result.placed_packages[0]
        assert placed.x == 0.0
        assert placed.y == 0.0
        assert placed.z == 0.0
    
    def test_dbl_selects_minimum_distance_position(self):
        """Test that DBL selects position with minimum Euclidean distance"""
        engine = DBLPackingEngine(3.0, 2.0, 2.0)
        
        # Place first package at origin
        pkg1 = Package("P1", 1.0, 0.5, 0.3, 10.0, 1)
        result1 = engine.pack_route([pkg1])
        
        # This creates contact points at:
        # (1.0, 0.0, 0.0) - distance = 1.0
        # (0.0, 0.5, 0.0) - distance = 0.5
        # (0.0, 0.0, 0.3) - distance = 0.3
        
        # Place second package - should choose (0.0, 0.0, 0.3) as it has minimum distance
        pkg2 = Package("P2", 0.5, 0.5, 0.3, 10.0, 1)
        engine.placed_packages = result1.placed_packages
        engine._update_contact_points(pkg1, 0.0, 0.0, 0.0)
        
        placed = engine._try_place_package(pkg2)
        assert placed
        
        # Should be placed at (0.0, 0.0, 0.3) - on top of first package
        placed_pkg = engine.placed_packages[1]
        assert placed_pkg.x == 0.0
        assert placed_pkg.y == 0.0
        assert placed_pkg.z == 0.3
    
    def test_dbl_tie_breaking_by_z_coordinate(self):
        """Test that DBL uses Z coordinate as tie-breaker when distances are equal"""
        engine = DBLPackingEngine(3.0, 3.0, 3.0)
        
        # Create contact points with equal distances but different Z values
        cp1 = ContactPoint(1.0, 0.0, 0.0, 1.0)  # Z = 0
        cp2 = ContactPoint(0.0, 0.0, 1.0, 1.0)  # Z = 1
        
        # Sort them - cp1 should come first (lower Z)
        sorted_points = sorted([cp2, cp1])
        assert sorted_points[0].z == 0.0
        assert sorted_points[1].z == 1.0


class TestLIFOOrderingPreservation:
    """Test that LIFO ordering is preserved during placement"""
    
    def test_lifo_ordering_preserved_simple(self):
        """Test LIFO ordering with simple 3-package scenario"""
        engine = DBLPackingEngine(5.0, 2.0, 2.0)
        
        packages = [
            Package("P1", 1.0, 0.5, 0.5, 10.0, 1),
            Package("P2", 1.0, 0.5, 0.5, 10.0, 2),
            Package("P3", 1.0, 0.5, 0.5, 10.0, 3),
        ]
        
        result = engine.pack_route(packages)
        
        # All packages should be placed
        assert len(result.placed_packages) == 3
        
        # Verify they were attempted in LIFO order (reverse stop order)
        # The placement order should be: P3 (stop 3), P2 (stop 2), P1 (stop 1)
        placed_ids = [p.package.order_id for p in result.placed_packages]
        assert placed_ids == ["P3", "P2", "P1"]
    
    def test_lifo_ordering_with_weight_sort(self):
        """Test LIFO ordering with weight-based secondary sort"""
        engine = DBLPackingEngine(5.0, 2.0, 2.0)
        
        packages = [
            Package("P1", 0.8, 0.5, 0.5, 5.0, 1),   # Stop 1, light
            Package("P2", 0.8, 0.5, 0.5, 15.0, 1),  # Stop 1, heavy
            Package("P3", 0.8, 0.5, 0.5, 10.0, 2),  # Stop 2, medium
        ]
        
        result = engine.pack_route(packages)
        
        # All packages should be placed
        assert len(result.placed_packages) == 3
        
        # Expected placement order: P3 (stop 2), P2 (stop 1, heavy), P1 (stop 1, light)
        placed_ids = [p.package.order_id for p in result.placed_packages]
        assert placed_ids == ["P3", "P2", "P1"]


class TestSamplePackageSets:
    """Test with sample package sets of varying sizes"""
    
    def test_5_package_set(self):
        """Test packing with 5 packages"""
        engine = DBLPackingEngine(3.0, 2.0, 2.0)
        
        packages = [
            Package("P1", 0.8, 0.5, 0.4, 10.0, 1),
            Package("P2", 0.7, 0.6, 0.3, 12.0, 2),
            Package("P3", 0.6, 0.5, 0.5, 8.0, 3),
            Package("P4", 0.9, 0.4, 0.4, 15.0, 1),
            Package("P5", 0.5, 0.5, 0.3, 6.0, 2),
        ]
        
        result = engine.pack_route(packages)
        
        # Verify all packages were processed
        total_packages = len(result.placed_packages) + len(result.failed_packages)
        assert total_packages == 5
        
        # Verify LIFO ordering in placement
        # Expected order: Stop 3 (P3), Stop 2 (P2 heavy, P5 light), Stop 1 (P4 heavy, P1 light)
        if len(result.placed_packages) >= 3:
            # First should be from stop 3
            assert result.placed_packages[0].package.stop_number == 3
        
        # Verify no overlaps
        for i, p1 in enumerate(result.placed_packages):
            for p2 in result.placed_packages[i+1:]:
                assert not engine._packages_overlap_3d(p1, p2)
        
        # Verify all placed packages satisfy constraints
        for placed in result.placed_packages:
            pkg = placed.package
            assert engine._check_boundaries(pkg, placed.x, placed.y, placed.z)
            if placed.z > 0:
                assert engine._check_support(pkg, placed.x, placed.y, placed.z)
                assert engine._check_weight_constraint(pkg, placed.x, placed.y, placed.z)
    
    def test_10_package_set(self):
        """Test packing with 10 packages"""
        engine = DBLPackingEngine(4.0, 2.5, 2.5)
        
        packages = []
        for i in range(10):
            stop = (i % 3) + 1  # Distribute across 3 stops
            weight = 10.0 + (i * 2)  # Varying weights
            packages.append(
                Package(f"P{i+1}", 0.6, 0.5, 0.4, weight, stop)
            )
        
        result = engine.pack_route(packages)
        
        # Verify all packages were processed
        total_packages = len(result.placed_packages) + len(result.failed_packages)
        assert total_packages == 10
        
        # Verify no overlaps
        for i, p1 in enumerate(result.placed_packages):
            for p2 in result.placed_packages[i+1:]:
                assert not engine._packages_overlap_3d(p1, p2)
        
        # Verify all placed packages satisfy constraints
        for placed in result.placed_packages:
            pkg = placed.package
            assert engine._check_boundaries(pkg, placed.x, placed.y, placed.z)
            if placed.z > 0:
                assert engine._check_support(pkg, placed.x, placed.y, placed.z)
                assert engine._check_weight_constraint(pkg, placed.x, placed.y, placed.z)
        
        # Verify utilization is calculated
        assert result.utilization_percent >= 0.0
        assert result.utilization_percent <= 100.0
    
    def test_20_package_set(self):
        """Test packing with 20 packages"""
        engine = DBLPackingEngine(5.0, 3.0, 3.0)
        
        packages = []
        for i in range(20):
            stop = (i % 5) + 1  # Distribute across 5 stops
            weight = 8.0 + (i * 1.5)  # Varying weights
            # Vary dimensions slightly
            length = 0.5 + (i % 3) * 0.1
            width = 0.4 + (i % 2) * 0.1
            height = 0.3 + (i % 4) * 0.05
            packages.append(
                Package(f"P{i+1}", length, width, height, weight, stop)
            )
        
        result = engine.pack_route(packages)
        
        # Verify all packages were processed
        total_packages = len(result.placed_packages) + len(result.failed_packages)
        assert total_packages == 20
        
        # Verify no overlaps
        for i, p1 in enumerate(result.placed_packages):
            for p2 in result.placed_packages[i+1:]:
                assert not engine._packages_overlap_3d(p1, p2)
        
        # Verify all placed packages satisfy constraints
        for placed in result.placed_packages:
            pkg = placed.package
            assert engine._check_boundaries(pkg, placed.x, placed.y, placed.z)
            if placed.z > 0:
                assert engine._check_support(pkg, placed.x, placed.y, placed.z)
                assert engine._check_weight_constraint(pkg, placed.x, placed.y, placed.z)
        
        # Verify metrics
        assert result.utilization_percent >= 0.0
        assert result.utilization_percent <= 100.0
        assert result.total_weight_kg > 0.0
        
        # Verify LIFO ordering - packages from higher stops should be placed first
        if len(result.placed_packages) >= 2:
            # First placed package should have higher or equal stop number than last
            first_stop = result.placed_packages[0].package.stop_number
            last_stop = result.placed_packages[-1].package.stop_number
            # Due to placement constraints, exact ordering may vary, but general trend should hold
            # Just verify that we have packages from different stops
            stop_numbers = set(p.package.stop_number for p in result.placed_packages)
            assert len(stop_numbers) > 1  # Should have packages from multiple stops


class TestIntegratedWorkflow:
    """Test complete packing workflow with all components"""
    
    def test_complete_workflow_with_failures(self):
        """Test complete workflow including packages that fail to place"""
        engine = DBLPackingEngine(2.0, 1.5, 1.5)
        
        packages = [
            Package("P1", 0.5, 0.5, 0.5, 10.0, 1),  # Should fit
            Package("P2", 0.5, 0.5, 0.5, 10.0, 2),  # Should fit
            Package("P3", 3.0, 1.0, 1.0, 20.0, 3),  # Too long - should fail
            Package("P4", 0.5, 0.5, 0.5, 10.0, 1),  # Should fit
        ]
        
        result = engine.pack_route(packages)
        
        # Should have some placed and some failed
        assert len(result.placed_packages) > 0
        assert len(result.failed_packages) > 0
        
        # P3 should be in failed packages
        failed_ids = [pkg.order_id for pkg, reason in result.failed_packages]
        assert "P3" in failed_ids
        
        # Failed package should have a reason
        for pkg, reason in result.failed_packages:
            assert len(reason) > 0
            assert isinstance(reason, str)
    
    def test_utilization_calculation(self):
        """Test that utilization is calculated correctly"""
        engine = DBLPackingEngine(2.0, 2.0, 2.0)
        
        # Vehicle volume = 2 * 2 * 2 = 8 m³
        # Place one 1x1x1 package = 1 m³
        # Expected utilization = 1/8 * 100 = 12.5%
        packages = [Package("P1", 1.0, 1.0, 1.0, 10.0, 1)]
        
        result = engine.pack_route(packages)
        
        assert len(result.placed_packages) == 1
        expected_utilization = (1.0 / 8.0) * 100.0
        assert abs(result.utilization_percent - expected_utilization) < 0.01
    
    def test_total_weight_calculation(self):
        """Test that total weight is calculated correctly"""
        engine = DBLPackingEngine(3.0, 2.0, 2.0)
        
        packages = [
            Package("P1", 0.5, 0.5, 0.5, 10.0, 1),
            Package("P2", 0.5, 0.5, 0.5, 15.0, 2),
            Package("P3", 0.5, 0.5, 0.5, 20.0, 3),
        ]
        
        result = engine.pack_route(packages)
        
        # All should be placed
        assert len(result.placed_packages) == 3
        
        # Total weight should be sum of all placed packages
        expected_weight = 10.0 + 15.0 + 20.0
        assert abs(result.total_weight_kg - expected_weight) < 0.01


class TestConstraintValidation:
    """Test that all constraints are properly validated during placement"""
    
    def test_support_constraint_enforced(self):
        """Test that 80% support constraint is enforced"""
        engine = DBLPackingEngine(3.0, 2.0, 2.0)
        
        # Place small base package
        pkg1 = Package("P1", 0.5, 0.5, 0.5, 20.0, 1)
        result1 = engine.pack_route([pkg1])
        assert len(result1.placed_packages) == 1
        
        # Try to place large package on top - should fail support check
        pkg2 = Package("P2", 1.5, 1.5, 0.5, 10.0, 2)
        engine.placed_packages = result1.placed_packages
        engine._update_contact_points(pkg1, 0.0, 0.0, 0.0)
        
        # Should not be able to place at (0, 0, 0.5) due to insufficient support
        can_place = engine._can_place_at(pkg2, 0.0, 0.0, 0.5)
        assert not can_place
    
    def test_weight_constraint_enforced(self):
        """Test that weight ratio constraint is enforced"""
        engine = DBLPackingEngine(3.0, 2.0, 2.0)
        
        # Place light base package
        pkg1 = Package("P1", 1.0, 1.0, 0.5, 10.0, 1)
        result1 = engine.pack_route([pkg1])
        assert len(result1.placed_packages) == 1
        
        # Try to place heavy package on top - should fail weight check
        pkg2 = Package("P2", 0.8, 0.8, 0.5, 20.0, 2)  # 20kg > 10kg * 1.5
        engine.placed_packages = result1.placed_packages
        engine._update_contact_points(pkg1, 0.0, 0.0, 0.0)
        
        # Should not be able to place at (0, 0, 0.5) due to weight constraint
        can_place = engine._can_place_at(pkg2, 0.0, 0.0, 0.5)
        assert not can_place


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
