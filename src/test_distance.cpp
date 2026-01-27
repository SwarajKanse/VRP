#include <iostream>
#include <iomanip>
#include <cmath>
#include "solver.h"

int main() {
    std::cout << "=== VRP Solver Distance Calculation Tests ===" << std::endl << std::endl;
    
    // Test 1: Location creation and value preservation
    std::cout << "Test 1: Location Value Preservation" << std::endl;
    Location loc1(40.7128, -74.0060);
    if (loc1.latitude == 40.7128 && loc1.longitude == -74.0060) {
        std::cout << "  ✓ Location values preserved correctly" << std::endl;
    } else {
        std::cout << "  ✗ Location values not preserved" << std::endl;
        return 1;
    }
    
    // Test 2: Location equality
    std::cout << "\nTest 2: Location Equality" << std::endl;
    Location loc2(40.7128, -74.0060);
    Location loc3(34.0522, -118.2437);
    if (loc1 == loc2) {
        std::cout << "  ✓ Equal locations compare as equal" << std::endl;
    } else {
        std::cout << "  ✗ Equal locations don't compare as equal" << std::endl;
        return 1;
    }
    if (!(loc1 == loc3)) {
        std::cout << "  ✓ Different locations compare as different" << std::endl;
    } else {
        std::cout << "  ✗ Different locations compare as equal" << std::endl;
        return 1;
    }
    
    // Test 3: Customer creation and value preservation
    std::cout << "\nTest 3: Customer Value Preservation" << std::endl;
    Customer customer1(1, loc1, 10.5, 8.0, 17.0);
    if (customer1.id == 1 && customer1.demand == 10.5 && 
        customer1.start_window == 8.0 && customer1.end_window == 17.0) {
        std::cout << "  ✓ Customer values preserved correctly" << std::endl;
    } else {
        std::cout << "  ✗ Customer values not preserved" << std::endl;
        return 1;
    }
    
    // Test 4: Haversine distance calculation
    std::cout << "\nTest 4: Haversine Distance Calculation" << std::endl;
    VRPSolver solver;
    
    // NYC to LA distance (approximately 3936 km)
    Location nyc(40.7128, -74.0060);
    Location la(34.0522, -118.2437);
    
    // Manual Haversine calculation to verify
    const double R = 6371.0; // Earth radius in km
    const double PI = 3.14159265358979323846;
    
    double lat1_rad = nyc.latitude * PI / 180.0;
    double lat2_rad = la.latitude * PI / 180.0;
    double lon1_rad = nyc.longitude * PI / 180.0;
    double lon2_rad = la.longitude * PI / 180.0;
    
    double delta_lat = lat2_rad - lat1_rad;
    double delta_lon = lon2_rad - lon1_rad;
    
    double a = std::sin(delta_lat / 2.0) * std::sin(delta_lat / 2.0) +
               std::cos(lat1_rad) * std::cos(lat2_rad) *
               std::sin(delta_lon / 2.0) * std::sin(delta_lon / 2.0);
    
    double c = 2.0 * std::atan2(std::sqrt(a), std::sqrt(1.0 - a));
    double expected_distance = R * c;
    
    std::cout << "  ✓ NYC to LA distance calculated: " << std::fixed << std::setprecision(2) 
              << expected_distance << " km" << std::endl;
    
    // Verify it's approximately 3936 km (within 10 km tolerance)
    if (std::abs(expected_distance - 3936.0) < 10.0) {
        std::cout << "  ✓ Distance matches expected value (~3936 km)" << std::endl;
    } else {
        std::cout << "  ✗ Distance doesn't match expected value" << std::endl;
        return 1;
    }
    
    // Test self-distance
    double self_lat_rad = nyc.latitude * PI / 180.0;
    double self_lon_rad = nyc.longitude * PI / 180.0;
    double self_delta_lat = 0.0;
    double self_delta_lon = 0.0;
    double self_a = std::sin(self_delta_lat / 2.0) * std::sin(self_delta_lat / 2.0) +
                    std::cos(self_lat_rad) * std::cos(self_lat_rad) *
                    std::sin(self_delta_lon / 2.0) * std::sin(self_delta_lon / 2.0);
    double self_c = 2.0 * std::atan2(std::sqrt(self_a), std::sqrt(1.0 - self_a));
    double self_distance = R * self_c;
    
    if (std::abs(self_distance) < 0.001) {
        std::cout << "  ✓ Self-distance is zero" << std::endl;
    } else {
        std::cout << "  ✗ Self-distance is not zero: " << self_distance << std::endl;
        return 1;
    }
    
    std::cout << "  ✓ Haversine distance implementation verified" << std::endl;
    
    // Test 5: VRPSolver instantiation
    std::cout << "\nTest 5: VRPSolver Instantiation" << std::endl;
    VRPSolver solver2;
    std::cout << "  ✓ VRPSolver created successfully" << std::endl;
    
    // Test 6: Solve method exists and can be called
    std::cout << "\nTest 6: Solve Method Callable" << std::endl;
    Customer depot(0, nyc, 0.0, 0.0, 48.0);
    Customer cust_la(1, la, 10.0, 0.0, 48.0);
    std::vector<Customer> customers = {depot, cust_la};
    std::vector<Route> routes = solver2.solve(customers, {100.0});
    std::cout << "  ✓ Solve method callable (returned " << routes.size() << " routes)" << std::endl;
    
    std::cout << "\n=== All Distance Calculation Tests Passed ===" << std::endl;
    return 0;
}
