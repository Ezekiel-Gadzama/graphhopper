import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from typing import Dict, List, Optional
from models.custom_model import CustomModel
from models.road import RoadExtractor, Road
from services.api.yandex_opentopo import YandexTrafficAndElevationAPI
from services.api.tomorrow_io import TomorrowIO
from services.fuel_analysis import FuelAnalyzer
from models.data_class import FuelPoint, RoadProfile
from services.RoadCoefficientProcessor import RoadCoefficientProcessor
from config.settings import settings

class FuelOptimizer:
    def __init__(self):
        self.traffic_slope_api = YandexTrafficAndElevationAPI()
        self.tomorrow_io = TomorrowIO()
        self.fuel_analyzer = FuelAnalyzer()
        self.coefficient_processor = RoadCoefficientProcessor()
        self.custom_model = CustomModel()

    def create_road_profile(self, road: Road) -> RoadProfile:
        traffic = self.traffic_slope_api.get_traffic(bbox="37.3,55.4,37.9,56.0")
        matching_traffic = self._find_matching_traffic(road, traffic)

        self.traffic_slope_api.fetch_moscow_slopes(road)
        slope = self.traffic_slope_api.get_slope_for_road(road)
        
        weather = self.tomorrow_io.get_weather_data()
        matching_weather = self._find_matching_weather(road, weather)

        return RoadProfile.from_osm_yandex_combined(
            road=road,
            traffic_data=matching_traffic or {},
            slope=slope,
            weather_data=matching_weather or {},
        )
    
    def _find_matching_traffic(self, road: Road, traffic: Dict) -> Dict:
        # Simplest strategy: pick first traffic feature whose polyline overlaps first coordinate
        for feat in traffic.get("features", []):
            coords = feat.get("geometry", {}).get("coordinates", [])
            if coords and (road.coordinates[0][::-1] in coords):
                props = feat.get("properties", {})
                return {
                    "jamFactor": props.get("jamFactor", 0.0),
                    "speed": props.get("speedKmH"),
                    "freeFlowSpeed": props.get("freeFlowSpeedKmH")
                }
        return {}

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
        extractor.apply_file(settings.OSM_FILE_PATH, locations=True)
        print(f"Number of Roads: {len(extractor.roads)}")
        fleet_profile = self.fuel_analyzer.analyze_fleet(700)
        fuel_type_coefficients = fleet_profile.median_coefficients
        print(f"Coefficients: {fuel_type_coefficients}")
        points = fleet_profile.vehicles[0].fuel_points # try for just the first vehicle
        grouped_points = self.group_points_by_road_id(points)
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
        for osm_id, road in list(extractor.roads.items()):
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
