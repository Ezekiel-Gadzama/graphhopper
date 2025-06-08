import osmium
from generate_custom_model import jam_factor_to_multiplier, write_custom_model
from here_traffic import get_traffic_flow_here_api

API_KEY = "YOUR_HERE_API_KEY"
OSM_FILE = "moscow_tagged.osm.pbf"

# You can load this dynamically or keep it static
unique_roads = ["road_00001", "road_00002", "road_00003"]

# Define the RoadExtractor class
class RoadExtractor(osmium.SimpleHandler):
    def __init__(self, target_road_ids):
        super().__init__()
        self.target_road_ids = set(target_road_ids)  # multiple road IDs
        self.roads = {}  # store coords by road_id

    def way(self, w):
        road_id = w.tags.get("road_id")
        if road_id in self.target_road_ids:
            print(road_id)
            coords = [(node.lon, node.lat) for node in w.nodes]
            print(coords)
            self.roads[road_id] = coords


# Dummy jam factor extractor (update according to HERE API response structure)
def extract_jam_factor(traffic_data):
    try:
        flows = traffic_data.get("RWS", [])[0].get("RW", [])[0].get("FIS", [])[0].get("FI", [])[0]
        jam_factor = flows.get("CF", [])[0].get("JF", 0)  # 'JF' = jam factor
        return jam_factor
    except (IndexError, KeyError, TypeError):
        print("Could not extract jam factor.")
        return 0.0

# Main logic
for road_id in unique_roads:
    extractor = RoadExtractor([road_id])  # pass a list of one element
    extractor.apply_file('filtered_roads.osm.pbf', locations=True)

    if road_id not in extractor.roads:
        print(f"No coordinates found for {road_id}. Skipping.")
        continue

    print(f"Coordinates for {road_id}: {extractor.roads[road_id]}")

    traffic_data = get_traffic_flow_here_api(API_KEY, extractor.coords)
    jam_factor = extract_jam_factor(traffic_data)
    multiplier = jam_factor_to_multiplier(jam_factor)

    write_custom_model(road_id, multiplier)
    print(f"Processed {road_id}: Jam factor = {jam_factor}, Multiplier = {multiplier}")

