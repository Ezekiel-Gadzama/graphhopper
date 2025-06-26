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
from math import radians, cos, sin, asin, sqrt
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

        if len(points_near_road) > 0:
            print(f"Total points: {len(points_near_road)}")
            print("Kiss me")
        # print(f"\n\points_near_road : {points_near_road}")
        
        if not points_near_road:
            # No specific data for this road, use general coefficients
            return self.fuel_coefficients.get(road.road_type, 1.0)
            
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
            points = db.get_fuel_points(vehicle['agentid'], days=1000)
            all_points.extend(points)
            
        # Filter points that are close to any point on the road
        # This is simplified - in reality you'd use proper spatial queries
        filtered = []
        for p in all_points:
            print(f"p.timestamp: {p.timestamp}, fuel_level: {p.fuel_level}, speed: {p.speed}")
            if any(self._distance(p.latitude, p.longitude, lat, lon) < 33 for lon, lat in road.coordinates):
                filtered.append(p)
        return filtered


    def _distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate haversine distance (in kilometers) between two lat/lon points"""
        R = 6371  # Earth radius in kilometers
        lat1r, lon1r, lat2r, lon2r = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2r - lat1r
        dlon = lon2r - lon1r
        a = sin(dlat/2)**2 + cos(lat1r)*cos(lat2r)*sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        distance = R * c
        print(f"target_lat: {lat1} target_lon: {lon1} | lat: {lat2} long: {lon2} with distance: {distance}KM")
        return distance


    
    def calculate_edge_weight_multiplier(
        self,
        fuel_multiplier: float,
        jam_multiplier: float, 
        weather_multiplier: float
        ) -> float:
            return fuel_multiplier * jam_multiplier * weather_multiplier

    def update_custom_model(self, osm_ids: List[int]) -> None:
        # Load all roads
        extractor = RoadExtractor()
        extractor.apply_file(settings.OSM_FILE_PATH, locations=True)
        print(f"Number of Roads: {len(extractor.roads)}")

############################Just to process few road that are close bye#############################

        # Define target point
        target_lat = 55.7656327
        target_lon = 37.5421311
        # Compute distances from each road to the target point
        road_distances = []
        for osm_id, road in extractor.roads.items():
            if road.coordinates:
                for lon, lat in road.coordinates:
                    dist = self._distance(target_lat, target_lon, lat, lon)
                    if dist < 1:
                        road_distances.append((osm_id, road, dist))
                        break  # Avoid adding the same road multiple times
            if len(road_distances) >= 5:
                break


        # Sort by distance and keep top 5
        closest_roads = sorted(road_distances, key=lambda x: x[2])[:5]

##############################################################################

        # Process only the closest 5 roads
        for osm_id, road, dist in closest_roads:
            print(f"Processing OSM ID {osm_id}: with distance {dist} type={road.road_type}")

            fuel_multiplier = self.process_road(road)

            # Optionally fetch traffic and weather data here
            # traffic_raw = self.here_api.get_traffic_flow(road.coordinates)
            # traffic_data = self.here_api.extract_traffic_data(traffic_raw)
            # weather_raw = self.tomorrow_io.get_weather_data(road.coordinates)
            # weather_data = self.tomorrow_io.extract_weather_data(weather_raw)

            # multiplier = self.calculate_edge_weight_multiplier(
            #     fuel_multiplier=fuel_multiplier,
            #     jam_multiplier=traffic_data.jam_factor,
            #     weather_multiplier=weather_data.weather_factor
            # )

            # multiplier = fuel_multiplier

            # self.custom_model.add_priority_rule(osm_id, multiplier)
            # print(f"Added rule: OSM ID {osm_id}, multiplier={multiplier:.2f}")

            break

        self.custom_model.save_to_file()
