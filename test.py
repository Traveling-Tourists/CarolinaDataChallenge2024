# def plot_route_on_map(locations, route, mode, api_key='YOUR_API_KEY'):
#     """Plot the optimized route on a map using Folium."""
#     client = openrouteservice.Client(key=api_key)
#     coords = []
#     for idx in route:
#         loc = locations[idx]
#         coords.append((loc['lng'], loc['lat']))
#     # Get the route geometry from OpenRouteService
#     geometry = client.directions(
#         coordinates=coords,
#         profile=mode,
#         format='geojson'
#     )['features'][0]['geometry']
#     decoded_geometry = geometry['coordinates']

#     # Create a Folium map centered around the first location
#     start_loc = locations[route[0]]
#     m = folium.Map(location=[start_loc['lat'], start_loc['lng']], zoom_start=13)

#     # Add the route as a PolyLine
#     folium.PolyLine(
#         locations=[(lat, lng) for lng, lat in decoded_geometry],
#         weight=5,
#         color='blue',
#         opacity=0.8
#     ).add_to(m)

#     # Add markers for each location
#     for idx in route:
#         loc = locations[idx]
#         if 'category' in loc:
#             if loc['category'] == 'restaurant':
#                 icon_color = 'blue'
#             elif loc['category'] == 'start':
#                 icon_color = 'red'
#             else:
#                 icon_color = 'green'
#         else:
#             icon_color = 'green'
#             loc['category'] = 'start'
#         folium.Marker(
#             [loc['lat'], loc['lng']],
#             popup=f"{loc['name']} ({loc['category']})",
#             icon=folium.Icon(color=icon_color)
#         ).add_to(m)

#     # Save the map to an HTML file
#     m.save('optimized_route.html')
#     print("\nMap has been saved to 'optimized_route.html'. Open this file to view the route.")

def plot_route_on_map(locations, route, mode, api_key='YOUR_API_KEY'):
    """Plot the optimized route on a map using Folium, including all top locations."""
    client = openrouteservice.Client(key=api_key)
    
    # Get coordinates of locations in the route
    coords = []
    for idx in route:
        loc = locations[idx]
        coords.append((loc['lng'], loc['lat']))
    
    # Get the route geometry from OpenRouteService
    geometry = client.directions(
        coordinates=coords,
        profile=mode,
        format='geojson'
    )['features'][0]['geometry']
    decoded_geometry = geometry['coordinates']

    # Create a Folium map centered around the first location in the route
    start_loc = locations[route[0]]
    m = folium.Map(location=[start_loc['lat'], start_loc['lng']], zoom_start=13)

    # Add the route as a PolyLine
    folium.PolyLine(
        locations=[(lat, lng) for lng, lat in decoded_geometry],
        weight=5,
        color='blue',
        opacity=0.8
    ).add_to(m)

    # Add markers for visited locations (in the route)
    for idx in route:
        loc = locations[idx]
        icon_color = 'red' if loc.get('category') == 'start' else 'green'
        folium.Marker(
            [loc['lat'], loc['lng']],
            popup=f"{loc['name']} - Visited",
            icon=folium.Icon(color=icon_color)
        ).add_to(m)

    # Add markers for all locations (including non-visited)
    for idx, loc in enumerate(locations):
        if idx not in route:
            icon_color = 'gray'  # Different color for non-visited locations
            folium.Marker(
                [loc['lat'], loc['lng']],
                popup=f"{loc['name']} ({loc['category']}) - Not Visited",
                icon=folium.Icon(color=icon_color)
            ).add_to(m)

    # Save the map to an HTML file
    m.save('optimized_route.html')
    print("\nMap has been saved to 'optimized_route.html'. Open this file to view the route.")

