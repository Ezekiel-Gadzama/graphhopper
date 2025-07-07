import requests
from typing import Dict
from config.settings import settings

class HereMapAPI:
    BASE_URL = "https://traffic.ls.hereapi.com/traffic/6.3/flow.json"
    
    def __init__(self, api_key: str = settings.HERE_API_KEY):
        self.api_key = api_key
        self.cached_traffic_data = None

    def get_moscow_traffic(self) -> Dict:
        """Get traffic data for entire Moscow area in one API call"""
        params = {
            'apiKey': self.api_key,
            'bbox': '55.5733,37.3656;55.9135,37.8584',  # Moscow bounding box
            'responseattributes': 'sh,fc',  # shape and functional class
            'maxfunctionalclass': 3,  # include all road types
            'zoom': 10  # appropriate zoom level for city
        }
        
        response = requests.get(self.base_url, params=params)
        response.raise_for_status()
        return response.json()

    def get_traffic_data(self) -> Dict:
        """Get cached or fresh traffic data"""
        if not self.cached_traffic_data:
            self.cached_traffic_data = self.get_moscow_traffic()
        return self.cached_traffic_data
        
class HereTerrainAPI:
    BASE_URL = "https://router.hereapi.com/v8/route"  # Or the appropriate terrain/elevation API endpoint
    
    def __init__(self, api_key: str = settings.HERE_TERRAIN_API_KEY):
        self.api_key = api_key
        self.cached_terrain_data = None

    def get_moscow_terrain(self) -> Dict:
        """Get terrain data for entire Moscow area in one API call"""
        params = {
            'apiKey': self.api_key,
            'bbox': '55.5733,37.3656;55.9135,37.8584',  # Moscow bounding box
            'layers': 'terrain,elevation',  # Request terrain and elevation data
            'resolution': 'medium'  # Adjust based on your needs
        }
        
        response = requests.get(self.BASE_URL, params=params)
        response.raise_for_status()
        return response.json()

    def get_terrain_data(self) -> Dict:
        """Get cached or fresh terrain data"""
        if not self.cached_terrain_data:
            self.cached_terrain_data = self.get_moscow_terrain()
        return self.cached_terrain_data