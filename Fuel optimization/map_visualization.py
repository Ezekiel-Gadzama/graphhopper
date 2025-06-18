import folium
from branca.colormap import linear

def visualize_route_with_custom_model(location, route, custom_model):
    # Create map
    m = folium.Map(location=[location[0], location[1]], zoom_start=13)
    
    # Extract coordinates
    coords = [[p[1], p[0]] for p in route["paths"][0]["points"]["coordinates"]]
    
    # Add base route
    folium.PolyLine(coords, color='blue', weight=5, opacity=0.7).add_to(m)
    
    # Highlight custom model effects
    if "details" in route["paths"][0] and "osm_id" in route["paths"][0]["details"]:
        # Get the OSM ID condition from your custom model
        target_osm_id = None
        for stmt in custom_model.get("priority", []):
            if "osm_id" in stmt.get("if", ""):
                target_osm_id = int(stmt["if"].split("==")[1].strip())
                multiplier = stmt["multiply_by"]
                break
        
        if target_osm_id:
            # Create color gradient for visual impact
            colormap = linear.RdYlGn_11.scale(0, 2)
            
            for edge in route["paths"][0]["details"]["osm_id"]:
                start_idx, end_idx, osm_id = edge
                segment = coords[start_idx:end_idx+1]
                
                if osm_id == target_osm_id:
                    # Highlight affected segment
                    folium.PolyLine(
                        segment,
                        color='red',
                        weight=10,
                        opacity=0.9,
                        popup=f"OSM ID: {osm_id} (Priority ×{multiplier})"
                    ).add_to(m)
                    
                    # Add marker at start
                    folium.Marker(
                        segment[0],
                        icon=folium.Icon(color='red', icon='info-sign'),
                        popup=f"Custom model applied: Priority ×{multiplier}"
                    ).add_to(m)

    # Add legend
    colormap.caption = "Priority Multiplier Effect"
    colormap.add_to(m)
    
    # Save map
    m.save("route_with_custom_model.html")
    print("✅ Map with custom model effects saved to route_with_custom_model.html")