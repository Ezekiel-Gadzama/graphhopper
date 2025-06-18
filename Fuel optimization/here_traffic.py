import requests

def get_traffic_flow_here_api(api_key, coords):
    lon, lat = coords[0]  # First point on the road
    url = f"https://traffic.ls.hereapi.com/traffic/6.3/flow.json?prox={lat},{lon},100&apiKey={api_key}"
    response = requests.get(url)
    data = response.json()
    return data  # You can parse speed, jam factor, etc.

def extract_jam_factor(traffic_data):
    try:
        flows = traffic_data.get("RWS", [])[0].get("RW", [])[0].get("FIS", [])[0].get("FI", [])[0]
        jam_factor = flows.get("CF", [])[0].get("JF", 0)  # 'JF' = jam factor
        return jam_factor
    except (IndexError, KeyError, TypeError):
        print("Could not extract jam factor.")
        return 0.0
