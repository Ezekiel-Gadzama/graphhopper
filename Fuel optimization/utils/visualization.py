import folium
from branca.colormap import linear
from typing import Dict, List, Tuple

def visualize_route(location: Tuple[float, float], route: Dict, custom_model: Dict) -> None:
    m = folium.Map(location=[location[0], location[1]], zoom_start=13)
    
    # Extract coordinates
    coords = [[p[1], p[0]] for p in route["paths"][0]["points"]["coordinates"]]
    
    # Add base route
    folium.PolyLine(coords, color='blue', weight=5, opacity=0.7).add_to(m)
    
    # Highlight custom model effects
    if "details" in route["paths"][0] and "osm_id" in route["paths"][0]["details"]:
        target_osm_id, multiplier = _find_target_osm_id(custom_model)
        
        if target_osm_id:
            colormap = linear.RdYlGn_11.scale(0, 2)
            
            for edge in route["paths"][0]["details"]["osm_id"]:
                start_idx, end_idx, osm_id = edge
                segment = coords[start_idx:end_idx+1]
                
                if osm_id == target_osm_id:
                    _highlight_segment(m, segment, osm_id, multiplier)
    
    colormap.caption = "Priority Multiplier Effect"
    colormap.add_to(m)
    m.save("route_with_custom_model.html")

def _find_target_osm_id(custom_model: Dict) -> Tuple[int, float]:
    for stmt in custom_model.get("priority", []):
        if "osm_id" in stmt.get("if", ""):
            target_osm_id = int(stmt["if"].split("==")[1].strip())
            multiplier = stmt["multiply_by"]
            return target_osm_id, multiplier
    return None, None

def _highlight_segment(map_obj, segment, osm_id, multiplier):
    folium.PolyLine(
        segment,
        color='red',
        weight=10,
        opacity=0.9,
        popup=f"OSM ID: {osm_id} (Priority ×{multiplier})"
    ).add_to(map_obj)
    
    folium.Marker(
        segment[0],
        icon=folium.Icon(color='red', icon='info-sign'),
        popup=f"Custom model applied: Priority ×{multiplier}"
    ).add_to(map_obj)