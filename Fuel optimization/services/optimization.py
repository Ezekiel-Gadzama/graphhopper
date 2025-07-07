import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from typing import Dict, List, Optional
from models.custom_model import CustomModel
from models.road import RoadExtractor, Road
from services.api.here_api import HereMapAPI, HereTerrainAPI
from services.api.tomorrow_io import TomorrowIO
from services.fuel_analysis import FuelAnalyzer
from models.data_class import FuelPoint, RoadProfile
from services.RoadCoefficientProcessor import RoadCoefficientProcessor
from utils.geo import calculate_distance

class FuelOptimizer:
    def __init__(self):
        self.here_map_api = HereMapAPI()
        self.here_terrain_api = HereTerrainAPI()
        self.tomorrow_io = TomorrowIO()
        self.fuel_analyzer = FuelAnalyzer()
        self.coefficient_processor = RoadCoefficientProcessor()
        self.custom_model = CustomModel()

    def create_road_profile(self, road: Road) -> RoadProfile:
        """Create road profile with current traffic, terrain, and weather data"""
        # Get cached data if available
        traffic_data = self.here_map_api.get_traffic_data()
        terrain_data = self.here_terrain_api.get_terrain_data()
        weather_data = self.tomorrow_io.get_weather_data()

        # Extract relevant data for this specific road
        road_traffic = self._find_matching_traffic(road, traffic_data)
        road_terrain = self._find_matching_terrain(road, terrain_data)
        road_weather = self._find_matching_weather(road, weather_data)
            
        return RoadProfile.from_here_api(
            road=road,
            road_traffic_data=road_traffic,
            road_terrain_data=road_terrain,
            road_weather_data=road_weather
        )
    
    def _find_matching_traffic(self, road: Road, traffic_data: Dict) -> Optional[Dict]:
        """Find traffic data for a specific road segment"""
        # Implementation depends on your road identification logic
        # Example: match by road ID or coordinates
        return traffic_data.get(road.id) or None

    def _find_matching_terrain(self, road: Road, terrain_data: Dict) -> Optional[Dict]:
        """Find terrain data for a specific road segment"""
        # Implementation depends on your terrain API response structure
        return terrain_data.get(road.id) or None
    
    def _find_matching_weather(self, road: Road, weather_data: Dict) -> Optional[Dict]:
        """Find weather data for a specific road segment"""
        # Implementation depends on how weather data is organized
        # Could be by coordinates or region
        return weather_data.get(road.region_id) or None
    
    
    def group_points_by_road_id(self, roads_points: List[FuelPoint]) -> Dict[int, List[FuelPoint]]:
        grouped = {}
        for point in roads_points:
            road_id = point.osm_roadID
            if road_id is not None:
                grouped.setdefault(road_id, []).append(point)
        return grouped

    def update_custom_model(self) -> None:
        # Load all roads
        extractor = RoadExtractor()
        # extractor.apply_file(settings.OSM_FILE_PATH, locations=True)
        # print(f"Number of Roads: {len(extractor.roads)}")
        fleet_profile = self.fuel_analyzer.analyze_fleet(300)
        fuel_type_coefficients = fleet_profile.median_coefficients
        print(f"Coefficients: {fuel_type_coefficients}")
        points = fleet_profile.vehicles[0].fuel_points # try for just the first vehicle
        grouped_points = self.group_points_by_road_id(points)
        print(f"grouped points: {grouped_points}")
        print(f"Invalid agents: {self.fuel_analyzer.invalid_agents}")
        print(f"All agents: {self.fuel_analyzer.all_agents}")

# ############################Just to process few road that are close by#############################

#         # Define target point
#         target_lat = 55.470371
#         target_lon = 37.572002
#         # Compute distances from each road to the target point
#         road_distances = []
#         for osm_id, road in extractor.roads.items():
#             if road.coordinates:
#                 for lat, lon in road.coordinates:
#                     dist = calculate_distance(target_lat, target_lon, lat, lon)
#                     if dist < 40:
#                         road_distances.append((osm_id, road, dist))
#                         break  # Avoid adding the same road multiple times

#         print(f"Lenght of roads: {len(road_distances)}")
#         # Sort by distance and keep top 5
#         closest_roads = sorted(road_distances, key=lambda x: x[2])[:5]

# ##############################################################################

        # Process only the closest 5 roads
        for osm_id, road in extractor.roads:
            print(f"Processing OSM ID {osm_id}: type={road.road_type}")
            type_coefficient = fuel_type_coefficients.get(road.road_type, 1.0)
            road_profile = self.create_road_profile(road)
            # Calculate priority multiplier
            multiplier = self.coefficient_processor.process_road_coefficient(road_profile)
            multiplier *= type_coefficient
            
            self.custom_model.add_priority_rule(osm_id, multiplier)
            print(f"Added rule: OSM ID {osm_id}, multiplier={multiplier:.2f}")
            break # this break for just one road (testing)

        self.custom_model.save_to_file()
