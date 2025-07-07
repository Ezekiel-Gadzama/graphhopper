import requests
from typing import Dict, Any
from config.settings import settings
from models.road import Road

class YandexTrafficAndElevationAPI:
    TRAFFIC_URL = "https://api.routing.yandex.net/v2/traffic"
    ELEVATION_URL = "https://api.opentopodata.org/v1/srtm90m"

    def __init__(self, yandex_key: str = settings.YANDEX_API_KEY):
        self.yandex_key = yandex_key
        self.cached_traffic = None
        self.cached_elevation = {}

    def get_traffic(self, bbox: str) -> Dict[str, Any]:
        """Fetch traffic flow in bounding box: 'left,bottom,right,top' (lon/lat)."""
        if self.cached_traffic:
            return self.cached_traffic
        params = {"bbox": bbox, "apikey": self.yandex_key}
        resp = requests.get(self.TRAFFIC_URL, params=params)
        resp.raise_for_status()
        self.cached_traffic = resp.json()
        return self.cached_traffic

    def get_elevation(self, lat: float, lon: float) -> float:
        """Fetch elevation via OpenTopoData."""
        key = f"{lat:.4f},{lon:.4f}"
        if key in self.cached_elevation:
            return self.cached_elevation[key]
        resp = requests.get(self.ELEVATION_URL, params={"locations": key})
        resp.raise_for_status()
        result = resp.json()["results"][0]["elevation"]
        self.cached_elevation[key] = result
        return result

    def get_elevation_for_road(self, road: Road):
        el_points = [self.get_elevation(lat, lon) for lat, lon in road.coordinates]
        return {
            "elevation_points": el_points,
            "average_elevation": sum(el_points) / len(el_points) if el_points else 0.0,
            "max_elevation": max(el_points, default=0.0),
            "min_elevation": min(el_points, default=0.0),
        }
