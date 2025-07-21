import requests
from typing import Dict, List, Tuple, Optional
from config.settings import settings
from models.road import Road
from shapely.geometry import LineString, Point
from shapely.strtree import STRtree
import time


class TomTomAPI:

    cache_hits = 0

    def __init__(self, api_key: str = settings.TOMTOM_API_KEY):
        self.api_key = api_key
        self.segment_cache: List[Tuple[LineString, Dict]] = []
        self.segment_tree: Optional[STRtree] = None
        self.CACHE_DISTANCE_THRESHOLD = 0.005  # ~5 meters
        self.verbose = settings.verbose
        self._geometry_to_data: Dict[LineString, Dict] = {} # might be not needed

    def _log(self, *args):
        if self.verbose > 0:
            print(*args)

    def get_traffic_data_from_coords(self, lat=55.753630, lon=37.620070, zoom=10):
        """
        Returns:
            Dict['str', 'int']: coordinates, free flow, current speed, travel time, segment coords, time of data receival
        """
        url = f"https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/{zoom}/json"
        params = {
            'point': f"{lat},{lon}",
            'unit': 'KMPH',
            'key': self.api_key
        }

        response = requests.get(url, params=params)
        if response.status_code != 200:
            if self.verbose > 0:
                print(f"*!* Error for point ({lat},{lon}):", response.status_code)
            return None

        data = response.json().get('flowSegmentData', {})
        coords = data.get('coordinates', {}).get('coordinate', [])
        if not coords:
            self._log(f"*!* No segment geometry for ({lat},{lon})")
            return None

        return {
            'lat': lat,
            'lon': lon,
            'frc': data.get('frc'),
            'currentSpeed': data.get('currentSpeed'),
            'freeFlowSpeed': data.get('freeFlowSpeed'),
            'currentTravelTime': data.get('currentTravelTime'),
            'freeFlowTravelTime': data.get('freeFlowTravelTime'),
            'confidence': data.get('confidence'),
            'roadClosure': data.get('roadClosure'),
            'segmentCoordinates': coords,
            'received': time.time()
        }

    def _rebuild_segment_tree(self):
        valid_geoms = [seg[0] for seg in self.segment_cache if isinstance(seg[0], LineString)]
        self._geometry_to_data = {seg[0]: seg[1] for seg in self.segment_cache if isinstance(seg[0], LineString)}
        self.segment_tree = STRtree(valid_geoms) if valid_geoms else None


    def _find_cached_segment(self, lat: float, lon: float) -> Optional[Dict]:
        if not self.segment_cache or self.segment_tree is None:
            return None

        point = Point(lon, lat)
        try:
            candidates = self.segment_tree.query(point)
        except Exception as e:
            self._log("!! STRtree query error:", e)
            return None
        
        geoms = self.segment_tree.geometries  # This preserves order
        for idx in candidates:
            candidate_geom = geoms[idx]
            
            if not isinstance(candidate_geom, LineString):
                self._log("Not a Linestring")
                continue

            # Get corresponding data
            data = self._geometry_to_data.get(candidate_geom)
            if not data:
                self._log("No record")
                continue

            try:
                distance = candidate_geom.distance(point)
                self._log(f"→ Distance to segment: {distance:.8f}")
                if distance < self.CACHE_DISTANCE_THRESHOLD:
                    self.cache_hits += 1
                    return data
            except Exception as e:
                self._log(f"!! Geometry distance check failed: {e}")
                continue

        return None



    def get_or_fetch_traffic(self, lat: float, lon: float, zoom: int = 10) -> Optional[Dict]:
        """Fetches data for the closest road via cache or API request.

        Args:
            lat (float): latitude
            lon (float): longitude
            zoom (int, optional): map zoom. Defaults to 10.

        Returns:
            Optional[Dict]: Dict of traffic parameters
        """
        cached = self._find_cached_segment(lat, lon)
        if cached:
            self._log(f"Using cached segment for ({lat}, {lon})")
            return cached

        data = self.get_traffic_data_from_coords(lat, lon, zoom)
        if not data or not data.get('segmentCoordinates'):
            return None

        try:
            coords = data['segmentCoordinates']
            if not ('longitude' in coords[0] and 'latitude' in coords[0]):
                self._log(f"No lat/lon in coords: {coords[0]}")
                
            points = [(p['longitude'], p['latitude']) for p in coords if 'longitude' in p and 'latitude' in p]
            if len(points) < 2:
                self._log(f"*!* Not enough valid coordinates for LineString at ({lat},{lon})")
                return None

            segment_geom = LineString(points)
            self.segment_cache.append((segment_geom, data))
            self._rebuild_segment_tree()
            self._log(f"+ Cached new segment ({lat}, {lon})")
            return data

        except Exception as e:
            self._log(f"*!* Failed to create LineString: {e}")
            return None
        
    def get_or_fetch_traffic_by_road(self, road: Road, zoom=10):
        """Decoration function for getting traffic data via Road class"""
        return self.get_or_fetch_traffic(road.coordinates[0][0], road.coordinates[0][1], zoom)
    
    def clear_cache(self):
        self.segment_cache.clear()
        self.segment_tree = None
        self.cache_hits = 0

    def stats(self):
        return {
            "cache_size": len(self.segment_cache),
            "cache_hits": self.cache_hits
        }
