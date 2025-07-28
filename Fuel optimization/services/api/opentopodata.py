from typing import Dict, Optional
from models.road import Road
import time
import math
from requests_futures.sessions import FuturesSession
from config.settings import settings
import os
import json


class ElevationAPI:
    ELEVATION_URL = "https://api.opentopodata.org/v1/srtm90m"

    def __init__(self, verbose: int = settings.verbose):
        self.verbose = verbose
        self.elevation_map = {}
        self.elevation_file = "Fuel optimization/stored_data/osm_elevation.json"

    def _log(self, *args):
        if self.verbose > 0:
            print(*args)

    def format_key(self, lat: float, lon: float) -> str:
        return f"{lat:.7f},{lon:.7f}"

    def load_elevation_cache(self):
        if os.path.exists(self.elevation_file):
            with open(self.elevation_file, "r") as f:
                self.elevation_map = json.load(f)

    def save_elevation_cache(self):
        with open(self.elevation_file, "w") as f:
            json.dump(self.elevation_map, f, indent=2)

    def fetch_missing_elevations(self, roads: Dict[int, Road], batch_size=100, max_workers=1, delay=1.2):
        self._log("Fetching slope data for roads...")
        coords = list({
            (lat, lon)
            for road in roads.values()
            for lat, lon in road.coordinates
            if self.format_key(lat, lon) not in self.elevation_map
        })
        
        self._log(len(coords))
        if not coords:
            return

        session = FuturesSession(max_workers=max_workers)
        futures = []

        for i in range(0, len(coords), batch_size):
            self._log(f"Batch: {i}")
            batch = coords[i:i + batch_size]
            locations_str = "|".join(self.format_key(lat, lon) for lat, lon in batch)
            future = session.get(self.ELEVATION_URL, params={"locations": locations_str})
            futures.append((future, batch))
            time.sleep(delay)

        for future, batch in futures:
            try:
                resp = future.result()
                results = resp.json().get("results", [])
                for (lat, lon), result in zip(batch, results):
                    self.elevation_map[self.format_key(lat, lon)] = result["elevation"]
            except Exception as e:
                self._log(f"Elevation batch failed: {e}")

    def get_elevation(self, lat: float, lon: float) -> Optional[float]:
        return self.elevation_map.get(self.format_key(lat, lon))

    @staticmethod
    def haversine(lat1, lon1, lat2, lon2):
        R = 6371
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        d_phi = math.radians(lat2 - lat1)
        d_lambda = math.radians(lon2 - lon1)
        a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
        return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))
