import requests, json
from typing import List, Dict, Any
from config.settings import settings

class GraphHopper:
    def __init__(self, base_url: str = settings.GRAPHHOPPER_URL, verbose: int = settings.verbose):
        self.base_url = base_url
        self.verbose = verbose

    def _log(self, *args):
        if self.verbose > 0:
            print(*args)

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
            
            # Print full response details
            self._log("\n=== Full Response ===")
            self._log(f"Status Code: {response.status_code}")
            self._log("Headers:")
            for header, value in response.headers.items():
                self._log(f"  {header}: {value}")
            self._log("\nBody:")
            try:
                # Pretty-print JSON if possible
                self._log(json.dumps(response.json(), indent=2))
            except ValueError:
                # Fallback to raw text if not JSON
                self._log(response.text)
            response.raise_for_status()  # Raise HTTP errors
            return response.json()
            
        except requests.exceptions.RequestException as e:
            self._log(f"\n=== Request Failed ===")
            print()
            if hasattr(e, 'response') and e.response:
                self._log(f"Status Code: {e.response.status_code}")
                self._log("Error Body:")
                self._log(e.response.text)
            self._log(f"Error: {str(e)}")
            return None