#include <iostream>
#include <iomanip>
#include "solver.h"

int main() {
    std::cout << "=== VRP Solver - C++ API Example ===" << std::endl;
    std::cout << std::endl;
    
    // Create sample customers for a delivery scenario
    // Customer 0 is the depot (warehouse)
    std::vector<Customer> customers;
    
    // Depot at coordinates (40.7128, -74.0060) - New York City
    customers.emplace_back(0, Location(40.7128, -74.0060), 0.0, 0.0, 24.0);
    
    // Customer 1: Brooklyn delivery
    customers.emplace_back(1, Location(40.6782, -73.9442), 15.0, 8.0, 12.0);
    
    // Customer 2: Queens delivery
    customers.emplace_back(2, Location(40.7282, -73.7949), 20.0, 9.0, 14.0);
    
    // Customer 3: Bronx delivery
    customers.emplace_back(3, Location(40.8448, -73.8648), 10.0, 10.0, 15.0);
    
    // Customer 4: Staten Island delivery
    customers.emplace_back(4, Location(40.5795, -74.1502), 25.0, 8.0, 13.0);
    
    // Customer 5: Manhattan delivery
    customers.emplace_back(5, Location(40.7589, -73.9851), 12.0, 11.0, 16.0);
    
    std::cout << "Created " << customers.size() << " customers (including depot)" << std::endl;
    std::cout << "Depot location: (" << customers[0].location.latitude 
              << ", " << customers[0].location.longitude << ")" << std::endl;
    std::cout << std::endl;
    
    // Display customer information
    std::cout << "Customer Details:" << std::endl;
    std::cout << std::setw(4) << "ID" 
              << std::setw(12) << "Latitude" 
              << std::setw(12) << "Longitude" 
              << std::setw(10) << "Demand" 
              << std::setw(12) << "Time Window" << std::endl;
    std::cout << std::string(50, '-') << std::endl;
    
    for (size_t i = 1; i < customers.size(); ++i) {
        const auto& c = customers[i];
        std::cout << std::setw(4) << c.id
                  << std::setw(12) << std::fixed << std::setprecision(4) << c.location.latitude
                  << std::setw(12) << std::fixed << std::setprecision(4) << c.location.longitude
                  << std::setw(10) << std::fixed << std::setprecision(1) << c.demand
                  << std::setw(6) << std::fixed << std::setprecision(1) << c.start_window
                  << " - " << std::setw(4) << std::fixed << std::setprecision(1) << c.end_window
                  << std::endl;
    }
    std::cout << std::endl;
    
    // Set vehicle capacities (heterogeneous fleet)
    std::vector<double> vehicle_capacities = {50.0, 50.0, 50.0};  // 3 vehicles with 50 units capacity each
    std::cout << "Fleet configuration: " << vehicle_capacities.size() << " vehicles" << std::endl;
    for (size_t i = 0; i < vehicle_capacities.size(); ++i) {
        std::cout << "  Vehicle " << (i + 1) << ": " << vehicle_capacities[i] << " units" << std::endl;
    }
    std::cout << std::endl;
    
    // Instantiate VRPSolver
    VRPSolver solver;
    std::cout << "VRPSolver instance created" << std::endl;
    
    // Solve the VRP
    std::cout << "Solving VRP using Nearest Neighbor heuristic..." << std::endl;
    auto routes = solver.solve(customers, vehicle_capacities);
    std::cout << "Solution found!" << std::endl;
    std::cout << std::endl;
    
    // Print the solution
    std::cout << "=== Solution ===" << std::endl;
    std::cout << "Number of routes: " << routes.size() << std::endl;
    std::cout << std::endl;
    
    for (size_t i = 0; i < routes.size(); ++i) {
        const auto& route = routes[i];
        double vehicle_capacity = vehicle_capacities[i];
        std::cout << "Route " << (i + 1) << " (Vehicle " << (i + 1) << " - Cap " << vehicle_capacity << "): ";
        
        // Calculate route load
        double route_load = 0.0;
        for (size_t j = 1; j < route.size() - 1; ++j) {  // Skip depot at start and end
            int customer_id = route[j];
            route_load += customers[customer_id].demand;
        }
        
        // Print route
        for (size_t j = 0; j < route.size(); ++j) {
            std::cout << route[j];
            if (j < route.size() - 1) {
                std::cout << " -> ";
            }
        }
        std::cout << " (Load: " << std::fixed << std::setprecision(1) << route_load << "/" << vehicle_capacity << ")" << std::endl;
    }
    std::cout << std::endl;
    
    // Calculate total customers served
    int total_served = 0;
    for (const auto& route : routes) {
        total_served += route.size() - 2;  // Exclude depot at start and end
    }
    
    std::cout << "Total customers served: " << total_served << " out of " << (customers.size() - 1) << std::endl;
    
    if (total_served < static_cast<int>(customers.size() - 1)) {
        std::cout << "Note: Some customers could not be served due to constraints" << std::endl;
    }
    
    std::cout << std::endl;
    std::cout << "=== Example Complete ===" << std::endl;
    
    return 0;
}
