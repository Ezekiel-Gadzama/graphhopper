import requests, json
from typing import List, Dict, Any
from config.settings import settings

class GraphHopper:
    def __init__(self, base_url: str = settings.GRAPHHOPPER_URL):
        self.base_url = base_url

    def request_route(self, start_coord: List[float], end_coord: List[float], custom_model: Dict[str, Any] = None) -> Dict[str, Any]:
        params = {
            "profile": "car",
            "locale": "en",
            "calc_points": True,
            "instructions": True,
            "ch.disable": True,
            "points": [
                [start_coord[1], start_coord[0]],  # Note: GraphHopper expects [lon, lat]
                [end_coord[1], end_coord[0]]
            ],
            "details": ["osm_id"],
            "points_encoded": False
        }

        if custom_model:
            params["custom_model"] = custom_model

        try:
            response = requests.post(self.base_url, json=params)
            
            # # Print full response details
            # print("\n=== Full Response ===")
            # print(f"Status Code: {response.status_code}")
            # print("Headers:")
            # for header, value in response.headers.items():
            #     print(f"  {header}: {value}")
            
            # print("\nBody:")
            # try:
            #     # Pretty-print JSON if possible
            #     print(json.dumps(response.json(), indent=2))
            # except ValueError:
            #     # Fallback to raw text if not JSON
            #     print(response.text)
            
            response.raise_for_status()  # Raise HTTP errors
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"\n=== Request Failed ===")
            # if hasattr(e, 'response') and e.response:
            #     print(f"Status Code: {e.response.status_code}")
            #     print("Error Body:")
            #     print(e.response.text)
            # print(f"Error: {str(e)}")
            return None