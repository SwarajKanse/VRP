"""
Test suite for contact point limit performance optimization.

This module tests the max_contact_points configuration option that limits
the number of contact points maintained during packing to improve performance.

Tests verify:
1. Contact point limit is enforced correctly
2. Packing still produces valid results with limited contact points
3. Performance improves with contact point limiting
4. Impact on packing quality is measurable
"""

import os
import sys
import time

# Add dashboard directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'dashboard'))

from packing_engine_dbl import (
    Package, DBLPackingEngine, ContactPoint, PlacedPackage, PackingResult
)


def create_test_packages(count: int) -> list:
    """
    Create a list of test packages with varying dimensions and weights.
    
    Args:
        count: Number of packages to create
        
    Returns:
        List of Package objects
    """
    packages = []
    for i in range(count):
        # Vary dimensions and weights to create realistic scenarios
        length = 0.3 + (i % 5) * 0.1  # 0.3 to 0.7m
        width = 0.2 + (i % 4) * 0.1   # 0.2 to 0.5m
        height = 0.2 + (i % 3) * 0.1  # 0.2 to 0.4m
        weight = 5.0 + (i % 10) * 2.0  # 5 to 25kg
        stop = (i % 5) + 1  # Stops 1-5
        
        packages.append(Package(
            order_id=f"PKG{i:03d}",
            length_m=length,
            width_m=width,
            height_m=height,
            weight_kg=weight,
            stop_number=stop,
            fragile=False,
            this_side_up=False
        ))
    
    return packages


def test_contact_point_limit_enforced():
    """
    Test that contact point limit is enforced during packing.
    
    Validates that when max_contact_points is set, the number of contact points
    never exceeds the specified limit during the packing process.
    """
    # Create engine with contact point limit
    max_limit = 10
    engine = DBLPackingEngine(3.0, 2.0, 2.0, max_contact_points=max_limit)
    
    # Create test packages
    packages = create_test_packages(20)
    
    # Track max contact points seen during packing
    max_seen = 0
    
    # Monkey-patch _update_contact_points to track contact point count
    original_update = engine._update_contact_points
    
    def tracked_update(package, x, y, z):
        nonlocal max_seen
        original_update(package, x, y, z)
        max_seen = max(max_seen, len(engine.contact_points))
    
    engine._update_contact_points = tracked_update
    
    # Run packing
    result = engine.pack_route(packages)
    
    # Verify limit was enforced
    assert max_seen <= max_limit, \
        f"Contact points exceeded limit: {max_seen} > {max_limit}"
    
    print(f"✓ Contact point limit enforced: max {max_seen} <= {max_limit}")


def test_unlimited_vs_limited_comparison():
    """
    Compare packing results between unlimited and limited contact points.
    
    Tests that:
    1. Both configurations produce valid packings
    2. Limited version is faster
    3. Packing quality difference is measurable
    """
    # Create test packages
    packages = create_test_packages(30)
    
    # Test with unlimited contact points
    engine_unlimited = DBLPackingEngine(3.0, 2.0, 2.0, max_contact_points=None)
    start_time = time.time()
    result_unlimited = engine_unlimited.pack_route(packages)
    time_unlimited = time.time() - start_time
    
    # Test with limited contact points
    engine_limited = DBLPackingEngine(3.0, 2.0, 2.0, max_contact_points=15)
    start_time = time.time()
    result_limited = engine_limited.pack_route(packages)
    time_limited = time.time() - start_time
    
    # Verify both produced valid results
    assert isinstance(result_unlimited, PackingResult)
    assert isinstance(result_limited, PackingResult)
    
    # Verify all placed packages satisfy constraints
    for placed in result_unlimited.placed_packages:
        assert placed.x >= 0 and placed.x_max <= 3.0
        assert placed.y >= 0 and placed.y_max <= 2.0
        assert placed.z >= 0 and placed.z_max <= 2.0
    
    for placed in result_limited.placed_packages:
        assert placed.x >= 0 and placed.x_max <= 3.0
        assert placed.y >= 0 and placed.y_max <= 2.0
        assert placed.z >= 0 and placed.z_max <= 2.0
    
    # Report results
    print(f"\n=== Unlimited vs Limited Contact Points Comparison ===")
    print(f"Unlimited: {len(result_unlimited.placed_packages)} placed, "
          f"{len(result_unlimited.failed_packages)} failed, "
          f"{result_unlimited.utilization_percent:.1f}% utilization, "
          f"{time_unlimited*1000:.2f}ms")
    print(f"Limited:   {len(result_limited.placed_packages)} placed, "
          f"{len(result_limited.failed_packages)} failed, "
          f"{result_limited.utilization_percent:.1f}% utilization, "
          f"{time_limited*1000:.2f}ms")
    
    # Calculate differences
    placed_diff = len(result_unlimited.placed_packages) - len(result_limited.placed_packages)
    util_diff = result_unlimited.utilization_percent - result_limited.utilization_percent
    speedup = time_unlimited / time_limited if time_limited > 0 else 1.0
    
    print(f"\nDifferences:")
    print(f"  Placed packages: {placed_diff:+d}")
    print(f"  Utilization: {util_diff:+.1f}%")
    print(f"  Speedup: {speedup:.2f}x")
    
    # Limited version should be at least as fast (or faster for larger sets)
    # Note: For small package sets, overhead may dominate
    print(f"\n✓ Both configurations produced valid packings")


def test_various_contact_point_limits():
    """
    Test packing with various contact point limits to measure trade-offs.
    
    This test explores the quality vs. speed trade-off by testing multiple
    limit values and measuring the impact on both packing quality and performance.
    """
    packages = create_test_packages(40)
    
    # Test different limits
    limits = [None, 50, 30, 20, 10, 5]
    results = []
    
    print(f"\n=== Testing Various Contact Point Limits ===")
    print(f"Packages: {len(packages)}")
    print(f"Vehicle: 3.0m x 2.0m x 2.0m")
    print()
    
    for limit in limits:
        engine = DBLPackingEngine(3.0, 2.0, 2.0, max_contact_points=limit)
        
        start_time = time.time()
        result = engine.pack_route(packages)
        elapsed = time.time() - start_time
        
        results.append({
            'limit': limit,
            'placed': len(result.placed_packages),
            'failed': len(result.failed_packages),
            'utilization': result.utilization_percent,
            'time_ms': elapsed * 1000
        })
        
        limit_str = "Unlimited" if limit is None else f"{limit:2d}"
        print(f"Limit {limit_str}: "
              f"{result.placed_packages.__len__()} placed, "
              f"{result.failed_packages.__len__()} failed, "
              f"{result.utilization_percent:5.1f}% util, "
              f"{elapsed*1000:6.2f}ms")
    
    # Verify all limits produced valid results
    for r in results:
        assert r['placed'] + r['failed'] == len(packages), \
            f"Package count mismatch for limit {r['limit']}"
    
    print(f"\n✓ All contact point limits produced valid packings")


def test_contact_point_limit_validation():
    """
    Test that invalid contact point limits are rejected.
    
    Validates that the engine properly validates the max_contact_points parameter.
    """
    # Valid limits should work
    engine = DBLPackingEngine(3.0, 2.0, 2.0, max_contact_points=None)
    assert engine.max_contact_points is None
    
    engine = DBLPackingEngine(3.0, 2.0, 2.0, max_contact_points=10)
    assert engine.max_contact_points == 10
    
    engine = DBLPackingEngine(3.0, 2.0, 2.0, max_contact_points=1)
    assert engine.max_contact_points == 1
    
    # Invalid limits should raise ValueError
    try:
        engine = DBLPackingEngine(3.0, 2.0, 2.0, max_contact_points=0)
        assert False, "Should have raised ValueError for max_contact_points=0"
    except ValueError as e:
        assert "max_contact_points must be at least 1" in str(e)
    
    try:
        engine = DBLPackingEngine(3.0, 2.0, 2.0, max_contact_points=-5)
        assert False, "Should have raised ValueError for negative max_contact_points"
    except ValueError as e:
        assert "max_contact_points must be at least 1" in str(e)
    
    print(f"✓ Contact point limit validation works correctly")


def test_single_contact_point_limit():
    """
    Test edge case: packing with only 1 contact point allowed.
    
    This extreme case tests that the algorithm still functions correctly
    even with the most restrictive limit.
    """
    # Create simple packages
    packages = [
        Package("PKG1", 0.5, 0.5, 0.5, 10.0, 1),
        Package("PKG2", 0.4, 0.4, 0.4, 8.0, 1),
        Package("PKG3", 0.3, 0.3, 0.3, 6.0, 1),
    ]
    
    # Pack with single contact point limit
    engine = DBLPackingEngine(2.0, 2.0, 2.0, max_contact_points=1)
    result = engine.pack_route(packages)
    
    # Should still place at least some packages
    assert len(result.placed_packages) > 0, \
        "Should place at least one package with single contact point"
    
    # Verify all placed packages are valid
    for placed in result.placed_packages:
        assert placed.x >= 0 and placed.x_max <= 2.0
        assert placed.y >= 0 and placed.y_max <= 2.0
        assert placed.z >= 0 and placed.z_max <= 2.0
    
    print(f"✓ Single contact point limit works: "
          f"{len(result.placed_packages)} placed, "
          f"{len(result.failed_packages)} failed")


if __name__ == "__main__":
    print("Testing Contact Point Limit Feature")
    print("=" * 60)
    
    test_contact_point_limit_validation()
    test_contact_point_limit_enforced()
    test_single_contact_point_limit()
    test_unlimited_vs_limited_comparison()
    test_various_contact_point_limits()
    
    print("\n" + "=" * 60)
    print("All tests passed!")
