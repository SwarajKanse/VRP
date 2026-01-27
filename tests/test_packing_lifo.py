"""
Tests for LIFO Packing Engine Module

This module tests the Last-In-First-Out packing algorithm with
physics constraints including fragile handling and stability.
"""

import os
import sys
import pytest

# Critical: Add DLL directories for MinGW runtime
if os.name == 'nt':
    os.add_dll_directory(r"C:\mingw64\bin")
    os.add_dll_directory(os.path.abspath("build"))

from dashboard.csv_parser import Package


class TestLIFOPacking:
    """Test suite for LIFO packing functionality."""
    
    def test_package_creation_for_packing(self):
        """Test that Package objects can be created for packing tests."""
        package = Package(
            order_id="ORD001",
            source_name="Warehouse A",
            destination_name="Customer 1",
            latitude=40.7128,
            longitude=-74.0060,
            length_m=0.5,
            width_m=0.4,
            height_m=0.3,
            weight_kg=15.5,
            fragile=True,
            this_side_up=False
        )
        
        assert package.order_id == "ORD001"
        assert package.fragile is True
        assert package.this_side_up is False
    
    def test_package_volume_calculation(self):
        """Test package volume calculation."""
        package = Package(
            order_id="ORD002",
            source_name="Warehouse A",
            destination_name="Customer 2",
            latitude=40.7589,
            longitude=-73.9851,
            length_m=1.0,
            width_m=1.0,
            height_m=1.0,
            weight_kg=20.0,
            fragile=False,
            this_side_up=True
        )
        
        assert package.volume_m3 == 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
