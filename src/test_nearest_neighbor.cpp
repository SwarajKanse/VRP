#include "solver.h"
#include <iostream>
#include <iomanip>

int main() {
    std::cout << "Testing Nearest Neighbor Heuristic Implementation\n";
    std::cout << "==================================================\n\n";
    
    // Create a simple test case with depot and 3 customers
    Location depot_loc(40.7128, -74.0060);  // NYC
    Location customer1_loc(40.7589, -73.9851);  // Times Square
    Location customer2_loc(40.7614, -73.9776);  // Central Park
    Location customer3_loc(40.7484, -73.9857);  // Empire State Building
    
    std::vector<Customer> customers;
    customers.push_back(Customer(0, depot_loc, 0.0, 0.0, 48.0));  // Depot
    customers.push_back(Customer(1, customer1_loc, 10.0, 0.0, 24.0));
    customers.push_back(Customer(2, customer2_loc, 15.0, 0.0, 24.0));
    customers.push_back(Customer(3, customer3_loc, 8.0, 0.0, 24.0));
    
    // Create solver and solve
    VRPSolver solver;
    double vehicle_capacity = 50.0;
    
    std::cout << "Problem Setup:\n";
    std::cout << "  Customers: " << customers.size() - 1 << " (excluding depot)\n";
    std::cout << "  Vehicle Capacity: " << vehicle_capacity << "\n";
    std::cout << "  Total Demand: " << (10.0 + 15.0 + 8.0) << "\n\n";
    
    std::vector<Route> routes = solver.solve(customers, {vehicle_capacity});
    
    std::cout << "Solution:\n";
    std::cout << "  Number of routes: " << routes.size() << "\n\n";
    
    for (size_t i = 0; i < routes.size(); ++i) {
        std::cout << "  Route " << (i + 1) << ": ";
        for (size_t j = 0; j < routes[i].size(); ++j) {
            std::cout << routes[i][j];
            if (j < routes[i].size() - 1) {
                std::cout << " -> ";
            }
        }
        std::cout << "\n";
    }
    
    // Verify basic properties
    std::cout << "\nVerification:\n";
    
    // Check that all routes start and end at depot
    bool all_routes_valid = true;
    for (const auto& route : routes) {
        if (route.empty() || route.front() != 0 || route.back() != 0) {
            all_routes_valid = false;
            std::cout << "  ERROR: Route does not start and end at depot!\n";
        }
    }
    
    if (all_routes_valid) {
        std::cout << "  ✓ All routes start and end at depot\n";
    }
    
    // Check that all customers are visited
    std::vector<bool> visited(customers.size(), false);
    visited[0] = true;  // depot
    
    for (const auto& route : routes) {
        for (int customer_id : route) {
            if (customer_id > 0 && customer_id < static_cast<int>(customers.size())) {
                visited[customer_id] = true;
            }
        }
    }
    
    bool all_visited = true;
    for (size_t i = 1; i < visited.size(); ++i) {
        if (!visited[i]) {
            all_visited = false;
            std::cout << "  ERROR: Customer " << i << " was not visited!\n";
        }
    }
    
    if (all_visited) {
        std::cout << "  ✓ All customers visited\n";
    }
    
    std::cout << "\nTest completed successfully!\n";
    
    return 0;
}
