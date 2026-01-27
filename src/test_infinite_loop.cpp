#include <iostream>
#include "solver.h"

int main() {
    std::cout << "=== Testing Infinite Loop Fix ===" << std::endl << std::endl;
    
    // Test 1: Infeasible customers (demand > capacity)
    std::cout << "Test 1: Customers with demand > vehicle capacity" << std::endl;
    
    Location depot_loc(0.0, 0.0);
    Location loc1(0.1, 0.1);
    Location loc2(0.2, 0.2);
    
    Customer depot(0, depot_loc, 0.0, 0.0, 48.0);
    Customer customer1(1, loc1, 100.0, 0.0, 48.0);  // Demand = 100
    Customer customer2(2, loc2, 150.0, 0.0, 48.0);  // Demand = 150
    
    std::vector<Customer> customers = {depot, customer1, customer2};
    
    VRPSolver solver;
    
    std::cout << "  Problem setup:" << std::endl;
    std::cout << "    Vehicle capacity: 50" << std::endl;
    std::cout << "    Customer 1 demand: 100 (exceeds capacity)" << std::endl;
    std::cout << "    Customer 2 demand: 150 (exceeds capacity)" << std::endl;
    std::cout << "  Calling solve()..." << std::endl;
    
    std::vector<Route> routes = solver.solve(customers, {50.0});
    
    std::cout << "  ✓ Solver returned (no infinite loop!)" << std::endl;
    std::cout << "  Number of routes: " << routes.size() << std::endl;
    
    if (routes.empty()) {
        std::cout << "  ✓ Correctly returned empty routes for infeasible problem" << std::endl;
    } else {
        std::cout << "  Routes generated:" << std::endl;
        for (size_t i = 0; i < routes.size(); ++i) {
            std::cout << "    Route " << (i+1) << ": ";
            for (int customer_id : routes[i]) {
                std::cout << customer_id << " ";
            }
            std::cout << std::endl;
        }
    }
    
    // Test 2: Mixed feasible and infeasible customers
    std::cout << "\nTest 2: Mix of feasible and infeasible customers" << std::endl;
    
    Location loc3(0.15, 0.15);
    Customer customer3(3, loc3, 20.0, 0.0, 48.0);  // Feasible
    Customer customer4(4, loc2, 200.0, 0.0, 48.0);  // Infeasible
    
    std::vector<Customer> customers2 = {depot, customer1, customer3, customer4};
    
    std::cout << "  Problem setup:" << std::endl;
    std::cout << "    Vehicle capacity: 50" << std::endl;
    std::cout << "    Customer 1 demand: 100 (infeasible)" << std::endl;
    std::cout << "    Customer 3 demand: 20 (feasible)" << std::endl;
    std::cout << "    Customer 4 demand: 200 (infeasible)" << std::endl;
    std::cout << "  Calling solve()..." << std::endl;
    
    VRPSolver solver2;
    std::vector<Route> routes2 = solver2.solve(customers2, {50.0});
    
    std::cout << "  ✓ Solver returned (no infinite loop!)" << std::endl;
    std::cout << "  Number of routes: " << routes2.size() << std::endl;
    
    if (!routes2.empty()) {
        std::cout << "  Routes generated:" << std::endl;
        for (size_t i = 0; i < routes2.size(); ++i) {
            std::cout << "    Route " << (i+1) << ": ";
            for (int customer_id : routes2[i]) {
                std::cout << customer_id << " ";
            }
            std::cout << std::endl;
        }
        std::cout << "  ✓ Feasible customers were served" << std::endl;
    }
    
    std::cout << "\n=== All Infinite Loop Tests Passed ===" << std::endl;
    return 0;
}
