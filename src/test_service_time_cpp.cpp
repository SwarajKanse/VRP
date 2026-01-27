#include "solver.h"
#include <iostream>

int main() {
    Location loc(0.0, 0.0);
    
    // Test 1: Create customer without service_time (should default to 0.0)
    Customer c1(1, loc, 10.0, 0.0, 24.0);
    std::cout << "Customer 1 service_time: " << c1.service_time << std::endl;
    
    // Test 2: Create customer with explicit service_time
    Customer c2(2, loc, 15.0, 0.0, 24.0, 10.0);
    std::cout << "Customer 2 service_time: " << c2.service_time << std::endl;
    
    // Test 3: Modify service_time
    c1.service_time = 5.0;
    std::cout << "Customer 1 service_time after modification: " << c1.service_time << std::endl;
    
    return 0;
}
