import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.graphhopper import GraphHopper
from .fuel import estimate_fuel_saved
from .models import Coordinate
from typing import Dict, Any

graphhopper = GraphHopper()

def get_routes(start: Coordinate, end: Coordinate, custom_model: Dict[str, Any]) -> Dict[str, Any]:
    default = graphhopper.request_route((start.lat, start.lon), (end.lat, end.lon))
    custom = graphhopper.request_route((start.lat, start.lon), (end.lat, end.lon), custom_model)
    return {"default": default, "custom": custom}

def extract_metrics(route: Dict[str, Any]) -> Dict[str, Any]:
    path = route["paths"][0]
    return {
        "distance": path["distance"],
        "time": path["time"],
        "osm_ids": path.get("details", {}).get("osm_id", [])
    }

def compare_and_compute(route1: Dict[str, Any], route2: Dict[str, Any]) -> Dict[str, Any]:
    m1 = extract_metrics(route1)
    m2 = extract_metrics(route2)
    fuel_saved = estimate_fuel_saved(m1["distance"], m2["distance"])
    percent_saved = (fuel_saved / (m1["distance"] / 1000 * 0.07)) * 100 if m1["distance"] else 0
    return {
        "default": m1,
        "custom": m2,
        "fuel_saving_liters": fuel_saved,
        "fuel_saving_percent": percent_saved,
        "distance_diff": m2["distance"] - m1["distance"],
        "time_diff": m2["time"] - m1["time"]
    }