"""
Unit tests for CSV Parser module
"""

import os
import sys
import tempfile
import pytest

# Critical: Add DLL directories for MinGW runtime
os.add_dll_directory(r"C:\mingw64\bin")
os.add_dll_directory(os.path.abspath("build"))

# Add dashboard to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'dashboard'))

from csv_parser import CSVParser, Package, Destination


def create_temp_csv(content: str) -> str:
    """Helper to create temporary CSV file."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
        f.write(content)
        return f.name


def test_package_volume_calculation():
    """Test that Package.volume_m3 property calculates correctly."""
    package = Package(
        order_id="TEST001",
        source_name="Warehouse",
        destination_name="Customer",
        latitude=40.7128,
        longitude=-74.0060,
        length_m=0.5,
        width_m=0.4,
        height_m=0.3,
        weight_kg=10.0,
        fragile=False,
        this_side_up=False
    )
    
    expected_volume = 0.5 * 0.4 * 0.3
    assert abs(package.volume_m3 - expected_volume) < 0.0001


def test_valid_csv_parsing():
    """Test parsing a valid CSV file."""
    csv_content = """Order ID,Source Name,Destination Name,Latitude,Longitude,Length (cm),Width (cm),Height (cm),Weight (kg),Fragile,This Side Up
ORD001,Warehouse A,Customer 1,40.7128,-74.0060,50,40,30,15.5,Yes,No
ORD002,Warehouse A,Customer 2,40.7589,-73.9851,30,30,30,8.2,No,Yes"""
    
    csv_file = create_temp_csv(csv_content)
    
    try:
        parser = CSVParser()
        destinations, error = parser.parse_manifest(csv_file)
        
        assert error is None
        assert len(destinations) == 2
        
        # Check first destination
        dest1 = next(d for d in destinations if d.name == "Customer 1")
        assert dest1.latitude == 40.7128
        assert dest1.longitude == -74.0060
        assert len(dest1.packages) == 1
        assert dest1.total_weight_kg == 15.5
        
        # Check package details
        pkg1 = dest1.packages[0]
        assert pkg1.order_id == "ORD001"
        assert pkg1.source_name == "Warehouse A"
        assert pkg1.fragile == True
        assert pkg1.this_side_up == False
        assert abs(pkg1.length_m - 0.5) < 0.0001  # 50cm = 0.5m
        assert abs(pkg1.width_m - 0.4) < 0.0001   # 40cm = 0.4m
        assert abs(pkg1.height_m - 0.3) < 0.0001  # 30cm = 0.3m
        
    finally:
        os.unlink(csv_file)


def test_missing_required_columns():
    """Test error handling for missing required columns."""
    csv_content = """Order ID,Destination Name,Latitude,Longitude
ORD001,Customer 1,40.7128,-74.0060"""
    
    csv_file = create_temp_csv(csv_content)
    
    try:
        parser = CSVParser()
        destinations, error = parser.parse_manifest(csv_file)
        
        assert error is not None
        assert "Missing required columns" in error
        assert "Source Name" in error
        
    finally:
        os.unlink(csv_file)


def test_missing_optional_columns_default_to_no():
    """Test that missing optional columns default to 'No'."""
    csv_content = """Order ID,Source Name,Destination Name,Latitude,Longitude,Length (cm),Width (cm),Height (cm),Weight (kg)
ORD001,Warehouse,Customer,40.7128,-74.0060,50,40,30,15.5"""
    
    csv_file = create_temp_csv(csv_content)
    
    try:
        parser = CSVParser()
        destinations, error = parser.parse_manifest(csv_file)
        
        assert error is None
        assert len(destinations) == 1
        
        pkg = destinations[0].packages[0]
        assert pkg.fragile == False
        assert pkg.this_side_up == False
        
    finally:
        os.unlink(csv_file)


def test_invalid_latitude():
    """Test validation of latitude range."""
    csv_content = """Order ID,Source Name,Destination Name,Latitude,Longitude,Length (cm),Width (cm),Height (cm),Weight (kg)
ORD001,Warehouse,Customer,95.0,-74.0060,50,40,30,15.5"""
    
    csv_file = create_temp_csv(csv_content)
    
    try:
        parser = CSVParser()
        destinations, error = parser.parse_manifest(csv_file)
        
        assert error is not None
        assert "Latitude must be between -90 and 90" in error
        assert "95.0" in error
        
    finally:
        os.unlink(csv_file)


def test_invalid_longitude():
    """Test validation of longitude range."""
    csv_content = """Order ID,Source Name,Destination Name,Latitude,Longitude,Length (cm),Width (cm),Height (cm),Weight (kg)
ORD001,Warehouse,Customer,40.7128,-200.0,50,40,30,15.5"""
    
    csv_file = create_temp_csv(csv_content)
    
    try:
        parser = CSVParser()
        destinations, error = parser.parse_manifest(csv_file)
        
        assert error is not None
        assert "Longitude must be between -180 and 180" in error
        assert "-200.0" in error
        
    finally:
        os.unlink(csv_file)


def test_invalid_dimensions():
    """Test validation of positive dimensions."""
    csv_content = """Order ID,Source Name,Destination Name,Latitude,Longitude,Length (cm),Width (cm),Height (cm),Weight (kg)
ORD001,Warehouse,Customer,40.7128,-74.0060,-10,40,30,15.5"""
    
    csv_file = create_temp_csv(csv_content)
    
    try:
        parser = CSVParser()
        destinations, error = parser.parse_manifest(csv_file)
        
        assert error is not None
        assert "Length (cm) must be positive" in error
        
    finally:
        os.unlink(csv_file)


def test_invalid_weight():
    """Test validation of positive weight."""
    csv_content = """Order ID,Source Name,Destination Name,Latitude,Longitude,Length (cm),Width (cm),Height (cm),Weight (kg)
ORD001,Warehouse,Customer,40.7128,-74.0060,50,40,30,0"""
    
    csv_file = create_temp_csv(csv_content)
    
    try:
        parser = CSVParser()
        destinations, error = parser.parse_manifest(csv_file)
        
        assert error is not None
        assert "Weight (kg) must be positive" in error
        
    finally:
        os.unlink(csv_file)


def test_case_insensitive_boolean_parsing():
    """Test that boolean values are parsed case-insensitively."""
    csv_content = """Order ID,Source Name,Destination Name,Latitude,Longitude,Length (cm),Width (cm),Height (cm),Weight (kg),Fragile,This Side Up
ORD001,Warehouse,Customer 1,40.7128,-74.0060,50,40,30,15.5,YES,no
ORD002,Warehouse,Customer 2,40.7589,-73.9851,30,30,30,8.2,No,YES"""
    
    csv_file = create_temp_csv(csv_content)
    
    try:
        parser = CSVParser()
        destinations, error = parser.parse_manifest(csv_file)
        
        assert error is None
        
        dest1 = next(d for d in destinations if d.name == "Customer 1")
        pkg1 = dest1.packages[0]
        assert pkg1.fragile == True
        assert pkg1.this_side_up == False
        
        dest2 = next(d for d in destinations if d.name == "Customer 2")
        pkg2 = dest2.packages[0]
        assert pkg2.fragile == False
        assert pkg2.this_side_up == True
        
    finally:
        os.unlink(csv_file)


def test_weight_aggregation_by_destination():
    """Test that weights are correctly aggregated per destination."""
    csv_content = """Order ID,Source Name,Destination Name,Latitude,Longitude,Length (cm),Width (cm),Height (cm),Weight (kg)
ORD001,Warehouse,Customer 1,40.7128,-74.0060,50,40,30,10.0
ORD002,Warehouse,Customer 1,40.7128,-74.0060,30,30,30,5.0
ORD003,Warehouse,Customer 2,40.7589,-73.9851,40,40,40,8.0"""
    
    csv_file = create_temp_csv(csv_content)
    
    try:
        parser = CSVParser()
        destinations, error = parser.parse_manifest(csv_file)
        
        assert error is None
        assert len(destinations) == 2
        
        dest1 = next(d for d in destinations if d.name == "Customer 1")
        assert len(dest1.packages) == 2
        assert dest1.total_weight_kg == 15.0
        
        dest2 = next(d for d in destinations if d.name == "Customer 2")
        assert len(dest2.packages) == 1
        assert dest2.total_weight_kg == 8.0
        
    finally:
        os.unlink(csv_file)


def test_dimension_conversion_from_cm_to_meters():
    """Test that dimensions are correctly converted from cm to meters."""
    csv_content = """Order ID,Source Name,Destination Name,Latitude,Longitude,Length (cm),Width (cm),Height (cm),Weight (kg)
ORD001,Warehouse,Customer,40.7128,-74.0060,100,50,25,10.0"""
    
    csv_file = create_temp_csv(csv_content)
    
    try:
        parser = CSVParser()
        destinations, error = parser.parse_manifest(csv_file)
        
        assert error is None
        pkg = destinations[0].packages[0]
        
        assert abs(pkg.length_m - 1.0) < 0.0001   # 100cm = 1.0m
        assert abs(pkg.width_m - 0.5) < 0.0001    # 50cm = 0.5m
        assert abs(pkg.height_m - 0.25) < 0.0001  # 25cm = 0.25m
        
    finally:
        os.unlink(csv_file)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
