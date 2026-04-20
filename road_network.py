"""
Real Road Network Distance Calculator
Uses OpenStreetMap data and routing algorithms for accurate road distances

Features:
- Real road network distances (not straight-line)
- Address geocoding
- Traffic simulation
- Multiple routing profiles (car, truck, bike)
- Caching for performance
"""

import requests
import json
import time
import math
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import sqlite3
import os
from concurrent.futures import ThreadPoolExecutor
import threading


@dataclass
class RoutingProfile:
    """Routing profile for different vehicle types"""
    name: str
    avoid_highways: bool = False
    avoid_tolls: bool = False
    avoid_ferries: bool = False
    max_weight_kg: Optional[float] = None
    max_height_m: Optional[float] = None
    max_width_m: Optional[float] = None
    max_length_m: Optional[float] = None


class AddressGeocoder:
    """Address geocoding using Nominatim (OpenStreetMap)"""
    
    def __init__(self):
        self.base_url = "https://nominatim.openstreetmap.org/search"
        self.cache = {}
        self.rate_limit_delay = 1.0  # Respect Nominatim rate limits
        self.last_request_time = 0.0
        
    def geocode(self, address: str) -> Optional[Tuple[float, float]]:
        """
        Convert address to coordinates
        
        Args:
            address: Address string (e.g., "TSEC College, Bandra, Mumbai")
            
        Returns:
            (latitude, longitude) or None if not found
        """
        # Check cache first
        if address in self.cache:
            return self.cache[address]
        
        # Rate limiting
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - time_since_last)
        
        try:
            params = {
                'q': address,
                'format': 'json',
                'limit': 1,
                'addressdetails': 1
            }
            
            headers = {
                'User-Agent': 'VRP-Solver/1.0 (Educational Project)'
            }
            
            response = requests.get(self.base_url, params=params, headers=headers, timeout=10)
            self.last_request_time = time.time()
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    lat = float(data[0]['lat'])
                    lon = float(data[0]['lon'])
                    result = (lat, lon)
                    self.cache[address] = result
                    return result
            
        except Exception as e:
            print(f"Geocoding error for '{address}': {e}")
        
        return None
    
    def reverse_geocode(self, lat: float, lon: float) -> Optional[str]:
        """
        Convert coordinates to address
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            Address string or None if not found
        """
        try:
            url = "https://nominatim.openstreetmap.org/reverse"
            params = {
                'lat': lat,
                'lon': lon,
                'format': 'json',
                'addressdetails': 1
            }
            
            headers = {
                'User-Agent': 'VRP-Solver/1.0 (Educational Project)'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('display_name', '')
            
        except Exception as e:
            print(f"Reverse geocoding error for ({lat}, {lon}): {e}")
        
        return None


class RoadNetworkRouter:
    """Real road network routing using OSRM (Open Source Routing Machine)"""
    
    def __init__(self, use_local_osrm: bool = False):
        """
        Initialize router
        
        Args:
            use_local_osrm: Use local OSRM server if available, otherwise use demo server
        """
        if use_local_osrm:
            self.base_url = "http://localhost:5000"
        else:
            # Use demo server (limited requests)
            self.base_url = "http://router.project-osrm.org"
        
        self.cache_db = "routing_cache.db"
        self.init_cache_db()
        self.rate_limit_delay = 0.1  # 10 requests per second max
        self.last_request_time = 0.0
        
    def init_cache_db(self):
        """Initialize SQLite cache database"""
        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS routing_cache (
                start_lat REAL,
                start_lon REAL,
                end_lat REAL,
                end_lon REAL,
                profile TEXT,
                distance_km REAL,
                duration_min REAL,
                geometry TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create index for faster lookups
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_routing_cache 
            ON routing_cache (start_lat, start_lon, end_lat, end_lon, profile)
        ''')
        
        conn.commit()
        conn.close()
    
    def get_route(
        self,
        start_lat: float,
        start_lon: float,
        end_lat: float,
        end_lon: float,
        profile: str = "driving"
    ) -> Optional[Dict]:
        """
        Get route between two points
        
        Args:
            start_lat, start_lon: Start coordinates
            end_lat, end_lon: End coordinates
            profile: Routing profile ("driving", "walking", "cycling")
            
        Returns:
            Route information with distance, duration, and geometry
        """
        # Check cache first
        cached_route = self._get_cached_route(start_lat, start_lon, end_lat, end_lon, profile)
        if cached_route:
            return cached_route
        
        # Rate limiting
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - time_since_last)
        
        try:
            # OSRM route API
            url = f"{self.base_url}/route/v1/{profile}/{start_lon},{start_lat};{end_lon},{end_lat}"
            params = {
                'overview': 'full',
                'geometries': 'geojson',
                'steps': 'false'
            }
            
            response = requests.get(url, params=params, timeout=15)
            self.last_request_time = time.time()
            
            if response.status_code == 200:
                data = response.json()
                
                if data['code'] == 'Ok' and data['routes']:
                    route = data['routes'][0]
                    
                    result = {
                        'distance_km': route['distance'] / 1000.0,  # Convert to km
                        'duration_min': route['duration'] / 60.0,   # Convert to minutes
                        'geometry': route['geometry'],
                        'profile': profile
                    }
                    
                    # Cache the result
                    self._cache_route(start_lat, start_lon, end_lat, end_lon, profile, result)
                    
                    return result
            
        except Exception as e:
            print(f"Routing error: {e}")
        
        # Fallback to straight-line distance
        return self._fallback_route(start_lat, start_lon, end_lat, end_lon, profile)
    
    def get_distance_matrix(
        self,
        coordinates: List[Tuple[float, float]],
        profile: str = "driving"
    ) -> Optional[List[List[float]]]:
        """
        Get distance matrix for multiple points
        
        Args:
            coordinates: List of (lat, lon) tuples
            profile: Routing profile
            
        Returns:
            N×N distance matrix in kilometers
        """
        n = len(coordinates)
        if n == 0:
            return []
        
        # For small matrices, use individual route requests
        if n <= 10:
            matrix = [[0.0] * n for _ in range(n)]
            
            for i in range(n):
                for j in range(n):
                    if i != j:
                        route = self.get_route(
                            coordinates[i][0], coordinates[i][1],
                            coordinates[j][0], coordinates[j][1],
                            profile
                        )
                        if route:
                            matrix[i][j] = route['distance_km']
                        else:
                            # Fallback to Haversine
                            matrix[i][j] = self._haversine_distance(
                                coordinates[i][0], coordinates[i][1],
                                coordinates[j][0], coordinates[j][1]
                            )
            
            return matrix
        
        # For larger matrices, use OSRM table service
        try:
            # Format coordinates for OSRM
            coord_string = ";".join([f"{lon},{lat}" for lat, lon in coordinates])
            
            url = f"{self.base_url}/table/v1/{profile}/{coord_string}"
            params = {
                'annotations': 'distance,duration'
            }
            
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                if data['code'] == 'Ok':
                    # Convert distances from meters to kilometers
                    distances = data['distances']
                    matrix = [[dist / 1000.0 for dist in row] for row in distances]
                    return matrix
            
        except Exception as e:
            print(f"Distance matrix error: {e}")
        
        # Fallback to Haversine distances
        return self._fallback_distance_matrix(coordinates)
    
    def _get_cached_route(self, start_lat: float, start_lon: float, end_lat: float, end_lon: float, profile: str) -> Optional[Dict]:
        """Get route from cache"""
        try:
            conn = sqlite3.connect(self.cache_db)
            cursor = conn.cursor()
            
            # Use small tolerance for coordinate matching (about 10 meters)
            tolerance = 0.0001
            
            cursor.execute('''
                SELECT distance_km, duration_min, geometry FROM routing_cache
                WHERE ABS(start_lat - ?) < ? AND ABS(start_lon - ?) < ?
                AND ABS(end_lat - ?) < ? AND ABS(end_lon - ?) < ?
                AND profile = ?
                ORDER BY created_at DESC
                LIMIT 1
            ''', (start_lat, tolerance, start_lon, tolerance, 
                  end_lat, tolerance, end_lon, tolerance, profile))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'distance_km': result[0],
                    'duration_min': result[1],
                    'geometry': json.loads(result[2]) if result[2] else None,
                    'profile': profile
                }
        
        except Exception as e:
            print(f"Cache read error: {e}")
        
        return None
    
    def _cache_route(self, start_lat: float, start_lon: float, end_lat: float, end_lon: float, profile: str, route: Dict):
        """Cache route result"""
        try:
            conn = sqlite3.connect(self.cache_db)
            cursor = conn.cursor()
            
            geometry_json = json.dumps(route.get('geometry')) if route.get('geometry') else None
            
            cursor.execute('''
                INSERT INTO routing_cache 
                (start_lat, start_lon, end_lat, end_lon, profile, distance_km, duration_min, geometry)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (start_lat, start_lon, end_lat, end_lon, profile,
                  route['distance_km'], route['duration_min'], geometry_json))
            
            conn.commit()
            conn.close()
        
        except Exception as e:
            print(f"Cache write error: {e}")
    
    def _fallback_route(self, start_lat: float, start_lon: float, end_lat: float, end_lon: float, profile: str) -> Dict:
        """Fallback to straight-line distance"""
        distance_km = self._haversine_distance(start_lat, start_lon, end_lat, end_lon)
        
        # Estimate duration based on profile
        if profile == "driving":
            speed_kmh = 40.0
        elif profile == "cycling":
            speed_kmh = 15.0
        else:  # walking
            speed_kmh = 5.0
        
        duration_min = (distance_km / speed_kmh) * 60.0
        
        return {
            'distance_km': distance_km * 1.3,  # Add 30% for road network
            'duration_min': duration_min,
            'geometry': None,
            'profile': profile
        }
    
    def _fallback_distance_matrix(self, coordinates: List[Tuple[float, float]]) -> List[List[float]]:
        """Fallback distance matrix using Haversine"""
        n = len(coordinates)
        matrix = [[0.0] * n for _ in range(n)]
        
        for i in range(n):
            for j in range(n):
                if i != j:
                    distance = self._haversine_distance(
                        coordinates[i][0], coordinates[i][1],
                        coordinates[j][0], coordinates[j][1]
                    )
                    matrix[i][j] = distance * 1.3  # Add 30% for road network
        
        return matrix
    
    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate Haversine distance in kilometers"""
        R = 6371.0  # Earth's radius in km
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(dlon / 2) ** 2)
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c


class TrafficSimulator:
    """Traffic simulation for dynamic routing"""
    
    def __init__(self):
        self.traffic_patterns = {
            'rush_hour_morning': {
                'start_time': 7.0 * 60,  # 7:00 AM in minutes
                'end_time': 10.0 * 60,   # 10:00 AM
                'multiplier': 1.8,
                'affected_roads': ['highway', 'primary', 'secondary']
            },
            'rush_hour_evening': {
                'start_time': 17.0 * 60,  # 5:00 PM
                'end_time': 20.0 * 60,    # 8:00 PM
                'multiplier': 2.0,
                'affected_roads': ['highway', 'primary', 'secondary']
            },
            'lunch_time': {
                'start_time': 12.0 * 60,  # 12:00 PM
                'end_time': 14.0 * 60,    # 2:00 PM
                'multiplier': 1.3,
                'affected_roads': ['primary', 'secondary']
            }
        }
    
    def get_traffic_multiplier(self, current_time_minutes: float, road_type: str = 'primary') -> float:
        """
        Get traffic multiplier for current time
        
        Args:
            current_time_minutes: Current time in minutes from midnight
            road_type: Type of road ('highway', 'primary', 'secondary', 'residential')
            
        Returns:
            Traffic multiplier (1.0 = normal, >1.0 = slower)
        """
        multiplier = 1.0
        
        for pattern_name, pattern in self.traffic_patterns.items():
            if (pattern['start_time'] <= current_time_minutes <= pattern['end_time'] and
                road_type in pattern['affected_roads']):
                multiplier = max(multiplier, pattern['multiplier'])
        
        # Add random variation (±10%)
        import random
        variation = random.uniform(0.9, 1.1)
        
        return multiplier * variation
    
    def simulate_incident(self, lat: float, lon: float, radius_km: float, severity: float) -> Dict:
        """
        Simulate traffic incident
        
        Args:
            lat, lon: Incident location
            radius_km: Affected radius
            severity: Severity factor (1.0-5.0)
            
        Returns:
            Incident information
        """
        return {
            'location': (lat, lon),
            'radius_km': radius_km,
            'multiplier': 1.0 + severity,
            'duration_minutes': severity * 30,  # Longer incidents for higher severity
            'description': f"Traffic incident (severity {severity:.1f})"
        }


# Integration class for VRP solver
class RealWorldDistanceProvider:
    """Provides real-world distances for VRP solver"""
    
    def __init__(self, use_caching: bool = True):
        self.geocoder = AddressGeocoder()
        self.router = RoadNetworkRouter()
        self.traffic_sim = TrafficSimulator()
        self.use_caching = use_caching
        
    def geocode_addresses(self, addresses: List[str]) -> List[Optional[Tuple[float, float]]]:
        """Geocode multiple addresses"""
        results = []
        
        for address in addresses:
            coords = self.geocoder.geocode(address)
            results.append(coords)
            
        return results
    
    def build_real_distance_matrix(
        self,
        coordinates: List[Tuple[float, float]],
        profile: str = "driving",
        include_traffic: bool = False,
        current_time_minutes: float = 0.0
    ) -> List[List[float]]:
        """
        Build distance matrix using real road networks
        
        Args:
            coordinates: List of (lat, lon) coordinates
            profile: Routing profile
            include_traffic: Whether to include traffic simulation
            current_time_minutes: Current time for traffic simulation
            
        Returns:
            Distance matrix in kilometers
        """
        # Get base distance matrix
        matrix = self.router.get_distance_matrix(coordinates, profile)
        
        if matrix is None:
            return []
        
        # Apply traffic if requested
        if include_traffic:
            for i in range(len(matrix)):
                for j in range(len(matrix[i])):
                    if i != j:
                        traffic_multiplier = self.traffic_sim.get_traffic_multiplier(
                            current_time_minutes, 'primary'
                        )
                        matrix[i][j] *= traffic_multiplier
        
        return matrix
    
    def get_optimal_departure_times(
        self,
        route: List[Tuple[float, float]],
        service_times: List[float],
        time_windows: List[Tuple[float, float]]
    ) -> Dict[str, any]:
        """
        Calculate optimal departure times considering traffic
        
        Args:
            route: List of coordinates in visit order
            service_times: Service time at each location
            time_windows: (start, end) time windows for each location
            
        Returns:
            Optimal departure times and total travel time
        """
        best_departure = 0.0
        best_total_time = float('inf')
        
        # Try different departure times (every 15 minutes)
        for departure_minutes in range(0, 24 * 60, 15):
            total_time = self._simulate_route_time(
                route, service_times, time_windows, departure_minutes
            )
            
            if total_time < best_total_time:
                best_total_time = total_time
                best_departure = departure_minutes
        
        return {
            'optimal_departure_minutes': best_departure,
            'optimal_departure_time': f"{int(best_departure // 60):02d}:{int(best_departure % 60):02d}",
            'total_time_minutes': best_total_time,
            'time_savings_minutes': self._simulate_route_time(route, service_times, time_windows, 0) - best_total_time
        }
    
    def _simulate_route_time(
        self,
        route: List[Tuple[float, float]],
        service_times: List[float],
        time_windows: List[Tuple[float, float]],
        departure_time: float
    ) -> float:
        """Simulate total route time with traffic"""
        current_time = departure_time
        total_time = 0.0
        
        for i in range(len(route) - 1):
            # Get base travel time
            route_info = self.router.get_route(
                route[i][0], route[i][1],
                route[i + 1][0], route[i + 1][1]
            )
            
            if route_info:
                travel_time = route_info['duration_min']
            else:
                # Fallback
                distance = self.router._haversine_distance(
                    route[i][0], route[i][1],
                    route[i + 1][0], route[i + 1][1]
                )
                travel_time = (distance / 40.0) * 60.0  # 40 km/h
            
            # Apply traffic
            traffic_multiplier = self.traffic_sim.get_traffic_multiplier(current_time)
            travel_time *= traffic_multiplier
            
            current_time += travel_time
            total_time += travel_time
            
            # Add service time and waiting time
            if i + 1 < len(service_times):
                service_time = service_times[i + 1]
                
                # Check time window
                if i + 1 < len(time_windows):
                    start_window, end_window = time_windows[i + 1]
                    
                    # Wait if arriving early
                    if current_time < start_window:
                        wait_time = start_window - current_time
                        current_time += wait_time
                        total_time += wait_time
                    
                    # Penalty if arriving late
                    if current_time > end_window:
                        penalty = (current_time - end_window) * 2  # 2x penalty
                        total_time += penalty
                
                current_time += service_time
                total_time += service_time
        
        return total_time


# Example usage and testing
if __name__ == "__main__":
    # Test geocoding
    geocoder = AddressGeocoder()
    
    test_addresses = [
        "TSEC College, Bandra, Mumbai",
        "Gateway of India, Mumbai",
        "Chhatrapati Shivaji Terminus, Mumbai"
    ]
    
    print("Testing Geocoding:")
    for address in test_addresses:
        coords = geocoder.geocode(address)
        print(f"{address}: {coords}")
    
    # Test routing
    router = RoadNetworkRouter()
    
    if len(test_addresses) >= 2:
        coords1 = geocoder.geocode(test_addresses[0])
        coords2 = geocoder.geocode(test_addresses[1])
        
        if coords1 and coords2:
            print(f"\nTesting Routing:")
            route = router.get_route(coords1[0], coords1[1], coords2[0], coords2[1])
            print(f"Route from {test_addresses[0]} to {test_addresses[1]}:")
            print(f"Distance: {route['distance_km']:.2f} km")
            print(f"Duration: {route['duration_min']:.1f} minutes")
    
    # Test traffic simulation
    traffic_sim = TrafficSimulator()
    
    print(f"\nTesting Traffic Simulation:")
    for hour in [8, 12, 18, 22]:  # 8 AM, 12 PM, 6 PM, 10 PM
        time_minutes = hour * 60
        multiplier = traffic_sim.get_traffic_multiplier(time_minutes)
        print(f"{hour:02d}:00 - Traffic multiplier: {multiplier:.2f}")