import requests
from typing import Dict, List, Tuple
from config.settings import settings
from .polyline import Polyline
from models.road import Road
from utils.geo import calculate_distance

class TomTomAPI:
    
    def __init__(self, api_key: str = settings.TOMTOM_API_KEY, zoom_level = 10):
        self.zoom_level = zoom_level
        self.api_key = api_key
        self.cached_traffic_data = None
        self.BASE_URL = f"https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/{zoom_level}/json"

    def get_traffic(self, latitude = 55.753630, longitude = 37.620070) -> Dict:
        """Get traffic data in one API call"""
        params = {
            'point': f"{latitude},{longitude}",
            'unit': 'KMPH',
            'key': self.api_key
        }
        
        response = requests.get(self.BASE_URL, params=params)
        if settings.verbose == 2:
            if response.status_code == 200:
                data = response.json()
                current_speed = data['flowSegmentData']['currentSpeed']
                free_flow_speed = data['flowSegmentData']['freeFlowSpeed']
                jam_factor = data['flowSegmentData']['confidence']

                print(f"Traffic data at {latitude}/{longitude}")
                print(f"Current Speed: {current_speed} km/h")
                print(f"Free Flow Speed: {free_flow_speed} km/h")
                print(f"Traffic Confidence: {jam_factor}")
            else:
                print("Error:", response.status_code, response.text)
        #response.raise_for_status()
        return response.json()

    def get_traffic_data(self) -> Dict:
        """Get cached or fresh traffic data"""
        if not self.cached_traffic_data:
            self.cached_traffic_data = self.get_traffic()
        print(f"Cached traffic data: {self.cached_traffic_data}")
        return self.cached_traffic_data