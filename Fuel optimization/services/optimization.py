import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from typing import Dict, List
from models.custom_model import CustomModel
from models.road import Road, RoadExtractor
from services.api.tomtom_api import TomTomAPI
from services.api.tomorrow_io import TomorrowAPI
from services.fuel_analysis import FuelAnalyzer
from models.data_class import FuelPoint, RoadProfile
from services.RoadCoefficientProcessor import RoadCoefficientProcessor
from utils.geo import calculate_distance
from config.settings import settings

class FuelOptimizer:
    def __init__(self, verbose: int = settings.verbose):
        self.verbose = verbose
        self.tomtom_traffic = TomTomAPI()
        self.tomorrow_io = TomorrowAPI()
        self.extractor = RoadExtractor()
        self.fuel_analyzer = FuelAnalyzer(self.extractor)
        self.coefficient_processor = RoadCoefficientProcessor()
        self.custom_model = CustomModel()

    def _log(self, *args):
        if self.verbose > 0:
            print(*args)

    def compare_segments(self,segments1, segments2):
        """Find segments that differ between routes"""
        set1 = {s["osm_id"] for s in segments1}
        set2 = {s["osm_id"] for s in segments2}
        
        return {
            "only_in_default": list(set1 - set2),
            "only_in_custom": list(set2 - set1)
        }

    def compare_routes(self, route1, route2):
        """Compare two routes and return differences"""
        if not route1 or not route2:
            return None
            
        path1 = route1["paths"][0]
        path2 = route2["paths"][0]
        
        return {
            "distance_diff": path2["distance"] - path1["distance"],
            "time_diff": path2["time"] - path1["time"],
            "segment_diff": self.compare_segments(path1.get("segments", []), path2.get("segments", []))
        }

    def create_road_profile(self, road: Road) -> RoadProfile:
        # traffic = self.tomtom_traffic.get_or_fetch_traffic_by_road(road, 10)
        # weather = self.tomorrow_io.get_or_fetch_weather_by_road(road)
        traffic = None
        weather = None

        return RoadProfile.build_profile(
            road=road,
            traffic_data=traffic or {},
            weather_data=weather or {},
        )
    
    
    def group_points_by_road_id(self, roads_points: List[FuelPoint]) -> Dict[int, List[FuelPoint]]:
        grouped = {}
        for point in roads_points:
            road_id = point.road_profile.road.osm_id
            if road_id is not None:
                grouped.setdefault(road_id, []).append(point)
        return grouped

    def update_custom_model(self) -> None:
        self._log(f"length of road: {len(self.extractor.roads.values())}")
        # Load all roads
        fleet_profile = self.fuel_analyzer.analyze_fleet(700)
        fuel_type_coefficients = fleet_profile.average_attr_coefficients.get("road_type", {})
        self._log(f"Average Coefficients: {fleet_profile.average_attr_coefficients}")
        self._log(f"Median Coefficients: {fleet_profile.median_attr_coefficients}")
        points = fleet_profile.vehicles[0].fuel_points # try for just the first vehicle
        grouped_points = self.group_points_by_road_id(points)

############################Just to process few road that are close by#############################

#         # Define target point
#         target = (6.68787,80.388847)
#         # Compute distances from each road to the target point
#         road_distances = []
#         for osm_id, road in self.extractor.roads.items():
#             if road.coordinates:
#                 for lat, lon in road.coordinates:
#                     dist = calculate_distance(target[0], target[1], lat, lon)
#                     if dist < 100000:  # Only consider roads within 100 km
#                         road_distances.append((osm_id, road, dist))
#                         break  # Avoid adding the same road multiple times

#         self._log(f"Found {len(road_distances)} roads within 100000m of target point ({target[0]}, {target[1]})")
#         # Sort by distance and keep top 5
#         closest_roads = sorted(road_distances, key=lambda x: x[2])

# # ##############################################################################

        # # Process only the closest 5 roads
        for index, (osm_id, road) in enumerate(self.extractor.roads.items(), start=1): # (osm_id, road) in enumerate(self.extractor.roads.items(), start=1)
            self._log(f"Processing road {index}/{len(self.extractor.roads.items())}: OSM ID {osm_id}")
            type_coefficient = 1 # fuel_type_coefficients.get(road.road_type, 1.0)
            self._log(f"Road type coefficient: {type_coefficient}")
            road_profile = self.create_road_profile(road)
            
            # Calculate priority multiplier
            multiplier = self.coefficient_processor.process_road_coefficient(road_profile)
            multiplier *= type_coefficient

            self.custom_model.add_priority_rule(osm_id, multiplier)
            self._log(f"[{index}] Added rule: OSM ID {osm_id}, multiplier={multiplier}")

        self._log(f"Average Coefficients: {fleet_profile.average_attr_coefficients}")
        self._log(f"Median Coefficients: {fleet_profile.median_attr_coefficients}")

        self.custom_model.save_to_file()
