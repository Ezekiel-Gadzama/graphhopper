import requests
from typing import Dict, Any, List, Tuple
from config.settings import settings
from models.road import Road
import time
import math


class YandexTrafficAndElevationAPI:
    TRAFFIC_URL = "https://api.routing.yandex.net/v2/traffic"
    ELEVATION_URL = "https://api.opentopodata.org/v1/srtm90m"

    def __init__(self, yandex_key: str = settings.YANDEX_API_KEY):
        self.yandex_key = yandex_key
        self.cached_traffic = None
        self.cached_elevation: Dict[str, float] = {}
        self.grid_coordinates: List[Tuple[float, float]] = []

    def get_traffic(self, bbox: str) -> Dict[str, Any]:
        if self.cached_traffic:
            return self.cached_traffic
        params = {"bbox": bbox, "apikey": self.yandex_key}
        resp = requests.get(self.TRAFFIC_URL, params=params)
        resp.raise_for_status()
        self.cached_traffic = resp.json()
        return self.cached_traffic

    def format_key(self, lat: float, lon: float) -> str:
        return f"{lat:.7f},{lon:.7f}"

import requests
from typing import Dict, Any, List, Tuple
from config.settings import settings
from models.road import Road
import time
import math


class YandexTrafficAndElevationAPI:
    TRAFFIC_URL = "https://api.routing.yandex.net/v2/traffic"
    ELEVATION_URL = "https://api.opentopodata.org/v1/srtm90m"

    def __init__(self, yandex_key: str = settings.YANDEX_API_KEY):
        self.yandex_key = yandex_key
        self.cached_traffic = None
        self.slope_cache: Dict[str, List[float]] = {}
        self.grid_coordinates: List[Tuple[float, float]] = []

    def get_traffic(self, bbox: str) -> Dict[str, Any]:
        if self.cached_traffic:
            return self.cached_traffic
        params = {"bbox": bbox, "apikey": self.yandex_key}
        resp = requests.get(self.TRAFFIC_URL, params=params)
        resp.raise_for_status()
        self.cached_traffic = resp.json()
        return self.cached_traffic

    def format_key(self, lat: float, lon: float) -> str:
        return f"{lat:.7f},{lon:.7f}"

    @staticmethod
    def haversine(lat1, lon1, lat2, lon2):
        """Calculate great-circle distance in kilometers."""
        R = 6371  # Radius of Earth in km
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        d_phi = math.radians(lat2 - lat1)
        d_lambda = math.radians(lon2 - lon1)
        a = math.sin(d_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2)**2
        return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

    def fetch_moscow_slopes(self, extractor, batch_size=100, delay_seconds=1.2):
        """Fetch elevation data and compute slope for roads in the extractor."""
        coords_set = set()
        for road in list(extractor.roads.values())[:100]:
            for lat, lon in road.coordinates:
                coords_set.add((lat, lon))

        coords = list(coords_set)
        print(f"Total unique coordinates: {len(coords)}")

        elevation_map: Dict[str, float] = {}

        # Fetch elevation in batches
        for i in range(0, len(coords), batch_size):
            batch = coords[i:i + batch_size]
            locations_str = "|".join(self.format_key(lat, lon) for lat, lon in batch)

            try:
                resp = requests.get(self.ELEVATION_URL, params={"locations": locations_str})
                resp.raise_for_status()
            except requests.exceptions.HTTPError as e:
                print(f"❌ Error fetching elevation for batch {i}-{i+batch_size}: {e}")
                break

            results = resp.json().get("results", [])
            for (lat, lon), result in zip(batch, results):
                key = self.format_key(lat, lon)
                elevation_map[key] = result["elevation"]

            time.sleep(delay_seconds)

        # Compute slopes per road and store in slope_cache
        for road in list(extractor.roads.values())[:100]:
            coords = road.coordinates
            slopes = []

            for i in range(len(coords) - 1):
                lat1, lon1 = coords[i]
                lat2, lon2 = coords[i + 1]
                key1 = self.format_key(lat1, lon1)
                key2 = self.format_key(lat2, lon2)

                if key1 not in elevation_map or key2 not in elevation_map:
                    continue

                ele1 = elevation_map[key1]
                ele2 = elevation_map[key2]
                delta_elevation = ele2 - ele1
                horizontal_dist_km = self.haversine(lat1, lon1, lat2, lon2)
                horizontal_dist_m = horizontal_dist_km * 1000

                if horizontal_dist_m > 0:
                    slope_percent = (delta_elevation / horizontal_dist_m) * 100
                    slopes.append(slope_percent)

            self.slope_cache[road.road_id] = slopes

    def get_slope_for_road(self, road: Road) -> Dict[str, float]:
        return self.slope_cache[road.osm_id]
