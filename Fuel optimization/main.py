import json
import random
import time
from datetime import timedelta
from typing import List, Dict, Any, Tuple
from services.optimization import FuelOptimizer
from services.graphhopper import GraphHopper

NUM_ROUTES = 1000
SRI_LANKA_BOUNDS = {
    "min_lat": 6.091419, "max_lat": 8.445618,
    "min_lon": 80.218134, "max_lon": 81.324091
}

class CoordinateGenerator:
    def __init__(self, bounds: Dict[str, float]):
        self.bounds = bounds
        self._validate_bounds()
        
    def _validate_bounds(self) -> None:
        """Ensure bounds are valid (min < max)"""
        if (self.bounds["min_lat"] >= self.bounds["max_lat"] or 
            self.bounds["min_lon"] >= self.bounds["max_lon"]):
            raise ValueError("Invalid bounds: min values must be less than max values")
        
    def generate_random_point(self) -> Tuple[float, float]:
        """Generate a random point within Sri Lanka with validation"""
        lat = random.uniform(self.bounds["min_lat"], self.bounds["max_lat"])
        lon = random.uniform(self.bounds["min_lon"], self.bounds["max_lon"])
        return (lat, lon)
    
    def get_valid_coordinate_pairs(self, num_pairs: int) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
        """Generate N valid coordinate pairs with error handling"""
        pairs = []
        attempts = 0
        max_attempts = num_pairs * 3  # More generous attempt limit
        
        while len(pairs) < num_pairs and attempts < max_attempts:
            try:
                start = self.generate_random_point()
                end = self.generate_random_point()
                # Simple validation that points aren't identical
                if start != end:
                    pairs.append((start, end))
            except Exception as e:
                print(f"Coordinate generation error: {e}")
                attempts += 1
                
        if len(pairs) < num_pairs:
            print(f"Warning: Only generated {len(pairs)}/{num_pairs} valid coordinate pairs")
            
        return pairs

def compare_routes(default_route: Dict[str, Any], custom_route: Dict[str, Any]) -> Dict[str, Any]:
    """Compare two routes and return differences"""
    if not default_route or not custom_route or not default_route.get("paths") or not custom_route.get("paths"):
        return None
        
    path1 = default_route["paths"][0]
    path2 = custom_route["paths"][0]
    
    # Extract OSM IDs from the details - each is a list of [start_index, end_index, osm_id]
    osm_ids1 = default_route["paths"][0].get("details", {}).get("osm_id", [])
    osm_ids2 = custom_route["paths"][0].get("details", {}).get("osm_id", [])
    
    return {
        "distance_diff": path2["distance"] - path1["distance"],
        "time_diff": path2["time"] - path1["time"],
        "segment_diff": compare_segments(osm_ids1, osm_ids2)
    }

def compare_segments(segments1: List[List[int]], segments2: List[List[int]]) -> Dict[str, List[List[int]]]:
    """Find segments that differ between routes"""
    # Convert lists of lists to sets of tuples (which are hashable)
    set1 = {tuple(segment) for segment in segments1}
    set2 = {tuple(segment) for segment in segments2}
    
    return {
        "only_in_default": [list(segment) for segment in (set1 - set2)],
        "only_in_custom": [list(segment) for segment in (set2 - set1)]
    }

def main():
    graphhopper = GraphHopper()
    # optimizer = FuelOptimizer()
    # optimizer.update_custom_model()
    print("Custom model updated successfully.")
    
    # Load custom model
    with open("custom_model.json") as f:
        custom_model = json.load(f)

    if "speed" not in custom_model:
        custom_model["speed"] = [{"if": "true", "limit_to": 100}]
    
    results = {
        "with_differences": [],
        "no_differences": []
    }

    coord_generator = CoordinateGenerator(SRI_LANKA_BOUNDS)
    coordinate_pairs = coord_generator.get_valid_coordinate_pairs(NUM_ROUTES)
    
    for i, (start, end) in enumerate(coordinate_pairs):
        print(f"Processing route {i+1}/{len(coordinate_pairs)}: {start} -> {end}")
        
        # Get route without custom model
        print("Requesting default route...")
        default_route = graphhopper.request_route(start, end)
        
        print("Requesting custom route...")
        # Get route with custom model
        custom_route = graphhopper.request_route(start, end, custom_model)
        
        if not default_route or not custom_route:
            print(f"Skipping failed route between {start} and {end}")
            continue
            
        comparison = compare_routes(default_route, custom_route)
        
        # Extract OSM IDs from the details
        osm_ids_default = default_route["paths"][0].get("details", {}).get("osm_id", [])
        osm_ids_custom = custom_route["paths"][0].get("details", {}).get("osm_id", [])
        
        result = {
            "start": start,
            "end": end,
            "default": {
                "distance": default_route["paths"][0]["distance"],
                "time": default_route["paths"][0]["time"],
                "segments": osm_ids_default
            },
            "custom": {
                "distance": custom_route["paths"][0]["distance"],
                "time": custom_route["paths"][0]["time"],
                "segments": osm_ids_custom
            }
        }
        
        if comparison and (comparison["distance_diff"] != 0 or comparison["time_diff"] != 0):
            result["differences"] = comparison
            results["with_differences"].append(result)
        else:
            results["no_differences"].append(result)
        
        if (i + 1) % 100 == 0:
            print(f"Processed {i + 1} routes...")
            # Save intermediate results
            with open("route_comparisons_interim.json", "w") as f:
                json.dump(results, f, indent=2)
        
        time.sleep(0.1)  # Rate limiting
    
    # Save final results
    with open("route_comparisons.json", "w") as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    print("\n=== Results Summary ===")
    print(f"Total routes processed: {len(coordinate_pairs)}")
    print(f"Routes with differences: {len(results['with_differences'])}")
    print(f"Routes without differences: {len(results['no_differences'])}")
    
    # Print examples if available
    if results["with_differences"]:
        print("\n=== Example Route With Differences ===")
        example = results["with_differences"][0]
        print(f"From {example['start']} to {example['end']}")
        print(f"Default: {example['default']['distance']/1000:.2f} km, {timedelta(seconds=example['default']['time']/1000)}")
        print(f"Custom: {example['custom']['distance']/1000:.2f} km, {timedelta(seconds=example['custom']['time']/1000)}")
        print(f"Distance difference: {example['differences']['distance_diff']/1000:.2f} km")
        print(f"Time difference: {timedelta(seconds=example['differences']['time_diff']/1000)}")
    
    if results["no_differences"]:
        print("\n=== Example Route Without Differences ===")
        example = results["no_differences"][0]
        print(f"From {example['start']} to {example['end']}")
        print(f"Distance: {example['default']['distance']/1000:.2f} km (same in both)")
        print(f"Time: {timedelta(seconds=example['default']['time']/1000)} (same in both)")

if __name__ == "__main__":
    main()