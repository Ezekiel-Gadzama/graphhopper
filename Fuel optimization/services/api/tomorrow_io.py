import requests
from typing import Optional, Dict, Tuple, Any
from config.settings import settings
from models.data_class import WeatherData
from models.road import Road
class TomorrowAPI:
    
    cache_hits = 0
    
    def __init__(self, api_key: str = settings.TOMORROW_API_KEY, cache_resolution: float = 0.1, verbose: int = settings.verbose):
        self.api_key = api_key
        self.verbose = verbose
        self.cache_resolution = cache_resolution
        self.cache: Dict[Tuple[float, float], WeatherData] = {}
        
    def _log(self, *args):
        if self.verbose > 0:
            print(*args)

    def _round_coords(self, lat: float, lon: float) -> Tuple[float, float]:
        # Round coordinates to reduce API calls, e.g., one request per ~10km
        rounded_lat = round(lat / self.cache_resolution) * self.cache_resolution
        rounded_lon = round(lon / self.cache_resolution) * self.cache_resolution
        return (rounded_lat, rounded_lon)

    def _fetch_weather(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        url = "https://api.tomorrow.io/v4/weather/realtime"
        params = {
            "location": f"{lat},{lon}",
            "apikey": self.api_key
        }

        try:
            response = requests.get(url, params=params)
            if response.status_code != 200:
                self._log(f"Failed to fetch weather for ({lat},{lon}): {response.status_code}")
                self._log(f"Full error response: {response.text}")
                return None

            json_data = response.json()
            if self.verbose > 1:
                print(json_data)
            return json_data
        except Exception as e:
            self._log(f"Exception fetching weather: {e}")
            return None
        
    def get_or_fetch_weather_by_road(self, road: Road):
        """Decoration function for getting traffic data via Road class"""
        return self.get_or_fetch_weather(road.coordinates[0][0], road.coordinates[0][1])

    def get_or_fetch_weather(self, lat: float, lon: float) -> Optional[Dict]:
        key = self._round_coords(lat, lon)

        if key in self.cache:
            self._log(f"Using cached weather for {key}")
            self.cache_hits += 1
            return self.cache[key]

        self._log(f"Fetching new weather for {key}")
        data = self._fetch_weather(lat=key[0], lon=key[1])
        if data:
            self.cache[key] = data
        return data

    def clear_cache(self):
        self.cache.clear()

    def stats(self):
        return {
            "cache_size": len(self.cache),
            "cache_hits": self.cache_hits
        }
