from typing import Dict,List, Tuple
from models.road import Road
import time
import math
from requests_futures.sessions import FuturesSession
import os
import json


class ElevationAPI:
    ELEVATION_URL = "https://api.opentopodata.org/v1/srtm90m"

    def __init__(self, extractor):
        self.slope_cache: Dict[str, List[float]] = {}
        self.grid_coordinates: List[Tuple[float, float]] = []
        self.elevation_map = {}
        self.elevation_file = "elevation.json"
        self.load_elevation_cache()
        self.fetch_moscow_slopes(extractor)

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
    
    def load_elevation_cache(self):
        """Load cached elevation data from JSON file if it exists."""
        if os.path.exists(self.elevation_file):
            with open(self.elevation_file, "r") as f:
                self.elevation_map = json.load(f)
            print(f"Loaded cached elevation data with {len(self.elevation_map)} points.")
        else:
            self.elevation_map = {}

    def save_elevation_cache(self):
        """Save elevation data to JSON file."""
        with open(self.elevation_file, "w") as f:
            json.dump(self.elevation_map, f, indent=2)

    def fetch_moscow_slopes(self, extractor, batch_size=100, max_workers=1, delay_seconds=1.2):
        """Fetch elevation and compute slopes for roads, only downloading if not cached."""

        coords = list({
            (lat, lon)
            for road in list(extractor.roads.values())
            for lat, lon in road.coordinates
            if self.format_key(lat, lon) not in self.elevation_map
        })

        if coords:
            session = FuturesSession(max_workers=max_workers)
            futures = []

            for i in range(0, len(coords), batch_size):
                batch = coords[i:i + batch_size]
                locations_str = "|".join(self.format_key(lat, lon) for lat, lon in batch)
                future = session.get(self.ELEVATION_URL, params={"locations": locations_str})
                futures.append((future, batch))
                time.sleep(delay_seconds)

            for future, batch in futures:
                try:
                    resp = future.result()
                    results = resp.json().get("results", [])
                    for (lat, lon), result in zip(batch, results):
                        self.elevation_map[self.format_key(lat, lon)] = result["elevation"]
                except Exception as e:
                    print(f"Batch failed: {e}")

            self.save_elevation_cache()

        # Step 2: Compute slope per road
        for road in list(extractor.roads.values()):
            coords = road.coordinates
            slopes = []
            for i in range(len(coords) - 1):
                lat1, lon1 = coords[i]
                lat2, lon2 = coords[i + 1]
                key1 = self.format_key(lat1, lon1)
                key2 = self.format_key(lat2, lon2)

                if key1 not in self.elevation_map or key2 not in self.elevation_map:
                    continue

                ele1 = self.elevation_map[key1]
                ele2 = self.elevation_map[key2]
                delta_elevation = ele2 - ele1
                horizontal_dist_km = self.haversine(lat1, lon1, lat2, lon2)
                horizontal_dist_m = horizontal_dist_km * 1000

                if horizontal_dist_m > 0:
                    slope_percent = (delta_elevation / horizontal_dist_m) * 100
                    slopes.append(slope_percent)

            self.slope_cache[road.osm_id] = slopes

            
    def get_slope_for_road(self, road: Road) -> List[float]:
        return self.slope_cache[road.osm_id]
