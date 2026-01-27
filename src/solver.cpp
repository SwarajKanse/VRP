#include "solver.h"
#include <stdexcept>
#include <limits>
#include <algorithm>

// Location implementation
Location::Location(double lat, double lon) 
    : latitude(lat), longitude(lon) {}

bool Location::operator==(const Location& other) const {
    return latitude == other.latitude && longitude == other.longitude;
}

// Customer implementation
Customer::Customer(int id, Location loc, double demand, double start_w, double end_w, double service_t)
    : id(id), location(loc), demand(demand), start_window(start_w), end_window(end_w), service_time(service_t) {}

// VRPSolver implementation
VRPSolver::VRPSolver() {}

std::vector<Route> VRPSolver::solve(
    const std::vector<Customer>& customers,
    const std::vector<double>& vehicle_capacities,
    bool use_simd,
    const std::vector<std::vector<double>>& time_matrix
) {
    // Validate vehicle_capacities is not empty
    if (vehicle_capacities.empty()) {
        throw std::invalid_argument("Vehicle capacities vector cannot be empty");
    }
    
    // Validate all capacities are positive
    for (size_t i = 0; i < vehicle_capacities.size(); ++i) {
        if (vehicle_capacities[i] <= 0) {
            throw std::invalid_argument("All vehicle capacities must be positive");
        }
    }
    
    // Handle empty customer list
    if (customers.empty() || customers.size() == 1) {
        return std::vector<Route>();
    }
    
    // Store time matrix and set flag
    if (!time_matrix.empty()) {
        // Validate dimensions
        size_t n = customers.size();
        if (time_matrix.size() != n) {
            throw std::invalid_argument(
                "Time matrix dimensions must match number of customers");
        }
        for (size_t i = 0; i < n; ++i) {
            if (time_matrix[i].size() != n) {
                throw std::invalid_argument(
                    "Time matrix must be square (N×N)");
            }
        }
        
        time_matrix_ = time_matrix;
        use_time_matrix_ = true;
    } else {
        use_time_matrix_ = false;
    }
    
    // Build distance matrix with SIMD flag
    buildDistanceMatrix(customers, use_simd);
    
    // Call nearest neighbor heuristic with vehicle capacities
    return nearestNeighborHeuristic(customers, vehicle_capacities);
}

void VRPSolver::buildDistanceMatrix(const std::vector<Customer>& customers, bool use_simd) {
    size_t n = customers.size();
    
    // Allocate n × n matrix
    distance_matrix_.resize(n);
    for (size_t i = 0; i < n; ++i) {
        distance_matrix_[i].resize(n);
    }
    
    // Conditional logic: use SIMD path if enabled and AVX2 is supported
    if (use_simd && hasAVX2Support()) {
        // SIMD path: extract coordinates and use AVX2 batch computation
        std::vector<double> lats, lons;
        extractCoordinates(customers, lats, lons);
        
        // Compute distances for all customer pairs using SIMD
        for (size_t i = 0; i < n; ++i) {
            // Set diagonal to zero
            distance_matrix_[i][i] = 0.0;
            
            // Compute distances from customer i to all subsequent customers
            // computeBatchDistancesAVX2 handles both SIMD (4 at a time) and scalar fallback
            computeBatchDistancesAVX2(lats, lons, i, i + 1);
        }
    } else {
        // Scalar path: use euclideanDistance for each pair
        for (size_t i = 0; i < n; ++i) {
            for (size_t j = 0; j < n; ++j) {
                if (i == j) {
                    // Set diagonal to zero
                    distance_matrix_[i][j] = 0.0;
                } else {
                    // Compute distance using euclideanDistance
                    distance_matrix_[i][j] = euclideanDistance(
                        customers[i].location.latitude,
                        customers[i].location.longitude,
                        customers[j].location.latitude,
                        customers[j].location.longitude
                    );
                }
            }
        }
    }
}

double VRPSolver::haversineDistance(const Location& loc1, const Location& loc2) {
    // Earth's radius in kilometers
    const double R = 6371.0;
    
    // Convert degrees to radians
    const double PI = 3.14159265358979323846;
    double lat1_rad = loc1.latitude * PI / 180.0;
    double lat2_rad = loc2.latitude * PI / 180.0;
    double lon1_rad = loc1.longitude * PI / 180.0;
    double lon2_rad = loc2.longitude * PI / 180.0;
    
    // Calculate differences
    double delta_lat = lat2_rad - lat1_rad;
    double delta_lon = lon2_rad - lon1_rad;
    
    // Apply Haversine formula
    double a = std::sin(delta_lat / 2.0) * std::sin(delta_lat / 2.0) +
               std::cos(lat1_rad) * std::cos(lat2_rad) *
               std::sin(delta_lon / 2.0) * std::sin(delta_lon / 2.0);
    
    double c = 2.0 * std::atan2(std::sqrt(a), std::sqrt(1.0 - a));
    
    // Return distance in kilometers
    return R * c;
}

/**
 * @brief Compute Euclidean distance between two geographic points
 * 
 * This method uses a simplified Euclidean approximation instead of the full
 * Haversine formula. For small geographic areas, this provides reasonable
 * accuracy while being much faster to compute, especially with SIMD operations.
 * 
 * Formula: distance = sqrt((lat2-lat1)^2 + (lon2-lon1)^2)
 * 
 * @param lat1 Latitude of first point
 * @param lon1 Longitude of first point
 * @param lat2 Latitude of second point
 * @param lon2 Longitude of second point
 * @return Euclidean distance between the two points
 */
double VRPSolver::euclideanDistance(double lat1, double lon1, double lat2, double lon2) const {
    // Euclidean approximation: sqrt((lat2-lat1)^2 + (lon2-lon1)^2)
    double dlat = lat2 - lat1;
    double dlon = lon2 - lon1;
    return std::sqrt(dlat * dlat + dlon * dlon);
}

/**
 * @brief Detect AVX2 CPU support at compile time
 * 
 * This method uses compile-time detection to determine if AVX2 instructions
 * are available. The compiler defines __AVX2__ when compiling with AVX2 support.
 * 
 * @return true if AVX2 is supported, false otherwise
 */
bool VRPSolver::hasAVX2Support() const {
    // Compile-time detection of AVX2 support
    #if defined(__AVX2__)
        return true;
    #else
        return false;
    #endif
}

/**
 * @brief Extract coordinates from customer list into Structure of Arrays (SoA) layout
 * 
 * This method transforms customer data from Array of Structures (AoS) to Structure
 * of Arrays (SoA) layout. This transformation enables efficient SIMD operations by
 * placing all latitudes and longitudes in contiguous memory, allowing vectorized
 * loads of 4 values at a time.
 * 
 * The original customer vector remains unchanged (non-destructive transformation).
 * 
 * @param customers Input customer list (AoS layout)
 * @param lats Output vector of latitudes (SoA layout)
 * @param lons Output vector of longitudes (SoA layout)
 */
void VRPSolver::extractCoordinates(
    const std::vector<Customer>& customers,
    std::vector<double>& lats,
    std::vector<double>& lons
) {
    size_t n = customers.size();
    lats.resize(n);
    lons.resize(n);
    
    // Extract coordinates while preserving customer ordering by index
    for (size_t i = 0; i < n; ++i) {
        lats[i] = customers[i].location.latitude;
        lons[i] = customers[i].location.longitude;
    }
}

/**
 * @brief Compute batch distances using AVX2 SIMD instructions
 * 
 * This method computes Euclidean distances from a reference point (from_idx) to
 * multiple target points using AVX2 256-bit vector operations. It processes 4
 * distance calculations simultaneously, achieving significant speedup over scalar code.
 * 
 * AVX2 Operations Used:
 * - _mm256_set1_pd: Broadcast a single double to all 4 lanes of a 256-bit register
 * - _mm256_loadu_pd: Load 4 doubles from unaligned memory (std::vector)
 * - _mm256_sub_pd: Subtract 4 doubles in parallel
 * - _mm256_mul_pd: Multiply 4 doubles in parallel
 * - _mm256_add_pd: Add 4 doubles in parallel
 * - _mm256_sqrt_pd: Compute square root of 4 doubles in parallel
 * - _mm256_storeu_pd: Store 4 doubles to unaligned memory
 * 
 * The method handles non-divisible-by-4 customer counts by processing remainders
 * with scalar fallback code.
 * 
 * @param lats Vector of all customer latitudes (SoA layout)
 * @param lons Vector of all customer longitudes (SoA layout)
 * @param from_idx Index of reference customer
 * @param to_idx Starting index for distance computation
 */
void VRPSolver::computeBatchDistancesAVX2(
    const std::vector<double>& lats,
    const std::vector<double>& lons,
    size_t from_idx,
    size_t to_idx
) {
#if defined(__AVX2__)
    // Get reference point coordinates
    double lat1 = lats[from_idx];
    double lon1 = lons[from_idx];
    
    // Broadcast reference point to all 4 lanes of 256-bit register
    // This creates a vector [lat1, lat1, lat1, lat1] for parallel subtraction
    __m256d lat1_vec = _mm256_set1_pd(lat1);
    __m256d lon1_vec = _mm256_set1_pd(lon1);
    
    size_t n = lats.size();
    size_t i = to_idx;
    
    // SIMD path: Process 4 customers at a time using AVX2
    for (; i + 3 < n; i += 4) {
        // Load 4 consecutive latitudes and longitudes from memory
        // Using unaligned load (_loadu) because std::vector doesn't guarantee 32-byte alignment
        __m256d lat2_vec = _mm256_loadu_pd(&lats[i]);  // [lat[i], lat[i+1], lat[i+2], lat[i+3]]
        __m256d lon2_vec = _mm256_loadu_pd(&lons[i]);  // [lon[i], lon[i+1], lon[i+2], lon[i+3]]
        
        // Compute deltas: lat2 - lat1, lon2 - lon1
        // Performs 4 subtractions in parallel
        __m256d dlat = _mm256_sub_pd(lat2_vec, lat1_vec);
        __m256d dlon = _mm256_sub_pd(lon2_vec, lon1_vec);
        
        // Square the deltas: dlat^2, dlon^2
        // Performs 4 multiplications in parallel
        __m256d dlat_sq = _mm256_mul_pd(dlat, dlat);
        __m256d dlon_sq = _mm256_mul_pd(dlon, dlon);
        
        // Sum: dlat^2 + dlon^2
        // Performs 4 additions in parallel
        __m256d sum = _mm256_add_pd(dlat_sq, dlon_sq);
        
        // Square root: sqrt(dlat^2 + dlon^2)
        // Performs 4 square roots in parallel
        __m256d dist = _mm256_sqrt_pd(sum);
        
        // Store 4 computed distances to temporary array
        double results[4];
        _mm256_storeu_pd(results, dist);
        
        // Store results in distance matrix (both [i][j] and [j][i] for symmetry)
        // This ensures the distance matrix remains symmetric
        for (int j = 0; j < 4; ++j) {
            distance_matrix_[from_idx][i + j] = results[j];
            distance_matrix_[i + j][from_idx] = results[j];
        }
    }
    
    // Scalar fallback for remainder customers (when count not divisible by 4)
    // Example: if we have 7 customers, SIMD processes 4, scalar handles remaining 3
    for (; i < n; ++i) {
        double dist = euclideanDistance(lat1, lon1, lats[i], lons[i]);
        distance_matrix_[from_idx][i] = dist;
        distance_matrix_[i][from_idx] = dist;
    }
#else
    // Fallback to scalar implementation when AVX2 is not available
    // This ensures the code compiles and runs on non-AVX2 systems
    double lat1 = lats[from_idx];
    double lon1 = lons[from_idx];
    
    size_t n = lats.size();
    for (size_t i = to_idx; i < n; ++i) {
        double dist = euclideanDistance(lat1, lon1, lats[i], lons[i]);
        distance_matrix_[from_idx][i] = dist;
        distance_matrix_[i][from_idx] = dist;
    }
#endif
}

std::vector<Route> VRPSolver::nearestNeighborHeuristic(
    const std::vector<Customer>& customers,
    const std::vector<double>& vehicle_capacities
) {
    size_t n = customers.size();
    size_t num_vehicles = vehicle_capacities.size();
    
    // Initialize visited array (all false except depot)
    std::vector<bool> visited(n, false);
    visited[0] = true;  // depot is always "visited"
    
    std::vector<Route> routes;
    
    // Count unvisited customers
    auto countUnvisited = [&visited]() {
        int count = 0;
        for (size_t i = 1; i < visited.size(); ++i) {
            if (!visited[i]) count++;
        }
        return count;
    };
    
    // Create routes up to num_vehicles
    for (size_t vehicle_idx = 0; vehicle_idx < num_vehicles; ++vehicle_idx) {
        // Check if any unvisited customers remain
        if (countUnvisited() == 0) {
            break;  // All customers served
        }
        
        // Get capacity for this specific vehicle
        double current_vehicle_capacity = vehicle_capacities[vehicle_idx];
        
        // Start new route at depot (customer 0)
        Route current_route;
        current_route.push_back(0);
        
        double current_load = 0.0;
        double current_time = 0.0;
        int current_location = 0;
        
        // Greedily add nearest feasible customer
        while (true) {
            int best_customer = -1;
            double best_distance = std::numeric_limits<double>::infinity();
            
            // Find nearest unvisited customer that satisfies constraints
            for (size_t i = 1; i < n; ++i) {
                if (!visited[i]) {
                    // Use current_vehicle_capacity instead of global capacity
                    if (canAddToRoute(current_route, i, customers, current_vehicle_capacity, current_time)) {
                        double distance = distance_matrix_[current_location][i];
                        if (distance < best_distance) {
                            best_distance = distance;
                            best_customer = i;
                        }
                    }
                }
            }
            
            // When no feasible customer, finalize route
            if (best_customer == -1) {
                break;
            }
            
            // Add customer to route
            current_route.push_back(best_customer);
            visited[best_customer] = true;
            
            // Update current location, load, and time
            const Customer& customer = customers[best_customer];
            current_load += customer.demand;
            
            // Calculate arrival time using getTravelTime()
            double travel_time = getTravelTime(current_location, best_customer);
            double arrival_time = current_time + travel_time;
            
            // Calculate waiting time if arriving before start_window
            double waiting_time = std::max(0.0, customer.start_window - arrival_time);
            
            // Update current_time: arrival + waiting + service
            current_time = arrival_time + waiting_time + customer.service_time;
            
            current_location = best_customer;
        }
        
        // Check if we added any customers to this route
        // If route only contains depot (size == 1), it means no customers could be added
        // This happens when remaining customers cannot fit in a fresh vehicle
        if (current_route.size() == 1) {
            // Cannot serve remaining customers - stop creating routes
            break;
        }
        
        // Return to depot
        current_route.push_back(0);
        
        // Add completed route to routes list
        routes.push_back(current_route);
    }
    
    // Return list of routes
    return routes;
}

bool VRPSolver::canAddToRoute(
    const Route& route,
    int customer_idx,
    const std::vector<Customer>& customers,
    double vehicle_capacity,
    double current_time
) {
    // Validate customer index
    if (customer_idx < 0 || customer_idx >= static_cast<int>(customers.size())) {
        return false;
    }
    
    const Customer& customer = customers[customer_idx];
    
    // Check capacity constraint: route_load + customer.demand ≤ capacity
    double route_load = calculateRouteLoad(route, customers);
    if (route_load + customer.demand > vehicle_capacity) {
        return false;
    }
    
    // Calculate arrival time: current_time + travel_time
    // Get the current location (last customer in route, or depot if empty)
    int current_location = route.empty() ? 0 : route.back();
    double travel_time = getTravelTime(current_location, customer_idx);
    double arrival_time = current_time + travel_time;
    
    // Check time window: arrival_time ≤ customer.end_window
    if (arrival_time > customer.end_window) {
        return false;
    }
    
    // All constraints satisfied
    return true;
}

double VRPSolver::getTravelTime(int from_idx, int to_idx) const {
    if (use_time_matrix_) {
        // Use provided time matrix (already in minutes)
        return time_matrix_[from_idx][to_idx];
    } else {
        // Fallback: Use distance matrix (in km)
        // Assume 40 km/h = 0.666... km/min
        // travel_time = distance / speed = distance / (40/60) = distance * 1.5
        return distance_matrix_[from_idx][to_idx] * 1.5;
    }
}

double VRPSolver::calculateRouteLoad(
    const Route& route,
    const std::vector<Customer>& customers
) {
    double total_load = 0.0;
    
    // Sum demands for all customers in the route
    for (int customer_id : route) {
        // Skip depot (customer 0) as it has no demand
        if (customer_id > 0 && customer_id < static_cast<int>(customers.size())) {
            total_load += customers[customer_id].demand;
        }
    }
    
    return total_load;
}
