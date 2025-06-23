from typing import List, Tuple
import osmium

class Road:
    def __init__(self, osm_id: int, coordinates: List[Tuple[float, float]], road_type: str = "unknown"):
        self.osm_id = osm_id
        self.coordinates = coordinates
        self.road_type = road_type

class RoadExtractor(osmium.SimpleHandler):
    def __init__(self, target_osm_ids: List[int]):
        super().__init__()
        self.target_osm_ids = set(target_osm_ids)
        self.roads = {}

    def way(self, w) -> None:
        if w.id in self.target_osm_ids:
            coords = [(node.lon, node.lat) for node in w.nodes]
            road_type = w.tags.get("highway", "unknown")
            self.roads[w.id] = Road(w.id, coords, road_type)