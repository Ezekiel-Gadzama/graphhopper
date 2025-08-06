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
        """Updates the routing model with fuel efficiency coefficients for each road type."""
        self._log(f"Total roads loaded: {len(self.extractor.roads.values())}")
        
        # Generate fleet-wide fuel consumption profiles (700 days of historical data)
        fleet_profile = self.fuel_analyzer.analyze_fleet(700)
        fuel_type_coefficients = fleet_profile.average_attr_coefficients.get("road_type", {})
        
        self._log(f"Average road coefficients: {fleet_profile.average_attr_coefficients}")
        self._log(f"Median road coefficients: {fleet_profile.median_attr_coefficients}")
        
        # Use first vehicle's data as sample implementation
        points = fleet_profile.vehicles[0].fuel_points
        grouped_points = self.group_points_by_road_id(points)

        # Implementation note:
        # Original plan was to assign coefficients per OSM_ID for dynamic adjustments (traffic/weather).
        # We modified GraphHopper to support osm_id in conditions:
        #   {"if": "osm_id == 12345", "multiply_by": 1.3}
        #
        # Challenges:
        # 1. Large custom model files (~40MB) exceed Janino's 64KB expression limit
        # 2. FreeMarker branch partially solves this by converting to Java classes, but:
        #    - Incomplete integration with our osm_id modifications
        #    - Fails on complex conditions like "osm_id == 12345"
        #
        # Current solution:
        # Using 'final-branch' branch which works with road_class level coefficients and other default grahhopper osm tags
        # Future work needed to complete FreeMarker integration for per-road optimization
        # self.custom_model.save_to_file()
