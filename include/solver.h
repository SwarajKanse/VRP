#pragma once

#include <vector>
#include <cmath>

// Conditional include for AVX2 intrinsics
#if defined(__AVX2__)
#include <immintrin.h>
#endif

// Location struct representing geographic coordinates
struct Location {
    double latitude;
    double longitude;
    
    Location(double lat, double lon);
    
    bool operator==(const Location& other) const;
};

// Customer struct with demand and time window constraints
struct Customer {
    int id;
    Location location;
    double demand;
    double start_window;
    double end_window;
    double service_time;
    
    Customer(int id, Location loc, double demand, double start_w, double end_w, double service_t = 0.0);
};

// Route type alias
using Route = std::vector<int>;

// VRPSolver class implementing Nearest Neighbor heuristic with AVX2 SIMD optimization
class VRPSolver {
public:
    VRPSolver();
    
    /**
     * @brief Solve the Vehicle Routing Problem with heterogeneous fleet and optional SIMD optimization
     * 
     * @param customers List of customers to visit (customer 0 is depot)
     * @param vehicle_capacities Vector of vehicle capacities, one per vehicle in the fleet
     * @param use_simd Enable AVX2 SIMD optimization for distance calculations (default: true)
     * @param time_matrix Optional travel time matrix (N×N) in minutes (default: empty)
     * @return Vector of routes, where each route is a sequence of customer IDs
     */
    std::vector<Route> solve(
        const std::vector<Customer>& customers,
        const std::vector<double>& vehicle_capacities,
        bool use_simd = true,
        const std::vector<std::vector<double>>& time_matrix = {}
    );

private:
    std::vector<std::vector<double>> distance_matrix_;
    std::vector<std::vector<double>> time_matrix_;  // Travel time matrix (minutes)
    bool use_time_matrix_;  // Flag to indicate if time_matrix is provided
    
    /**
     * @brief Build distance matrix using SIMD or scalar path
     * 
     * @param customers List of customers
     * @param use_simd Flag to enable SIMD optimization
     */
    void buildDistanceMatrix(const std::vector<Customer>& customers, bool use_simd);
    
    /**
     * @brief Extract coordinates into Structure of Arrays (SoA) layout for SIMD
     * 
     * @param customers Input customer list
     * @param lats Output vector of latitudes
     * @param lons Output vector of longitudes
     */
    void extractCoordinates(
        const std::vector<Customer>& customers,
        std::vector<double>& lats,
        std::vector<double>& lons
    );
    
    /**
     * @brief Calculate Haversine distance between two locations (legacy method)
     * 
     * @param loc1 First location
     * @param loc2 Second location
     * @return Distance in kilometers
     */
    double haversineDistance(const Location& loc1, const Location& loc2);
    
    /**
     * @brief Calculate Euclidean distance approximation
     * 
     * @param lat1 Latitude of first point
     * @param lon1 Longitude of first point
     * @param lat2 Latitude of second point
     * @param lon2 Longitude of second point
     * @return Euclidean distance
     */
    double euclideanDistance(double lat1, double lon1, double lat2, double lon2) const;
    
    /**
     * @brief Detect AVX2 CPU support at compile time
     * 
     * @return true if AVX2 is available, false otherwise
     */
    bool hasAVX2Support() const;
    
    /**
     * @brief Compute batch distances using AVX2 SIMD instructions
     * 
     * Processes 4 distance calculations simultaneously using 256-bit vector operations.
     * Handles non-divisible-by-4 counts with scalar fallback.
     * 
     * @param lats Vector of all customer latitudes
     * @param lons Vector of all customer longitudes
     * @param from_idx Index of reference customer
     * @param to_idx Starting index for distance computation
     */
    void computeBatchDistancesAVX2(
        const std::vector<double>& lats,
        const std::vector<double>& lons,
        size_t from_idx,
        size_t to_idx
    );
    
    std::vector<Route> nearestNeighborHeuristic(
        const std::vector<Customer>& customers,
        const std::vector<double>& vehicle_capacities
    );
    
    bool canAddToRoute(
        const Route& route,
        int customer_idx,
        const std::vector<Customer>& customers,
        double vehicle_capacity,
        double current_time
    );
    
    /**
     * @brief Get travel time between two customers
     * 
     * Uses time_matrix when available, otherwise falls back to distance_matrix * 1.5
     * (assuming 40 km/h average speed: distance / (40/60) = distance * 1.5)
     * 
     * @param from_idx Index of origin customer
     * @param to_idx Index of destination customer
     * @return Travel time in minutes
     */
    double getTravelTime(int from_idx, int to_idx) const;
    
    double calculateRouteLoad(
        const Route& route,
        const std::vector<Customer>& customers
    );
};
