import math
from typing import Tuple, List

# Earth's radius in meters
EARTH_RADIUS = 6371000

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on the Earth's surface
    using the Haversine formula.
    
    Args:
        lat1: Latitude of first point in degrees
        lon1: Longitude of first point in degrees
        lat2: Latitude of second point in degrees
        lon2: Longitude of second point in degrees
    
    Returns:
        Distance between points in meters
    """
    # Convert degrees to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Differences in coordinates
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    # Haversine formula
    a = (math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return EARTH_RADIUS * c

def calculate_distance_between_points(point1: Tuple[float, float], point2: Tuple[float, float]) -> float:
    """
    Calculate distance between two points represented as (lat, lon) tuples.
    
    Args:
        point1: Tuple of (latitude, longitude) for first point
        point2: Tuple of (latitude, longitude) for second point
    
    Returns:
        Distance between points in meters
    """
    return calculate_distance(point1[0], point1[1], point2[0], point2[1])

def calculate_path_length(points: List[Tuple[float, float]]) -> float:
    """
    Calculate the total length of a path composed of multiple points.
    
    Args:
        points: List of (latitude, longitude) tuples representing the path
    
    Returns:
        Total path length in meters
    """
    if len(points) < 2:
        return 0.0
    
    total_distance = 0.0
    for i in range(len(points) - 1):
        total_distance += calculate_distance_between_points(points[i], points[i+1])
    
    return total_distance