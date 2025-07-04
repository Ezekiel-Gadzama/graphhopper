import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from typing import Dict, List
from models.custom_model import CustomModel
from models.road import RoadExtractor, Road
from services.api.here_api import HereMapAPI, HereTerrainAPI
from services.api.tomorrow_io import TomorrowIO
from services.fuel_analysis import FuelAnalyzer
from config.settings import settings
from models.data_class import FuelPoint, RoadProfile
from utils.geo import calculate_distance

class FuelOptimizer:
    def __init__(self):
        self.here_map_api = HereMapAPI()
        self.here_terrain_api = HereTerrainAPI()
        self.tomorrow_io = TomorrowIO()
        self.fuel_analyzer = FuelAnalyzer()
        self.custom_model = CustomModel()
        self.fleet_profile = self.fuel_analyzer.analyze_fleet(300)
        self.fuel_type_coefficients = self.fleet_profile.median_coefficients
    
    def process_Unique_road_fuel_weight(self, roadProfile: RoadProfile) -> float:
        # Analyze it and get a fuel coefficent multupler

        return 1.0
    
    def calculate_edge_weight_multiplier(
        self,
        fuel_multiplier: float,
        jam_multiplier: float, 
        weather_multiplier: float
        ) -> float:
            return fuel_multiplier * jam_multiplier * weather_multiplier
    
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
        points = self.fleet_profile.vehicles[0].fuel_points # try for just the first vehicle
        grouped_points = self.group_points_by_road_id(points)
        print(f"Coefficients: {self.fuel_type_coefficients}")
        print(f"grouped points: {grouped_points}")
        print(f"Invalid agents: {self.fuel_analyzer.invalid_agents}")

############################Just to process few road that are close bye#############################

        # Define target point
        target_lat = 55.470371
        target_lon = 37.572002
        # Compute distances from each road to the target point
        road_distances = []
        for osm_id, road in extractor.roads.items():
            if road.coordinates:
                for lat, lon in road.coordinates:
                    dist = calculate_distance(target_lat, target_lon, lat, lon)
                    if dist < 1:
                        road_distances.append((osm_id, road, dist))
                        break  # Avoid adding the same road multiple times

        print(f"Lenght of roads: {len(road_distances)}")
        # Sort by distance and keep top 5
        closest_roads = sorted(road_distances, key=lambda x: x[2])[:5]

##############################################################################

        # Process only the closest 5 roads
        for osm_id, road in closest_roads:
            print(f"Processing OSM ID {osm_id}: type={road.road_type}")
            # fuel_multiplier = self.process_Unique_road_fuel_weight(grouped_points.get(osm_id, []))
            type_coefficient = self.fuel_type_coefficients.get(road.road_type, 1.0)

            # multiplier = self.calculate_edge_weight_multiplier(
            #     fuel_multiplier=fuel_multiplier,
            # )

            # multiplier = fuel_multiplier

            # self.custom_model.add_priority_rule(osm_id, multiplier)
            # print(f"Added rule: OSM ID {osm_id}, multiplier={multiplier:.2f}")

            break

        self.custom_model.save_to_file()
