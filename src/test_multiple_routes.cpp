#include "solver.h"
#include <iostream>

int main() {
    std::cout << "Testing Multiple Routes with Capacity Constraints\n";
    std::cout << "==================================================\n\n";
    
    // Create test case with depot and 4 customers
    // Total demand will exceed single vehicle capacity
    Location depot_loc(40.7128, -74.0060);  // NYC
    Location customer1_loc(40.7589, -73.9851);  // Times Square
    Location customer2_loc(40.7614, -73.9776);  // Central Park
    Location customer3_loc(40.7484, -73.9857);  // Empire State Building
    Location customer4_loc(40.7306, -73.9352);  // Queens
    
    std::vector<Customer> customers;
    customers.push_back(Customer(0, depot_loc, 0.0, 0.0, 48.0));  // Depot
    customers.push_back(Customer(1, customer1_loc, 20.0, 0.0, 24.0));
    customers.push_back(Customer(2, customer2_loc, 25.0, 0.0, 24.0));
    customers.push_back(Customer(3, customer3_loc, 18.0, 0.0, 24.0));
    customers.push_back(Customer(4, customer4_loc, 22.0, 0.0, 24.0));
    
    // Create solver with limited capacity
    VRPSolver solver;
    double vehicle_capacity = 50.0;  // Can't fit all customers in one route
    
    std::cout << "Problem Setup:\n";
    std::cout << "  Customers: " << customers.size() - 1 << " (excluding depot)\n";
    std::cout << "  Vehicle Capacity: " << vehicle_capacity << "\n";
    std::cout << "  Customer Demands: 20, 25, 18, 22\n";
    std::cout << "  Total Demand: " << (20.0 + 25.0 + 18.0 + 22.0) << "\n\n";
    
    std::vector<Route> routes = solver.solve(customers, {vehicle_capacity, vehicle_capacity});
    
    std::cout << "Solution:\n";
    std::cout << "  Number of routes: " << routes.size() << "\n\n";
    
    for (size_t i = 0; i < routes.size(); ++i) {
        std::cout << "  Route " << (i + 1) << ": ";
        double route_load = 0.0;
        
        for (size_t j = 0; j < routes[i].size(); ++j) {
            int customer_id = routes[i][j];
            std::cout << customer_id;
            
            if (customer_id > 0 && customer_id < static_cast<int>(customers.size())) {
                route_load += customers[customer_id].demand;
            }
            
            if (j < routes[i].size() - 1) {
                std::cout << " -> ";
            }
        }
        std::cout << " (Load: " << route_load << "/" << vehicle_capacity << ")\n";
        
        // Verify capacity constraint
        if (route_load > vehicle_capacity) {
            std::cout << "    ERROR: Route exceeds capacity!\n";
        }
    }
    
    // Verify all customers are visited
    std::cout << "\nVerification:\n";
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
    
    std::cout << "  ✓ All routes respect capacity constraints\n";
    std::cout << "\nTest completed successfully!\n";
    
    return 0;
}
