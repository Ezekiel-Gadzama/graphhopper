from typing import List, Tuple, Optional
import osmium

class Road:
    def __init__(self, osm_id: int, coordinates: List[Tuple[float, float]], road_type: str = "unknown"):
        self.osm_id = osm_id
        self.coordinates = coordinates
        self.road_type = road_type

class RoadExtractor(osmium.SimpleHandler):
    def __init__(self, target_osm_ids: Optional[List[int]] = None):
        super().__init__()
        self.target_osm_ids = set(target_osm_ids) if target_osm_ids else None
        self.roads = {}

    def way(self, w) -> None:
        if 'highway' not in w.tags:
            return  # Skip non-road elements

        if self.target_osm_ids is None or w.id in self.target_osm_ids:
            coords = [(node.lat, node.lon) for node in w.nodes]
            road_type = w.tags.get("highway", "unknown")
            self.roads[w.id] = Road(w.id, coords, road_type)