import subprocess
import json
import requests

def generate_custom_model():
    print("🔄 Generating new custom_model.json...")
    subprocess.run(["python", "roadExtractor.py"], check=True)
    print("✅ custom_model.json generated.")

def request_route_from_graphhopper(start_coords, end_coords):
    with open("custom_model.json") as f:
        custom_model_data = json.load(f)

    # Base URL without query parameters
    url = "http://localhost:8989/route"
    
    # Request parameters (now in the POST body)
    params = {
        "profile": "car",
        "locale": "en",
        "calc_points": True,
        "instructions": True,
        "custom_model": custom_model_data,
        "ch.disable": True,
        "points": [
            [start_coords[1], start_coords[0]],  # Note: GraphHopper expects [lon, lat]
            [end_coords[1], end_coords[0]]
        ]
    }

    # Send POST with all parameters in the body
    response = requests.post(url, json=params)
    return response.json()

if __name__ == "__main__":
    start = (55.761368, 37.537752)
    end = (55.669699, 37.626329)

    route = request_route_from_graphhopper(start, end)
    print(json.dumps(route, indent=2))

