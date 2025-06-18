import requests
from typing import List, Dict, Any
from config.settings import settings

class GraphHopper:
    def __init__(self, base_url: str = settings.GRAPHHOPPER_URL):
        self.base_url = base_url

    def request_route(self, start_coords: List[float], end_coords: List[float], custom_model: Dict[str, Any]) -> Dict[str, Any]:
        params = {
            "profile": "car",
            "locale": "en",
            "calc_points": True,
            "instructions": True,
            "custom_model": custom_model,
            "ch.disable": True,
            "points": [
                [start_coords[1], start_coords[0]],
                [end_coords[1], end_coords[0]]
            ],
            "details": ["osm_id"],
            "points_encoded": False
        }

        response = requests.post(self.base_url, json=params)
        response.raise_for_status()
        return response.json()