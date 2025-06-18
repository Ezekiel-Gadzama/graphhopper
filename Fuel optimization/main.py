import json
from services.optimization import FuelOptimizer
from services.graphhopper import GraphHopper
from utils.visualization import visualize_route
from config.settings import settings

def main():
    # Define OSM IDs to process
    unique_osm_ids = [
        498126573, 498126585, 498126586, 498126562,
        240294599, 761483024, 46737021, 240294607
    ]

    # Process optimization
    optimizer = FuelOptimizer()
    for osm_id in unique_osm_ids:
        optimizer.process_osm_id(osm_id)
    optimizer.save_custom_model()

    # Request route from GraphHopper
    start = (55.761368, 37.537752)
    end = (55.669699, 37.626329)
    
    with open(settings.CUSTOM_MODEL_PATH) as f:
        custom_model = json.load(f)
    
    graphhopper = GraphHopper()
    route = graphhopper.request_route(start, end, custom_model)

    if "paths" in route:
        print("Route processing complete")
        for edge in route["paths"][0].get("details", {}).get("osm_id", []):
            print(f"Edge: {edge[2]}")
            if edge[2] == 123456789:  # Example target ID
                print(f"⚠️ Found target OSM ID at positions {edge[0]}-{edge[1]}")

    visualize_route(start, route, custom_model)

if __name__ == "__main__":
    main()