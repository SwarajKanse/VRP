"""
Tests for Manifest Builder Module

This module tests the generation of driver manifests in CSV and PDF formats
with stop-by-stop delivery instructions.
"""

import os
import sys
import pytest
import csv
import io

# Critical: Add DLL directories for MinGW runtime
if os.name == 'nt':
    os.add_dll_directory(r"C:\mingw64\bin")
    os.add_dll_directory(os.path.abspath("build"))

from dashboard.manifest_builder import ManifestBuilder
from dashboard.csv_parser import Package, Destination
from dashboard.financial_engine import RouteCost


class TestManifestBuilder:
    """Test suite for manifest builder functionality."""
    
    def test_manifest_builder_instantiation(self):
        """Test that ManifestBuilder can be instantiated."""
        builder = ManifestBuilder()
        assert builder is not None
    
    def test_format_special_handling_fragile_only(self):
        """Test special handling formatting for fragile packages."""
        builder = ManifestBuilder()
        
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
        
        result = builder._format_special_handling(package)
        assert result == "⚠️ FRAGILE"
    
    def test_format_special_handling_this_side_up_only(self):
        """Test special handling formatting for orientation-locked packages."""
        builder = ManifestBuilder()
        
        package = Package(
            order_id="ORD002",
            source_name="Warehouse A",
            destination_name="Customer 2",
            latitude=40.7589,
            longitude=-73.9851,
            length_m=0.3,
            width_m=0.3,
            height_m=0.3,
            weight_kg=8.2,
            fragile=False,
            this_side_up=True
        )
        
        result = builder._format_special_handling(package)
        assert result == "⬆️ THIS SIDE UP"
    
    def test_format_special_handling_both_constraints(self):
        """Test special handling formatting when both constraints apply."""
        builder = ManifestBuilder()
        
        package = Package(
            order_id="ORD003",
            source_name="Warehouse A",
            destination_name="Customer 3",
            latitude=40.7589,
            longitude=-73.9851,
            length_m=0.3,
            width_m=0.3,
            height_m=0.3,
            weight_kg=8.2,
            fragile=True,
            this_side_up=True
        )
        
        result = builder._format_special_handling(package)
        assert "⚠️ FRAGILE" in result
        assert "⬆️ THIS SIDE UP" in result
    
    def test_format_special_handling_no_constraints(self):
        """Test special handling formatting when no constraints apply."""
        builder = ManifestBuilder()
        
        package = Package(
            order_id="ORD004",
            source_name="Warehouse A",
            destination_name="Customer 4",
            latitude=40.7589,
            longitude=-73.9851,
            length_m=0.3,
            width_m=0.3,
            height_m=0.3,
            weight_kg=8.2,
            fragile=False,
            this_side_up=False
        )
        
        result = builder._format_special_handling(package)
        assert result == ""
    
    def test_generate_csv_basic(self):
        """Test CSV manifest generation with basic route."""
        builder = ManifestBuilder()
        
        # Create test packages
        package1 = Package(
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
        
        package2 = Package(
            order_id="ORD002",
            source_name="Warehouse B",
            destination_name="Customer 2",
            latitude=40.7589,
            longitude=-73.9851,
            length_m=0.3,
            width_m=0.3,
            height_m=0.3,
            weight_kg=8.2,
            fragile=False,
            this_side_up=True
        )
        
        # Create destinations
        dest1 = Destination(
            name="Customer 1",
            latitude=40.7128,
            longitude=-74.0060,
            total_weight_kg=15.5,
            packages=[package1]
        )
        
        dest2 = Destination(
            name="Customer 2",
            latitude=40.7589,
            longitude=-73.9851,
            total_weight_kg=8.2,
            packages=[package2]
        )
        
        # Create route (depot + 2 customers)
        route = [0, 1, 2]
        
        # Generate CSV
        csv_content = builder.generate_csv(route, [package1, package2], [dest1, dest2])
        
        # Parse CSV to verify structure
        reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(reader)
        
        # Verify header columns
        assert 'Stop' in reader.fieldnames
        assert 'Source Name' in reader.fieldnames
        assert 'Destination Name' in reader.fieldnames
        assert 'Order ID' in reader.fieldnames
        assert 'Dimensions' in reader.fieldnames
        assert 'Weight (kg)' in reader.fieldnames
        assert 'Special Handling' in reader.fieldnames
        
        # Verify row count (2 packages)
        assert len(rows) == 2
        
        # Verify first row
        assert rows[0]['Stop'] == '1'
        assert rows[0]['Source Name'] == 'Warehouse A'
        assert rows[0]['Destination Name'] == 'Customer 1'
        assert rows[0]['Order ID'] == 'ORD001'
        assert '50.0x40.0x30.0 cm' in rows[0]['Dimensions']
        assert '15.50' in rows[0]['Weight (kg)']
        assert '⚠️ FRAGILE' in rows[0]['Special Handling']
        
        # Verify second row
        assert rows[1]['Stop'] == '2'
        assert rows[1]['Source Name'] == 'Warehouse B'
        assert rows[1]['Destination Name'] == 'Customer 2'
        assert rows[1]['Order ID'] == 'ORD002'
        assert '⬆️ THIS SIDE UP' in rows[1]['Special Handling']
    
    def test_generate_csv_default_source_name(self):
        """Test CSV manifest defaults missing source name to 'Depot'."""
        builder = ManifestBuilder()
        
        # Create package with empty source name
        package = Package(
            order_id="ORD001",
            source_name="",
            destination_name="Customer 1",
            latitude=40.7128,
            longitude=-74.0060,
            length_m=0.5,
            width_m=0.4,
            height_m=0.3,
            weight_kg=15.5,
            fragile=False,
            this_side_up=False
        )
        
        dest = Destination(
            name="Customer 1",
            latitude=40.7128,
            longitude=-74.0060,
            total_weight_kg=15.5,
            packages=[package]
        )
        
        route = [0, 1]
        
        csv_content = builder.generate_csv(route, [package], [dest])
        reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(reader)
        
        # Verify source name defaults to "Depot"
        assert rows[0]['Source Name'] == 'Depot'
    
    def test_generate_pdf_basic(self):
        """Test PDF manifest generation produces valid PDF."""
        builder = ManifestBuilder()
        
        # Create test data
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
        
        dest = Destination(
            name="Customer 1",
            latitude=40.7128,
            longitude=-74.0060,
            total_weight_kg=15.5,
            packages=[package]
        )
        
        route_cost = RouteCost(
            route_id=1,
            vehicle_name="Truck A",
            distance_km=50.0,
            time_hours=2.5,
            fuel_efficiency_km_per_L=8.0,
            fuel_consumed_L=6.25,
            fuel_cost=12.50,
            labor_cost=50.00,
            total_cost=62.50
        )
        
        route = [0, 1]
        
        # Generate PDF
        pdf_bytes = builder.generate_pdf(route, [package], [dest], "Truck A", route_cost)
        
        # Verify PDF is generated (check PDF header)
        assert pdf_bytes is not None
        assert len(pdf_bytes) > 0
        assert pdf_bytes[:4] == b'%PDF'  # PDF file signature
    
    def test_generate_pdf_with_multiple_packages(self):
        """Test PDF manifest with multiple packages at different stops."""
        builder = ManifestBuilder()
        
        # Create multiple packages
        packages = []
        destinations = []
        
        for i in range(3):
            package = Package(
                order_id=f"ORD00{i+1}",
                source_name=f"Warehouse {chr(65+i)}",
                destination_name=f"Customer {i+1}",
                latitude=40.7128 + i * 0.01,
                longitude=-74.0060 + i * 0.01,
                length_m=0.5,
                width_m=0.4,
                height_m=0.3,
                weight_kg=10.0 + i * 5,
                fragile=(i % 2 == 0),
                this_side_up=(i % 2 == 1)
            )
            packages.append(package)
            
            dest = Destination(
                name=f"Customer {i+1}",
                latitude=40.7128 + i * 0.01,
                longitude=-74.0060 + i * 0.01,
                total_weight_kg=10.0 + i * 5,
                packages=[package]
            )
            destinations.append(dest)
        
        route_cost = RouteCost(
            route_id=1,
            vehicle_name="Truck A",
            distance_km=100.0,
            time_hours=4.0,
            fuel_efficiency_km_per_L=8.0,
            fuel_consumed_L=12.5,
            fuel_cost=25.00,
            labor_cost=80.00,
            total_cost=105.00
        )
        
        route = [0, 1, 2, 3]
        
        # Generate PDF
        pdf_bytes = builder.generate_pdf(route, packages, destinations, "Truck A", route_cost)
        
        # Verify PDF is valid
        assert pdf_bytes is not None
        assert len(pdf_bytes) > 0
        assert pdf_bytes[:4] == b'%PDF'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
