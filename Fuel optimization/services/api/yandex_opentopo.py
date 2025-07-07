import requests
from typing import Dict, Any, List, Tuple
from config.settings import settings
from models.road import Road
import time


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

    def fetch_moscow_elevation_grid(self, extractor, batch_size=100, delay_seconds=1.2):
        """Fetch elevation data for all road coordinates in the extractor, without grid generation."""
        coords_set = set()
        for road in list(extractor.roads.values())[:100]:  # Limit to first 100 roads for testing
            for lat, lon in road.coordinates:
                key = self.format_key(lat, lon)
                if key not in self.cached_elevation:
                    coords_set.add((lat, lon))

        coords = list(coords_set)
        print(f"Total unique coordinates from extractor: {len(coords)}")

        for i in range(0, len(coords), batch_size):
            batch = coords[i:i + batch_size]
            locations_str = "|".join(self.format_key(lat, lon) for lat, lon in batch)

            try:
                resp = requests.get(self.ELEVATION_URL, params={"locations": locations_str})
                resp.raise_for_status()
            except requests.exceptions.HTTPError as e:
                print(f"Error fetching elevation for batch {i}-{i+batch_size}: {e}")
                break

            results = resp.json().get("results", [])
            for (lat, lon), result in zip(batch, results):
                key = self.format_key(lat, lon)
                self.cached_elevation[key] = result["elevation"]

            time.sleep(delay_seconds)

    def get_elevation_for_road(self, road: Road) -> Dict[str, float]:
        """Use exact 7-digit coordinate match from cached elevation."""
        elevation_points = []

        for lat, lon in road.coordinates:
            key = self.format_key(lat, lon)
            if key not in self.cached_elevation:
                print(f"⚠️ Missing elevation for: ({lat:.7f}, {lon:.7f})")
                continue
            elevation = self.cached_elevation[key]
            elevation_points.append(elevation)

        return {
            "elevation_points": elevation_points,
            "average_elevation": sum(elevation_points) / len(elevation_points) if elevation_points else 0.0,
            "max_elevation": max(elevation_points, default=0.0),
            "min_elevation": min(elevation_points, default=0.0),
        }
