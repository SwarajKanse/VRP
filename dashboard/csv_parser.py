"""
CSV Parser Module for VRP Solver

This module provides functionality to parse CSV manifest files containing
package information with validation for coordinates, dimensions, and constraints.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
import pandas as pd


@dataclass
class Package:
    """Represents a single package with all delivery details."""
    order_id: str
    source_name: str
    destination_name: str
    latitude: float
    longitude: float
    length_m: float  # converted from cm
    width_m: float   # converted from cm
    height_m: float  # converted from cm
    weight_kg: float
    fragile: bool
    this_side_up: bool
    
    @property
    def volume_m3(self) -> float:
        """Calculate package volume in cubic meters."""
        return self.length_m * self.width_m * self.height_m


@dataclass
class Destination:
    """Represents a delivery destination with aggregated package data."""
    name: str
    latitude: float
    longitude: float
    total_weight_kg: float
    packages: List[Package]


class CSVParser:
    """Parser for CSV manifest files with validation."""
    
    REQUIRED_COLUMNS = [
        'Order ID',
        'Source Name',
        'Destination Name',
        'Latitude',
        'Longitude',
        'Length (cm)',
        'Width (cm)',
        'Height (cm)',
        'Weight (kg)'
    ]
    
    OPTIONAL_COLUMNS = ['Fragile', 'This Side Up']
    
    def parse_manifest(self, file_path: str) -> Tuple[List[Destination], Optional[str]]:
        """
        Parse CSV manifest and return destinations with packages.
        
        Args:
            file_path: Path to the CSV file
            
        Returns:
            (destinations, error_message)
            - destinations: List of Destination objects if successful
            - error_message: None if successful, error string if validation fails
        """
        try:
            # Read CSV file
            df = pd.read_csv(file_path)
            
            # Validate required columns
            missing_columns = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
            if missing_columns:
                return [], f"Missing required columns: {', '.join(missing_columns)}"
            
            # Add optional columns with defaults if missing
            if 'Fragile' not in df.columns:
                df['Fragile'] = 'No'
            if 'This Side Up' not in df.columns:
                df['This Side Up'] = 'No'
            
            packages = []
            
            # Parse each row
            for idx, row in df.iterrows():
                row_num = idx + 2  # +2 because: 0-indexed + header row
                
                # Validate coordinates
                error = self._validate_coordinates(
                    row['Latitude'], 
                    row['Longitude'], 
                    row_num
                )
                if error:
                    return [], error
                
                # Validate dimensions and weight
                error = self._validate_dimensions(
                    row['Length (cm)'],
                    row['Width (cm)'],
                    row['Height (cm)'],
                    row['Weight (kg)'],
                    row_num
                )
                if error:
                    return [], error
                
                # Parse boolean values
                fragile = self._parse_boolean(row['Fragile'], default=False)
                this_side_up = self._parse_boolean(row['This Side Up'], default=False)
                
                # Create package with converted dimensions
                package = Package(
                    order_id=str(row['Order ID']),
                    source_name=str(row['Source Name']),
                    destination_name=str(row['Destination Name']),
                    latitude=float(row['Latitude']),
                    longitude=float(row['Longitude']),
                    length_m=self._convert_to_meters(float(row['Length (cm)'])),
                    width_m=self._convert_to_meters(float(row['Width (cm)'])),
                    height_m=self._convert_to_meters(float(row['Height (cm)'])),
                    weight_kg=float(row['Weight (kg)']),
                    fragile=fragile,
                    this_side_up=this_side_up
                )
                packages.append(package)
            
            # Aggregate packages by destination
            destinations = self._aggregate_by_destination(packages)
            
            return destinations, None
            
        except Exception as e:
            return [], f"Error parsing CSV: {str(e)}"
    
    def _validate_coordinates(self, lat: float, lon: float, row_num: int) -> Optional[str]:
        """
        Validate latitude and longitude ranges.
        
        Args:
            lat: Latitude value
            lon: Longitude value
            row_num: Row number for error reporting
            
        Returns:
            Error message if invalid, None if valid
        """
        try:
            lat = float(lat)
            lon = float(lon)
            
            if lat < -90 or lat > 90:
                return f"Row {row_num}: Latitude must be between -90 and 90 (got {lat})"
            
            if lon < -180 or lon > 180:
                return f"Row {row_num}: Longitude must be between -180 and 180 (got {lon})"
            
            return None
        except (ValueError, TypeError):
            return f"Row {row_num}: Invalid coordinate values"
    
    def _validate_dimensions(self, length: float, width: float, height: float, 
                            weight: float, row_num: int) -> Optional[str]:
        """
        Validate all dimensions and weight are positive.
        
        Args:
            length: Length in cm
            width: Width in cm
            height: Height in cm
            weight: Weight in kg
            row_num: Row number for error reporting
            
        Returns:
            Error message if invalid, None if valid
        """
        try:
            length = float(length)
            width = float(width)
            height = float(height)
            weight = float(weight)
            
            if length <= 0:
                return f"Row {row_num}: Length (cm) must be positive (got {length})"
            
            if width <= 0:
                return f"Row {row_num}: Width (cm) must be positive (got {width})"
            
            if height <= 0:
                return f"Row {row_num}: Height (cm) must be positive (got {height})"
            
            if weight <= 0:
                return f"Row {row_num}: Weight (kg) must be positive (got {weight})"
            
            return None
        except (ValueError, TypeError) as e:
            return f"Row {row_num}: Invalid numeric value - {str(e)}"
    
    def _parse_boolean(self, value: str, default: bool = False) -> bool:
        """
        Parse Yes/No values case-insensitively.
        
        Args:
            value: String value to parse
            default: Default value if parsing fails
            
        Returns:
            Boolean value
        """
        if pd.isna(value):
            return default
        
        value_str = str(value).strip().lower()
        if value_str in ['yes', 'y', 'true', '1']:
            return True
        elif value_str in ['no', 'n', 'false', '0']:
            return False
        else:
            return default
    
    def _convert_to_meters(self, cm: float) -> float:
        """
        Convert centimeters to meters.
        
        Args:
            cm: Value in centimeters
            
        Returns:
            Value in meters
        """
        return cm / 100.0
    
    def _aggregate_by_destination(self, packages: List[Package]) -> List[Destination]:
        """
        Group packages by destination and aggregate weights.
        
        Args:
            packages: List of Package objects
            
        Returns:
            List of Destination objects with aggregated data
        """
        # Group packages by destination name
        destination_map = {}
        
        for package in packages:
            dest_name = package.destination_name
            
            if dest_name not in destination_map:
                destination_map[dest_name] = {
                    'latitude': package.latitude,
                    'longitude': package.longitude,
                    'packages': []
                }
            
            destination_map[dest_name]['packages'].append(package)
        
        # Create Destination objects
        destinations = []
        for dest_name, dest_data in destination_map.items():
            total_weight = sum(p.weight_kg for p in dest_data['packages'])
            
            destination = Destination(
                name=dest_name,
                latitude=dest_data['latitude'],
                longitude=dest_data['longitude'],
                total_weight_kg=total_weight,
                packages=dest_data['packages']
            )
            destinations.append(destination)
        
        return destinations
