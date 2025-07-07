import requests
from typing import Dict, List, Tuple
from config.settings import settings
from .polyline import Polyline
from models.road import Road
from utils.geo import calculate_distance


class HereMapAPI:
    TRAFFIC_URL = "https://data.traffic.hereapi.com/v7/flow"
    
    def __init__(self, api_key: str = settings.HERE_API_KEY):
        self.api_key = api_key
        print(f"Using HERE API Key: {self.api_key}")
        self.cached_traffic_data = None

    def get_moscow_traffic(self) -> Dict:
        """Get real-time traffic flow data for Moscow"""
        params = {
            'in': 'bbox:13.4000,52.5000,13.4050,52.5050',  # W,S,E,N
            'locationReferencing': 'shape',
            'apiKey': self.api_key
        }

        try:
            response = requests.get(self.TRAFFIC_URL, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Debug print the actual API request URL
            print(f"API Request URL: {response.request.url}")
            
            return data
        except requests.exceptions.HTTPError as e:
            print(f"Traffic API Error: {e}")
            print(f"Response: {e.response.text}")
            return {'sourceUpdated': None, 'results': []}
        
    def get_traffic_data(self) -> Dict:
        """Get cached or fresh traffic data"""
        if not self.cached_traffic_data:
            self.cached_traffic_data = self.get_moscow_traffic()
        print(f"Cached traffic data: {self.cached_traffic_data}")
        return self.cached_traffic_data

        

class HereTerrainAPI:
    BASE_URL = "https://router.hereapi.com/v8/routes"

    def __init__(self, api_key: str = settings.HERE_API_KEY):
        self.api_key = api_key
        self.cached_terrain_data = None
        self.moscow_bbox = [
            (55.5733, 37.3656),  # SW corner
            (55.9135, 37.8584)   # NE corner
        ]

    def get_moscow_terrain(self) -> Dict:
        """Get terrain data for Moscow area using Routing API elevation profile"""
        # Create waypoints along the bounding box to get full coverage
        waypoints = self._generate_grid_waypoints()
        
        # Construct the waypoints parameter correctly
        waypoints_params = {
            f'destination{i}': f"{lat},{lon}"
            for i, (lat, lon) in enumerate(waypoints[1:], start=1)
        }
        
        params = {
            'apiKey': self.api_key,
            'origin': f"{waypoints[0][0]},{waypoints[0][1]}",
            'transportMode': 'car',
            'return': 'polyline,elevation',
            'spans': 'elevation',
            **waypoints_params  # Unpack the waypoints into the params dict
        }
        
        response = requests.get(self.BASE_URL, params=params)
        response.raise_for_status()
        return self._process_elevation_data(response.json())

    def _generate_grid_waypoints(self, grid_size: int = 5) -> List[Tuple[float, float]]:
        """Generate grid of waypoints within Moscow bounding box"""
        min_lat, min_lon = self.moscow_bbox[0]
        max_lat, max_lon = self.moscow_bbox[1]
        
        lat_step = (max_lat - min_lat) / grid_size
        lon_step = (max_lon - min_lon) / grid_size
        
        waypoints = []
        for i in range(grid_size + 1):
            for j in range(grid_size + 1):
                waypoints.append((
                    min_lat + i * lat_step,
                    min_lon + j * lon_step
                ))
        return waypoints

    def _process_elevation_data(self, raw_data: Dict) -> Dict:
        """Process raw elevation data into a more usable format"""
        elevation_data = {}
        
        for route in raw_data.get('routes', []):
            for section in route.get('sections', []):
                if 'polyline' in section:
                    # Decode the flexible polyline with elevation data
                    decoded = Polyline.decode(section['polyline'], 3)
                    for point in decoded:
                        lat, lon, elev = point
                        elevation_data[f"{lat:.4f},{lon:.4f}"] = elev
        
        return {
            'elevation_data': elevation_data,
            'raw': raw_data  # Keep original data for reference
        }

    def get_terrain_data(self) -> Dict:
        """Get cached or fresh terrain data"""
        if not self.cached_terrain_data:
            self.cached_terrain_data = self.get_moscow_terrain()
        return self.cached_terrain_data

    def get_elevation_for_road(self, road: Road) -> Dict:
        """Get elevation data for specific road coordinates"""
        elevation_points = []
        
        for coord in road.coordinates:
            # Find nearest elevation point (simplified - could be improved)
            closest_key = min(
                self.cached_terrain_data['elevation_data'].keys(),
                key=lambda k: calculate_distance(
                    coord, 
                    tuple(map(float, k.split(',')))
                )
            )
            elevation_points.append(self.cached_terrain_data['elevation_data'][closest_key])
        
        return {
            'elevation_points': elevation_points,
            'average_elevation': sum(elevation_points) / len(elevation_points),
            'max_elevation': max(elevation_points),
            'min_elevation': min(elevation_points)
        }