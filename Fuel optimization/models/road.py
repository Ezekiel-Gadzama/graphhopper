from typing import List, Dict, Tuple, Optional
import osmium
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
    UNKNOWN = "UNKNOWN"

class Road:
    def __init__(
        self,
        osm_id: int,
        coordinates: List[Tuple[float, float]],
        road_type: RoadType = RoadType.UNKNOWN,
        osm_tags: Optional[Dict[str, str]] = None
    ):
        self.osm_id = osm_id
        self.coordinates = coordinates
        self.road_type = road_type
        self.osm_tags = osm_tags or {}  # new field for storing tags

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
        self.target_osm_ids = set(target_osm_ids) if target_osm_ids else None
        self.roads = {}
        self.apply_file(settings.OSM_FILE_PATH, locations=True)

    def way(self, w) -> None:
        if 'highway' not in w.tags:
            return  # Skip non-road elements

        if self.target_osm_ids is None or w.id in self.target_osm_ids:
            coords = [(node.lat, node.lon) for node in w.nodes]
            road_type = w.tags.get("highway", "unknown")
            self.roads[w.id] = Road(w.id, coords, RoadType(road_type.upper()), dict(w.tags))