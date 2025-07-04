import requests
from typing import List, Tuple, Dict, Any
from config.settings import settings
from models.data_class import TrafficData

class HereMapAPI:
    BASE_URL = "https://traffic.ls.hereapi.com/traffic/6.3/flow.json"
    
    def __init__(self, api_key: str = settings.HERE_API_KEY):
        self.api_key = api_key

    def get_traffic_flow(self, coords: List[Tuple[float, float]]) -> Dict[str, Any]:
        lon, lat = coords[0]
        params = {
            "prox": f"{lat},{lon},100",
            "apiKey": self.api_key
        }
        response = requests.get(self.BASE_URL, params=params)
        response.raise_for_status()
        return response.json()


    def extract_traffic_data(self, raw_data: Dict[str, Any]) -> TrafficData:
        try:
            flows = raw_data.get("RWS", [])[0].get("RW", [])[0].get("FIS", [])[0].get("FI", [])[0]
            jam_factor = flows.get("CF", [])[0].get("JF", 0)
            return TrafficData(jam_factor=jam_factor)
        except (IndexError, KeyError, TypeError):
            return TrafficData(jam_factor=0.0)
        

class HereTerrainAPI:
    BASE_URL = "https://traffic.ls.hereapi.com/traffic/6.3/flow.json"
    
    def __init__(self, api_key: str = settings.HERE_API_KEY):
        self.api_key = api_key

    def get_traffic_flow(self, coords: List[Tuple[float, float]]) -> Dict[str, Any]:
        lon, lat = coords[0]
        params = {
            "prox": f"{lat},{lon},100",
            "apiKey": self.api_key
        }
        response = requests.get(self.BASE_URL, params=params)
        response.raise_for_status()
        return response.json()


    def extract_traffic_data(self, raw_data: Dict[str, Any]) -> TrafficData:
        try:
            flows = raw_data.get("RWS", [])[0].get("RW", [])[0].get("FIS", [])[0].get("FI", [])[0]
            jam_factor = flows.get("CF", [])[0].get("JF", 0)
            return TrafficData(jam_factor=jam_factor)
        except (IndexError, KeyError, TypeError):
            return TrafficData(jam_factor=0.0)