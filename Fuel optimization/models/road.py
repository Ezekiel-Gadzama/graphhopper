from typing import List, Dict, Tuple, Optional
import osmium, os
from utils.geo import calculate_distance
from config.settings import settings
from enum import Enum

class RoadType(str, Enum):
    MOTORWAY = "MOTORWAY"
    MOTORWAY_LINK = "MOTORWAY_LINK"
    TRUNK = "TRUNK"
    TRUNK_LINK = "TRUNK_LINK"
    PRIMARY = "PRIMARY"
    PRIMARY_LINK = "PRIMARY_LINK"
    PATH = "PATH"
    FOOTWAY = "FOOTWAY"
    SECONDARY = "SECONDARY"
    SECONDARY_LINK = "SECONDARY_LINK"
    TERTIARY = "TERTIARY"
    TERTIARY_LINK = "TERTIARY_LINK"
    CONSTRUCTION = "CONSTRUCTION"
    UNCLASSIFIED = "UNCLASSIFIED"
    RESIDENTIAL = "RESIDENTIAL"
    ROAD = "ROAD"
    SERVICE = "SERVICE"
    SERVICES = "SERVICES"
    STEPS = "STEPS"
    LIVING_STREET = "LIVING_STREET"
    TRACK = "TRACK"
    REST_AREA = "REST_AREA"
    PEDESTRIAN = "PEDESTRIAN"
    CYCLEWAY = "CYCLEWAY"
    RACEWAY = "RACEWAY"
    BRIDLEWAY = "BRIDLEWAY"
    STREET_LAMP = "STREET_LAMP"
    PLATFORM = "PLATFORM"
    PROPOSED = "PROPOSED"
    ABANDONED = "ABANDONED"
    ELEVATOR = "ELEVATOR"
    CORRIDOR = "CORRIDOR"
    VIA_FERRATA = "VIA_FERRATA"
    BUS_STOP = "BUS_STOP"
    SIDEWALK = "SIDEWALK"
    ESCAPE = "ESCAPE"
    EMERGENCY_ACCESS_POINT = "EMERGENCY_ACCESS_POINT"
    PLATFORM_BUS_STOP = "PLATFORM;BUS_STOP"
    YES = "YES"
    BUSWAY = "BUSWAY"
    UNKNOWN = "UNKNOWN"

class Road:
    def __init__(
        self,
        osm_id: int,
        coordinates: List[Tuple[float, float]],
        road_type: RoadType = RoadType.UNKNOWN,
        osm_tags: Optional[Dict[str, str]] = None,
        slope: Optional[list] = None
    ):
        self.osm_id = osm_id
        self.coordinates = coordinates
        self.road_type = road_type
        self.osm_tags = osm_tags or {}
        self.slope = slope or {}

    @property
    def length(self) -> float:
        total = 0.0
        for i in range(1, len(self.coordinates)):
            lat1, lon1 = self.coordinates[i - 1]
            lat2, lon2 = self.coordinates[i]
            total += calculate_distance(lat1, lon1, lat2, lon2)
        return total

class RoadExtractor(osmium.SimpleHandler):
    def __init__(self, target_osm_ids: Optional[List[int]] = None):
        super().__init__()
        from services.api.opentopodata import ElevationAPI  # optional

        self.target_osm_ids = set(target_osm_ids) if target_osm_ids else None
        self.roads = {}

        # Apply each file in the list
        for osm_path in settings.OSM_FILE_PATHS:
            if os.path.exists(osm_path):
                self.apply_file(osm_path, locations=True)
            else:
                print(f"OSM file not found: {osm_path}")

        # Optional: Elevation logic
        self.elevation = ElevationAPI()
        self.elevation.load_elevation_cache()
        self.elevation.fetch_missing_elevations(self.roads)
        self.assign_slopes()
        self.elevation.save_elevation_cache()

    def way(self, w) -> None:
        if 'highway' not in w.tags:
            return

        if self.target_osm_ids is None or w.id in self.target_osm_ids:
            coords = [(node.lat, node.lon) for node in w.nodes]
            road_type = w.tags.get("highway", "unknown")
            try:
                road_enum = RoadType(road_type.upper())
            except ValueError:
                road_enum = RoadType.UNKNOWN
            self.roads[w.id] = Road(w.id, coords, road_enum, dict(w.tags))

    def assign_slopes(self):
        for road in self.roads.values():
            coords = road.coordinates
            slopes = []
            for i in range(len(coords) - 1):
                lat1, lon1 = coords[i]
                lat2, lon2 = coords[i + 1]
                ele1 = self.elevation.get_elevation(lat1, lon1)
                ele2 = self.elevation.get_elevation(lat2, lon2)
                if ele1 is None or ele2 is None:
                    continue
                delta_elev = ele2 - ele1
                dist_km = self.elevation.haversine(lat1, lon1, lat2, lon2)
                dist_m = dist_km * 1000
                if dist_m > 0:
                    slope = (delta_elev / dist_m) * 100
                    slopes.append(slope)
            road.slope = slopes

