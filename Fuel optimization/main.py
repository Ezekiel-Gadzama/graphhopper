import json
import random
import time
from datetime import timedelta
from typing import List, Dict, Any, Tuple
from services.optimization import FuelOptimizer
from services.graphhopper import GraphHopper
from utils.visualization import visualize_route 
import os

NUM_ROUTES = 10
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

def format_difference(value: float, unit: str = "km") -> str:
    """Format difference with appropriate sign"""
    if value >= 0:
        return f"+{abs(value):.2f} {unit}"
    else:
        return f"-{abs(value):.2f} {unit}"

def format_time_difference(ms_diff: float) -> str:
    """Format time difference in hh:mm:ss, handling negatives properly"""
    seconds_diff = ms_diff / 1000
    sign = "-" if seconds_diff < 0 else "+"
    abs_diff = abs(seconds_diff)
    
    hours = int(abs_diff // 3600)
    minutes = int((abs_diff % 3600) // 60)
    seconds = int(abs_diff % 60)
    
    return f"{sign}{hours:02d}:{minutes:02d}:{seconds:02d}"

def compare_routes(default_route: Dict[str, Any], custom_route: Dict[str, Any]) -> Dict[str, Any]:
    """Compare routes and extract custom-only points"""
    if not default_route or not custom_route or not default_route.get("paths") or not custom_route.get("paths"):
        return None

    path1 = default_route["paths"][0]
    path2 = custom_route["paths"][0]

    distance_diff = path2["distance"] - path1["distance"]
    time_diff = path2["time"] - path1["time"]

    # Get coordinate points
    default_coords = set(tuple(coord) for coord in path1["points"]["coordinates"])
    custom_coords = [tuple(coord) for coord in path2["points"]["coordinates"]]

    # Get only custom-only points
    custom_only_points = [coord for coord in custom_coords if coord not in default_coords]

    return {
        "distance_diff": distance_diff,
        "distance_diff_formatted": format_difference(distance_diff / 1000, "km"),
        "time_diff": time_diff,
        "time_diff_formatted": format_time_difference(time_diff),
        "custom_only_points": custom_only_points  # Point-level difference only
    }

def find_differing_segments(points1: List[List[float]], points2: List[List[float]]) -> Dict[str, List[Tuple[int, int]]]:
    """Find segments where the routes diverge by comparing coordinate sequences"""
    # Convert to tuples for comparison
    coords1 = [tuple(p) for p in points1]
    coords2 = [tuple(p) for p in points2]
    
    # Find the longest common subsequence
    lcs = []
    i = j = 0
    while i < len(coords1) and j < len(coords2):
        if coords1[i] == coords2[j]:
            lcs.append((i, j))
            i += 1
            j += 1
        elif coords1[i][0] < coords2[j][0] or (coords1[i][0] == coords2[j][0] and coords1[i][1] < coords2[j][1]):
            i += 1
        else:
            j += 1
    
    # Identify differing segments
    differing_segments = {"only_in_default": [], "only_in_custom": []}
    prev_i = prev_j = 0
    
    for match in lcs:
        i, j = match
        if i > prev_i:
            differing_segments["only_in_default"].append((prev_i, i-1))
        if j > prev_j:
            differing_segments["only_in_custom"].append((prev_j, j-1))
        prev_i, prev_j = i+1, j+1
    
    # Handle remaining segments after last match
    if prev_i < len(coords1):
        differing_segments["only_in_default"].append((prev_i, len(coords1)-1))
    if prev_j < len(coords2):
        differing_segments["only_in_custom"].append((prev_j, len(coords2)-1))
    
    return differing_segments

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
    #optimizer = FuelOptimizer()
    #optimizer.update_custom_model()
    #print("Custom model updated successfully.")
    
    # Load custom model
    with open("custom_model.json") as f:
        custom_model = json.load(f)
    
    results = {
        "with_differences": [],
        "no_differences": []
    }

    coord_generator = CoordinateGenerator(SRI_LANKA_BOUNDS)
    coordinate_pairs = coord_generator.get_valid_coordinate_pairs(NUM_ROUTES)
    
    # Define the output path once at the beginning
    output_dir = os.path.abspath("Fuel optimization")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "route_comparisons.json")

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

            # ✅ VISUALIZE AND SAVE ROUTE
            filename = f"route_for_{start[0]:.4f}_{start[1]:.4f}_to_{end[0]:.4f}_{end[1]:.4f}.html"
            print(f"Generating visualization: {filename}")
            visualize_route(start, custom_route, custom_model, output_file=filename, differences=comparison)
        else:
            results["no_differences"].append(result)
        
        # Save progress every 100 routes or at the end
        if (i + 1) % 100 == 0 or (i + 1) == len(coordinate_pairs):
            print(f"Processed {i + 1} routes...")
            with open(output_path, "w") as f:
                json.dump(results, f, indent=2)
        
        time.sleep(0.1)  # Rate limiting
    
    # Print summary
    print("\n=== Results Summary ===")
    print(f"Total routes processed: {len(coordinate_pairs)}")
    print(f"Routes with differences: {len(results['with_differences'])}")
    print(f"Routes without differences: {len(results['no_differences'])}")
    

    # Print all examples with differences
    if results["with_differences"]:
        print("\n=== Routes With Differences ===")
        for i, example in enumerate(results["with_differences"], 1):
            print(f"\n--- Route {i} ---")
            print(f"From {example['start']} to {example['end']}")
            print(f"Default: {example['default']['distance']/1000:.2f} km, {timedelta(seconds=example['default']['time']/1000)}")
            print(f"Custom: {example['custom']['distance']/1000:.2f} km, {timedelta(seconds=example['custom']['time']/1000)}")
            print(f"Distance difference: {example['differences']['distance_diff_formatted']}")
            print(f"Time difference: {example['differences']['time_diff_formatted']}")


    # Print all examples without differences
    if results["no_differences"]:
        print("\n=== Routes Without Differences ===")
        for i, example in enumerate(results["no_differences"], 1):
            print(f"\n--- Route {i} ---")
            print(f"From {example['start']} to {example['end']}")
            print(f"Distance: {example['default']['distance']/1000:.2f} km (same in both)")
            print(f"Time: {timedelta(seconds=example['default']['time']/1000)} (same in both)")

if __name__ == "__main__":
    main()