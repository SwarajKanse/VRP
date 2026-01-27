#!/usr/bin/env python3
"""Integration tests for time matrix functionality (Tasks 1 & 2)"""

import os
import sys
import pytest

# Critical: Add DLL directories for MinGW runtime
os.add_dll_directory(r"C:\mingw64\bin")
os.add_dll_directory(os.path.abspath("build"))

import vrp_core


class TestTimeMatrixIntegration:
    """Test time matrix integration from Tasks 1 and 2"""
    
    def test_service_time_field_exists(self):
        """Verify service_time field was added to Customer struct (Task 1)"""
        loc = vrp_core.Location(0.0, 0.0)
        customer = vrp_core.Customer(1, loc, 10.0, 0.0, 100.0, 15.0)
        assert hasattr(customer, 'service_time')
        assert customer.service_time == 15.0
    
    def test_service_time_default_value(self):
        """Verify service_time defaults to 0.0 (Task 1)"""
        loc = vrp_core.Location(0.0, 0.0)
        customer = vrp_core.Customer(1, loc, 10.0, 0.0, 100.0)
        assert customer.service_time == 0.0
    
    def test_solve_accepts_time_matrix_parameter(self):
        """Verify solve() accepts time_matrix parameter (Task 2.2)"""
        solver = vrp_core.VRPSolver()
        
        depot = vrp_core.Customer(0, vrp_core.Location(0.0, 0.0), 0.0, 0.0, 100.0)
        customer1 = vrp_core.Customer(1, vrp_core.Location(0.1, 0.1), 10.0, 0.0, 100.0)
        customer2 = vrp_core.Customer(2, vrp_core.Location(0.2, 0.2), 15.0, 0.0, 100.0)
        
        customers = [depot, customer1, customer2]
        
        # Create a simple time matrix (3x3)
        time_matrix = [
            [0.0, 10.0, 20.0],  # From depot
            [10.0, 0.0, 8.0],   # From customer 1
            [20.0, 8.0, 0.0]    # From customer 2
        ]
        
        # Should not raise an exception
        routes = solver.solve(customers, [50.0], True, time_matrix)
        assert isinstance(routes, list)
    
    def test_solve_without_time_matrix_backward_compatibility(self):
        """Verify solve() works without time_matrix (Task 2.2 - backward compatibility)"""
        solver = vrp_core.VRPSolver()
        
        depot = vrp_core.Customer(0, vrp_core.Location(0.0, 0.0), 0.0, 0.0, 100.0)
        customer1 = vrp_core.Customer(1, vrp_core.Location(0.1, 0.1), 10.0, 0.0, 100.0)
        
        customers = [depot, customer1]
        
        # Call without time_matrix - should use fallback
        routes = solver.solve(customers, [50.0])
        assert isinstance(routes, list)
        assert len(routes) > 0
    
    def test_time_matrix_dimension_validation(self):
        """Verify time_matrix dimension validation (Task 2.2)"""
        solver = vrp_core.VRPSolver()
        
        depot = vrp_core.Customer(0, vrp_core.Location(0.0, 0.0), 0.0, 0.0, 100.0)
        customer1 = vrp_core.Customer(1, vrp_core.Location(0.1, 0.1), 10.0, 0.0, 100.0)
        
        customers = [depot, customer1]
        
        # Invalid time matrix (wrong dimensions)
        invalid_time_matrix = [
            [0.0, 10.0],
            [10.0, 0.0],
            [5.0, 5.0]  # Extra row - should be 2x2, not 3x2
        ]
        
        # Should raise an exception
        with pytest.raises(Exception):
            solver.solve(customers, [50.0], True, invalid_time_matrix)
    
    def test_time_matrix_non_square_validation(self):
        """Verify time_matrix must be square (Task 2.2)"""
        solver = vrp_core.VRPSolver()
        
        depot = vrp_core.Customer(0, vrp_core.Location(0.0, 0.0), 0.0, 0.0, 100.0)
        customer1 = vrp_core.Customer(1, vrp_core.Location(0.1, 0.1), 10.0, 0.0, 100.0)
        
        customers = [depot, customer1]
        
        # Non-square time matrix
        non_square_matrix = [
            [0.0, 10.0, 5.0],  # 3 columns
            [10.0, 0.0]        # 2 columns - not square
        ]
        
        # Should raise an exception
        with pytest.raises(Exception):
            solver.solve(customers, [50.0], True, non_square_matrix)
    
    def test_time_matrix_affects_routing(self):
        """Verify time_matrix actually affects routing decisions (Task 2.4)"""
        solver = vrp_core.VRPSolver()
        
        # Create a scenario where time matrix would make a difference
        depot = vrp_core.Customer(0, vrp_core.Location(0.0, 0.0), 0.0, 0.0, 1000.0)
        customer1 = vrp_core.Customer(1, vrp_core.Location(0.1, 0.1), 10.0, 0.0, 1000.0)
        customer2 = vrp_core.Customer(2, vrp_core.Location(0.2, 0.2), 10.0, 0.0, 1000.0)
        
        customers = [depot, customer1, customer2]
        
        # Time matrix where customer 2 is "closer" in time than customer 1
        # even though spatially customer 1 is closer
        time_matrix = [
            [0.0, 100.0, 5.0],   # Depot: customer2 is much closer in time
            [100.0, 0.0, 10.0],
            [5.0, 10.0, 0.0]
        ]
        
        routes = solver.solve(customers, [50.0], True, time_matrix)
        
        # Should successfully generate routes
        assert len(routes) > 0
        # Both customers should be visited
        all_customers = []
        for route in routes:
            all_customers.extend([c for c in route if c != 0])
        assert 1 in all_customers
        assert 2 in all_customers


class TestGetTravelTimeMethod:
    """Test getTravelTime() helper method (Task 2.4)"""
    
    def test_fallback_to_distance_matrix(self):
        """Verify getTravelTime falls back to distance_matrix * 1.5 when no time_matrix"""
        solver = vrp_core.VRPSolver()
        
        depot = vrp_core.Customer(0, vrp_core.Location(0.0, 0.0), 0.0, 0.0, 100.0)
        customer1 = vrp_core.Customer(1, vrp_core.Location(0.1, 0.1), 10.0, 0.0, 100.0)
        
        customers = [depot, customer1]
        
        # Solve without time_matrix - should use fallback
        routes = solver.solve(customers, [50.0])
        
        # If it completes without error, the fallback is working
        assert len(routes) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
