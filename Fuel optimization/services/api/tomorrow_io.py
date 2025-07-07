import requests
from typing import List, Tuple, Dict, Any
from config.settings import settings
from models.data_class import WeatherData

class TomorrowIO:
    BASE_URL = "https://api.tomorrow.io/v4/weather/forecast"
    
    def __init__(self, api_key: str = settings.TOMORROW_API_KEY):
        self.api_key = api_key
        self.cached_weather_data = None
        # Moscow bounding box coordinates (NW and SE corners)
        self.moscow_bbox = "55.9135,37.3656,55.5733,37.8584"

    def get_moscow_weather(self) -> Dict:
        """Get weather data for entire Moscow area in one API call"""
        params = {
            "apikey": self.api_key,
            "location": self.moscow_bbox,
            "timesteps": "current",
            "units": "metric",
            "fields": ["temperature", "precipitationIntensity", "weatherCode"]
        }
        
        response = requests.get(self.BASE_URL, params=params)
        response.raise_for_status()
        return response.json()

    def get_weather_data(self) -> Dict:
        """Get cached or fresh weather data for Moscow"""
        if not self.cached_weather_data:
            self.cached_weather_data = self.get_moscow_weather()
        return self.cached_weather_data