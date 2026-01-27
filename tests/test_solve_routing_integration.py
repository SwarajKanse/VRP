"""
Unit tests for solve_routing() OSRM integration
Tests OSRM success path, fallback behavior, and DLL configuration preservation
"""

import pytest
import sys
import os
from unittest import mock
import pandas as pd

# Windows-specific DLL path fix
if os.name == 'nt':
    test_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(test_dir, '..'))
    build_path = os.path.join(project_root, 'build')
    
    # Critical: Add DLL directories for MinGW runtime
    os.add_dll_directory(r"C:\mingw64\bin")
    os.add_dll_directory(os.path.abspath(build_path))
    
    if os.path.exists(build_path):
        sys.path.insert(0, build_path)

try:
    import vrp_core
except ImportError as e:
    pytest.skip(
        f"vrp_core module not available: {e}. "
        "This may be due to missing C++ runtime DLLs on Windows.",
        allow_module_level=True
    )

# Import dashboard app functions
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'dashboard'))
from app import solve_routing, get_osrm_matrix, generate_time_matrix, dataframe_to_customers


class TestSolveRoutingIntegration:
    """Unit tests for solve_routing() OSRM integration"""
    
    @pytest.fixture
    def sample_dataframe(self):
        """Create a sample DataFrame with customer data"""
        return pd.DataFrame([
            {'id': 0, 'lat': 19.065, 'lon': 72.835, 'demand': 0, 'start_window': 0, 'end_window': 600, 'service_time': 0},
            {'id': 1, 'lat': 19.070, 'lon': 72.840, 'demand': 10, 'start_window': 0, 'end_window': 600, 'service_time': 10},
            {'id': 2, 'lat': 19.075, 'lon': 72.845, 'demand': 15, 'start_window': 0, 'end_window': 600, 'service_time': 10}
        ])
    
    def test_osrm_success_path(self, sample_dataframe):
        """
        Test OSRM success path: mock successful OSRM response, 
        verify matrix used and success message displayed
        Requirements: 2.1, 2.2, 6.1
        """
        # Create customers
        customers = dataframe_to_customers(sample_dataframe)
        
        # Mock OSRM response with a valid time matrix
        mock_time_matrix = [
            [0.0, 3.5, 7.0],
            [3.5, 0.0, 3.5],
            [7.0, 3.5, 0.0]
        ]
        
        # Mock streamlit success to capture success message
        with mock.patch('app.get_osrm_matrix', return_value=mock_time_matrix) as mock_osrm:
            with mock.patch('app.st.success') as mock_success:
                # Call solve_routing
                routes, execution_time, time_matrix = solve_routing(
                    customers,
                    vehicle_capacities=[50, 50],
                    df=sample_dataframe
                )
                
                # Verify OSRM was called
                mock_osrm.assert_called_once()
                
                # Verify success message was displayed
                mock_success.assert_called_once()
                call_args = str(mock_success.call_args)
                assert "OSRM" in call_args
                assert "real road network" in call_args or "✅" in call_args
                
                # Verify routes were generated
                assert routes is not None
                assert isinstance(routes, list)
                assert execution_time > 0
                assert time_matrix is not None
    
    def test_osrm_failure_fallback(self, sample_dataframe):
        """
        Test OSRM failure fallback: mock ConnectionError, 
        verify fallback to generate_time_matrix() and warning displayed
        Requirements: 3.1, 3.2, 3.3, 4.1, 4.2
        """
        # Create customers
        customers = dataframe_to_customers(sample_dataframe)
        
        # Mock OSRM to raise ConnectionError
        with mock.patch('app.get_osrm_matrix', side_effect=ConnectionError("Network error")) as mock_osrm:
            with mock.patch('app.st.warning') as mock_warning:
                with mock.patch('app.generate_time_matrix') as mock_fallback:
                    # Set up fallback to return a valid matrix
                    mock_fallback.return_value = [
                        [0.0, 3.5, 7.0],
                        [3.5, 0.0, 3.5],
                        [7.0, 3.5, 0.0]
                    ]
                    
                    # Call solve_routing
                    routes, execution_time, time_matrix = solve_routing(
                        customers,
                        vehicle_capacities=[50, 50],
                        df=sample_dataframe
                    )
                    
                    # Verify OSRM was attempted
                    mock_osrm.assert_called_once()
                    
                    # Verify fallback was called
                    mock_fallback.assert_called_once()
                    
                    # Verify warning message was displayed
                    mock_warning.assert_called_once()
                    call_args = str(mock_warning.call_args)
                    assert "OSRM" in call_args
                    assert "unavailable" in call_args or "⚠️" in call_args
                    assert "Haversine" in call_args
                    
                    # Verify routes were still generated
                    assert routes is not None
                    assert isinstance(routes, list)
                    assert execution_time > 0
                    assert time_matrix is not None
    
    def test_dll_configuration_preservation(self):
        """
        Test DLL configuration preservation: verify os.add_dll_directory() 
        calls remain unchanged in app.py
        Requirements: 4.1, 4.2
        """
        # Read app.py file
        app_path = os.path.join(os.path.dirname(__file__), '..', 'dashboard', 'app.py')
        with open(app_path, 'r', encoding='utf-8') as f:
            app_content = f.read()
        
        # Verify DLL configuration block exists
        assert 'os.add_dll_directory' in app_content, "DLL configuration missing from app.py"
        assert r'C:\mingw64\bin' in app_content, "MinGW DLL path missing from app.py"
        
        # Verify the DLL configuration is in the correct location (before imports)
        dll_config_index = app_content.find('os.add_dll_directory')
        vrp_import_index = app_content.find('import vrp_core')
        
        assert dll_config_index < vrp_import_index, \
            "DLL configuration should appear before vrp_core import"
    
    def test_osrm_timeout_fallback(self, sample_dataframe):
        """
        Test OSRM timeout triggers fallback
        Requirements: 3.1, 3.2, 3.5
        """
        import requests
        
        # Create customers
        customers = dataframe_to_customers(sample_dataframe)
        
        # Mock OSRM to raise Timeout
        with mock.patch('app.get_osrm_matrix', side_effect=requests.exceptions.Timeout("Request timeout")) as mock_osrm:
            with mock.patch('app.st.warning') as mock_warning:
                with mock.patch('app.generate_time_matrix') as mock_fallback:
                    # Set up fallback to return a valid matrix
                    mock_fallback.return_value = [
                        [0.0, 3.5, 7.0],
                        [3.5, 0.0, 3.5],
                        [7.0, 3.5, 0.0]
                    ]
                    
                    # Call solve_routing
                    routes, execution_time, time_matrix = solve_routing(
                        customers,
                        vehicle_capacities=[50, 50],
                        df=sample_dataframe
                    )
                    
                    # Verify fallback was triggered
                    mock_fallback.assert_called_once()
                    mock_warning.assert_called_once()
                    
                    # Verify routes were generated
                    assert routes is not None
                    assert time_matrix is not None
    
    def test_osrm_http_error_fallback(self, sample_dataframe):
        """
        Test OSRM HTTP error triggers fallback
        Requirements: 3.1, 3.2, 5.3
        """
        import requests
        
        # Create customers
        customers = dataframe_to_customers(sample_dataframe)
        
        # Mock OSRM to raise HTTPError
        with mock.patch('app.get_osrm_matrix', side_effect=requests.exceptions.HTTPError("404 Not Found")) as mock_osrm:
            with mock.patch('app.st.warning') as mock_warning:
                with mock.patch('app.generate_time_matrix') as mock_fallback:
                    # Set up fallback to return a valid matrix
                    mock_fallback.return_value = [
                        [0.0, 3.5, 7.0],
                        [3.5, 0.0, 3.5],
                        [7.0, 3.5, 0.0]
                    ]
                    
                    # Call solve_routing
                    routes, execution_time, time_matrix = solve_routing(
                        customers,
                        vehicle_capacities=[50, 50],
                        df=sample_dataframe
                    )
                    
                    # Verify fallback was triggered
                    mock_fallback.assert_called_once()
                    mock_warning.assert_called_once()
                    
                    # Verify routes were generated
                    assert routes is not None
                    assert time_matrix is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
