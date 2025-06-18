import requests
from typing import List, Tuple, Dict, Any
from config.settings import settings
from models.data_class import WeatherData

class TomorrowIO:
    BASE_URL = "https://api.tomorrow.io/v4/weather/realtime"
    
    def __init__(self, api_key: str = settings.TOMORROW_API_KEY):
        self.api_key = api_key

    def get_weather_data(self, coords: List[Tuple[float, float]]) -> Dict[str, Any]:
        params = {
            "location": f"{coords[0][1]},{coords[0][0]}",
            "apikey": self.api_key
        }
        response = requests.get(self.BASE_URL, params=params)
        response.raise_for_status()
        return response.json()

    def extract_weather_data(self, raw_data: Dict[str, Any]) -> WeatherData:
        try:
            # Implement actual weather factor calculation based on your requirements
            weather_factor = 1.0  # Default value
            return WeatherData(weather_factor=weather_factor)
        except (KeyError, TypeError):
            return WeatherData(weather_factor=1.0)