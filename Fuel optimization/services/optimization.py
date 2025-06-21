import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from typing import Dict, List
from models.custom_model import CustomModel
from models.road import RoadExtractor, Road
from services.api.here_api import HereAPI
from services.api.tomorrow_io import TomorrowIO
from services.api.fuel_database import FuelDatabase
from services.fuel_analysis import FuelAnalyzer
from config.settings import settings
import json
from models.data_class import FuelPoint


class FuelOptimizer:
    def __init__(self):
        self.here_api = HereAPI()
        self.tomorrow_io = TomorrowIO()
        self.fuel_analyzer = FuelAnalyzer()
        self.custom_model = CustomModel()
        self.fuel_coefficients = self._load_fuel_coefficients()

    def _load_fuel_coefficients(self) -> Dict[str, float]:
        """Load or calculate fuel coefficients"""
        try:
            with open('fuel_coefficients.json') as f:
                return json.load(f)
        except FileNotFoundError:
            # Example - in real usage you'd analyze actual vehicles
            fleet_profile = self.fuel_analyzer.analyze_fleet([196, 197])  # Example vehicle IDs
            coefficients = fleet_profile.median_coefficients
            
            with open('fuel_coefficients.json', 'w') as f:
                json.dump(coefficients, f)
                
            return coefficients

    def process_road(self, road: Road) -> float:
        """Process a single road segment to calculate its fuel multiplier"""
        if not road.coordinates:
            return 1.0  # Default multiplier
            
        # Get fuel data points along this road
        db = FuelDatabase(settings.DB_CONFIG)
        points_near_road = self._get_points_near_road(road, db)
        
        if not points_near_road:
            # No specific data for this road, use general coefficients
            return self.fuel_coefficients.get(road.road_type.value, 1.0)
            
        # Calculate specific coefficient for this road
        segments = self.fuel_analyzer.create_segments(points_near_road)
        coefficients = self.fuel_analyzer.calculate_coefficients(segments)
        return coefficients.get(road.road_type, 1.0)

    def _get_points_near_road(self, road: Road, db: FuelDatabase) -> List[FuelPoint]:
        """Get fuel points that are near the specified road"""
        # In a real implementation, you'd query points within a buffer of the road
        # For simplicity, we'll just get all points and filter
        all_points = []
        for vehicle in db.get_vehicles_with_fuel_sensors():
            print(f"Vehicle: {vehicle}")
            points = db.get_fuel_points(vehicle['agentid'], days=30)
            all_points.extend(points)
            
        # Filter points that are close to any point on the road
        # This is simplified - in reality you'd use proper spatial queries
        return [
            p for p in all_points
            if any(self._distance(p.latitude, p.longitude, lat, lon) < 0.01  # ~1km
                  for lon, lat in road.coordinates)
        ]

    def _distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Simple distance calculation (in degrees)"""
        return ((lat1 - lat2)**2 + (lon1 - lon2)**2)**0.5
    
    def calculate_edge_weight_multiplier(
        self,
        fuel_multiplier: float,
        jam_multiplier: float, 
        weather_multiplier: float
        ) -> float:
            return fuel_multiplier * jam_multiplier * weather_multiplier

    def update_custom_model(self, osm_ids: List[int]) -> None:
        """Update custom model with fuel coefficients for specified roads"""
        extractor = RoadExtractor(osm_ids)
        extractor.apply_file(settings.OSM_FILE_PATH, locations=True)
        
        for osm_id in osm_ids:
            if osm_id not in extractor.roads:
                continue
                
            road = extractor.roads[osm_id]
            fuel_multiplier = self.process_road(road)

            # # Get traffic data
            # traffic_raw = self.here_api.get_traffic_flow(road.coordinates)
            # traffic_data = self.here_api.extract_traffic_data(traffic_raw)
            
            # # Get weather data
            # weather_raw = self.tomorrow_io.get_weather_data(road.coordinates)
            # weather_data = self.tomorrow_io.extract_weather_data(weather_raw)

            # # Calculate multiplier
            # multiplier = self.calculate_edge_weight_multiplier(
            #     fuel_multiplier=fuel_multiplier,
            #     jam_multiplier=traffic_data.jam_factor,
            #     weather_multiplier=weather_data.weather_factor
            # )

            multiplier = fuel_multiplier
            
            self.custom_model.add_priority_rule(osm_id, multiplier)
            print(f"Processed OSM ID {osm_id}: {road.road_type.value} road, multiplier={multiplier:.2f}")
        
        self.custom_model.save_to_file()