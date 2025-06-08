import requests

def get_traffic_flow_here_api(api_key, coords):
    lon, lat = coords[0]  # First point on the road
    url = f"https://traffic.ls.hereapi.com/traffic/6.3/flow.json?prox={lat},{lon},100&apiKey={api_key}"
    response = requests.get(url)
    data = response.json()
    return data  # You can parse speed, jam factor, etc.
