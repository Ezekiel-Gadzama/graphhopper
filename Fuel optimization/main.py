import json
from datetime import timedelta
from services.optimization import FuelOptimizer
from services.graphhopper import GraphHopper
from utils.visualization import visualize_route
from config.settings import settings

def main():
    # Define OSM IDs to process
    unique_osm_ids = [
        1391537230, 1391557173, 1391552083, 1391333467
        # 498126573, 498126585, 498126586, 498126562,
        # 240294599, 761483024, 46737021, 240294607
    ]

    # Initialize and run optimization
    optimizer = FuelOptimizer()
    
    # Update custom model with all OSM IDs at once (more efficient)
    optimizer.update_custom_model(unique_osm_ids)

    # Request route from GraphHopper
    start = (55.761368, 37.537752)  # Latitude, Longitude
    end = (55.669699, 37.626329)
    
    # Load the custom model that was just updated
    with open(settings.CUSTOM_MODEL_PATH) as f:
        custom_model = json.load(f)
    
    # Get optimized route
    graphhopper = GraphHopper(base_url=settings.GRAPHHOPPER_URL)
    route = graphhopper.request_route(
        start_coord=start,
        end_coord=end,
        custom_model=custom_model
    )

    # Process and display results
    if route and "paths" in route:
        print("\nRoute processing complete")
        print(f"Total distance: {route['paths'][0]['distance']/1000:.2f} km")
        print(f"Estimated time: {timedelta(seconds=route['paths'][0]['time']/1000)}")
        
        # Print important edges in the route
        print("\nKey road segments in route:")
        for i, edge in enumerate(route["paths"][0].get("details", {}).get("osm_id", [])[:5]):  # Show first 5
            print(f"Segment {i+1}: OSM ID {edge[2]} positions {edge[0]}-{edge[1]}")

    # Visualize the route
    visualize_route(
        location=start,
        route=route,
        custom_model=custom_model
    )

if __name__ == "__main__":
    main()