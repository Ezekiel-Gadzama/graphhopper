import folium
from branca.colormap import linear
from typing import Dict, Tuple
import os

def visualize_route(location: Tuple[float, float], route: Dict, custom_model: Dict,
                   output_file: str = "route_with_custom_model.html",
                   differences: Dict = None) -> None:
    # Convert coordinates to [lat, lon] format
    coords = [[p[1], p[0]] for p in route["paths"][0]["points"]["coordinates"]]
    
    # Create map centered on starting location
    m = folium.Map(location=[location[0], location[1]], zoom_start=13)

    # Draw the base route in blue
    folium.PolyLine(
        coords, 
        color='blue', 
        weight=5, 
        opacity=0.7, 
        tooltip="Default Route"
    ).add_to(m)

    # Add start and end markers
    start_coord = coords[0]
    end_coord = coords[-1]
    folium.Marker(
        start_coord,
        popup=f"Start: {start_coord[0]:.5f}, {start_coord[1]:.5f}",
        icon=folium.Icon(color='green', icon='play')
    ).add_to(m)
    
    folium.Marker(
        end_coord,
        popup=f"End: {end_coord[0]:.5f}, {end_coord[1]:.5f}",
        icon=folium.Icon(color='red', icon='stop')
    ).add_to(m)

    # Calculate route metrics
    distance_km = route["paths"][0]["distance"] / 1000
    duration_ms = route["paths"][0]["time"]
    duration_hours = int(duration_ms // 3600000)
    duration_minutes = int((duration_ms % 3600000) // 60000)

    # Create professional overlay HTML (same as before)
    info_html = f"""
    <div style="
        position: fixed;
        top: 10px;
        left: 10px;
        z-index: 1000;
        padding: 12px;
        background: white;
        border-radius: 6px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.1);
        font-family: Arial, sans-serif;
        width: 240px;
    ">
        <div style="
            border-bottom: 1px solid #eee;
            padding-bottom: 8px;
            margin-bottom: 8px;
        ">
            <span style="font-size: 16px; font-weight: bold;">Route Summary</span>
        </div>
        
        <div style="margin-bottom: 4px; font-size: 13px;">
            <span style="color: #666;">From:</span> {start_coord[0]:.5f}, {start_coord[1]:.5f}
        </div>
        <div style="margin-bottom: 8px; font-size: 13px;">
            <span style="color: #666;">To:</span> {end_coord[0]:.5f}, {end_coord[1]:.5f}
        </div>
        
        <div style="
            margin: 12px 0;
            padding: 8px 0;
            border-top: 1px solid #eee;
            border-bottom: 1px solid #eee;
        ">
            <div style="font-size: 18px; font-weight: bold; margin-bottom: 4px;">
                {duration_hours}h {duration_minutes}min
            </div>
            <div style="font-size: 18px; font-weight: bold;">
                {distance_km:.1f} km
            </div>
        </div>
        
        <div style="
            display: flex;
            justify-content: space-between;
            margin-top: 8px;
        ">
            <button style="
                padding: 6px 12px;
                background: #f8f9fa;
                border: 1px solid #ddd;
                border-radius: 4px;
                cursor: pointer;
                font-size: 13px;
            ">GPX</button>
            <button style="
                padding: 6px 12px;
                background: #f8f9fa;
                border: 1px solid #ddd;
                border-radius: 4px;
                cursor: pointer;
                font-size: 13px;
            ">Details</button>
        </div>
        
        <div style="
            margin-top: 12px;
            font-size: 11px;
            color: #999;
            text-align: right;
        ">
            Powered by GraphHopper
        </div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(info_html))

    # Highlight only the segments that are different
    folium.PolyLine(
        coords, 
        color='blue', 
        weight=5, 
        opacity=0.7, 
        tooltip="Default Route"
    ).add_to(m)

    # Highlight custom-only points if available
    if differences and "custom_only_points" in differences:
        for coord in differences["custom_only_points"]:
            lat, lon = coord[1], coord[0]  # Reverse from (lon, lat) to (lat, lon)
            folium.CircleMarker(
                location=[lat, lon],
                radius=5,
                color='red',
                fill=True,
                fill_opacity=0.9,
                popup=f"Custom-only Point: {lat:.5f}, {lon:.5f}"
            ).add_to(m)


    # Create output directory if it doesn't exist
    output_dir = os.path.abspath(os.path.join("Fuel optimization", "custom_model_route"))
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, output_file)
    
    # Save the map
    m.save(output_path)
    print(f"Map saved to: {output_path}")

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