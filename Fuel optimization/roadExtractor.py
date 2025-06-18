import osmium
from generate_custom_model import factor_to_multiplier, write_custom_model
from here_traffic import get_traffic_flow_here_api, extract_jam_factor
from Tomorrow_io import get_weather_from_tomorrowIo_api, extract_weather_factor
from fuel_data import get_fuel_data

HERE_API_KEY = "YOUR_HERE_API_KEY"
TOMORROW_API_KEY = "YOUR_TOMORROW_API_KEY"
OSM_FILE = "moscow_tagged.osm.pbf"

# Now using actual OSM Way IDs (integers, not strings)
unique_osm_ids = [
    498126573, 498126585, 498126586, 498126562,
    240294599, 761483024, 46737021, 240294607
]

# Define the RoadExtractor class using OSM way ID
class RoadExtractor(osmium.SimpleHandler):
    def __init__(self, target_osm_ids):
        super().__init__()
        self.target_osm_ids = set(target_osm_ids)  # Use integer IDs
        self.roads = {}  # {osm_id: [(lon, lat), ...]}

    def way(self, w):
        if w.id in self.target_osm_ids:
            coords = [(node.lon, node.lat) for node in w.nodes]
            self.roads[w.id] = coords

def calculate_edge_weight_multipler(fuel_data, Jam_multiplier, weather_multipler):
    pass

# Main logic
for osm_id in unique_osm_ids:
    extractor = RoadExtractor([osm_id])
    extractor.apply_file(OSM_FILE, locations=True)

    if osm_id not in extractor.roads:
        print(f"No coordinates found for OSM ID {osm_id}. Skipping.")
        continue

    coords = extractor.roads[osm_id]
    print(f"Coordinates for {osm_id}: {coords}")

    traffic_data = get_traffic_flow_here_api(HERE_API_KEY, coords)
    jam_factor = extract_jam_factor(traffic_data)
    Jam_multiplier = factor_to_multiplier(jam_factor)
    weather_data = get_weather_from_tomorrowIo_api(TOMORROW_API_KEY, coords)
    weather_factor = extract_weather_factor(weather_data)
    weather_multipler = factor_to_multiplier(weather_factor)

    fuel_data = get_fuel_data(coords)
    edge_weight_multipler = calculate_edge_weight_multipler(fuel_data, Jam_multiplier, weather_multipler)


    write_custom_model(str(osm_id), edge_weight_multipler)
    print(f"Processed {osm_id}: Jam factor = {jam_factor}, Multiplier = {edge_weight_multipler}")
