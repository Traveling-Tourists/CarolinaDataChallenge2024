import requests
import pandas as pd
from tqdm import tqdm
import openrouteservice
import folium
from datetime import datetime, timedelta

CATEGORY_VISIT_DURATIONS = {
    'poi': 30,
    'restaurant': 60,
    'attraction': 60,
    'accommodation': 60
}

def fetch_places(city, categories):
    url = 'http://tour-pedia.org/api/getPlaces'
    places = []
    for category in tqdm(categories, desc="Processing Categories"):
        params = {'location': city, 'category': category.strip()}
        response = requests.get(url, params=params)
        if response.status_code == 200:
            places.extend(response.json())

    df = pd.DataFrame(places)
    
    df_clean = df.dropna(subset=['numReviews'])
    
    return df_clean

def normalize_series(series):
    """Normalize a pandas Series using min-max normalization."""
    min_val = series.min()
    max_val = series.max()
    if max_val - min_val == 0:
        return series - min_val
    return (series - min_val) / (max_val - min_val)

def compute_scores(df):
    """Compute normalized scores and overall score for each location."""

    df['normalized_polarity'] = normalize_series(df['polarity'])
    df['normalized_numReviews'] = normalize_series(df['numReviews'])

    df['overall_score'] = 0.7 * df['normalized_polarity'] + 1.5 * df['normalized_numReviews']

    return df

def compute_scores_underground(df):
    """
    Compute normalized scores and overall score for each location,
    favoring high polarity and low number of reviews.
    """

    df['normalized_polarity'] = normalize_series(df['polarity'])
    df['normalized_numReviews'] = normalize_series(df['numReviews'])
    df['normalized_numReviews_inverse'] = 1 - df['normalized_numReviews']
    
    df['overall_score'] = 0.7 * df['normalized_polarity'] + 0.3 * df['normalized_numReviews_inverse']
    
    return df

def remove_traps(df):
    

def select_top_locations(df, user_prefs, N=20):
    """Select top N locations based on the overall score and user preferences.
    
    If 'restaurant' is among the categories, ensure that the number of restaurants
    selected is between min_restaurants and max_restaurants.
    """

    df = df[
        (df['polarity'] >= user_prefs['min_polarity']) &
        (df['numReviews'] >= user_prefs['min_num_reviews'])
    ]

    has_restaurant = 'restaurant' in [cat.lower() for cat in user_prefs['categories']]
    
    if has_restaurant:
        min_rest = user_prefs.get('min_restaurants', 2)
        max_rest = user_prefs.get('max_restaurants', 2)
        
        df_restaurants = df[df['category'].str.lower() == 'restaurant']
        df_non_restaurants = df[df['category'].str.lower() != 'restaurant']
        
        available_rest = len(df_restaurants)
        if available_rest < min_rest:
            print(f"Only {available_rest} restaurants available, which is less than the minimum required ({min_rest}).")
            selected_restaurants = df_restaurants
        else:
            selected_restaurants = df_restaurants.sort_values(by='overall_score', ascending=False).head(max_rest)
        
        remaining_slots = N - len(selected_restaurants)
        selected_non_restaurants = df_non_restaurants.sort_values(by='overall_score', ascending=False).head(remaining_slots)
        
        df_top = pd.concat([selected_restaurants, selected_non_restaurants]).drop_duplicates().reset_index(drop=True)
        
        actual_rest = len(df_top[df_top['category'].str.lower() == 'restaurant'])
        if actual_rest < min_rest:
            print(f"Warning: Only {actual_rest} restaurants selected, which is less than the desired minimum ({min_rest}).")
    else:
        df_top = df.sort_values(by='overall_score', ascending=False).head(N)
    
    return df_top

def prepare_locations(df_top, user_prefs):
    """Prepare locations list including the start location."""
    start_location = {
        'id': 'start',
        'name': 'Start Location',
        'lat': user_prefs['start_lat'],
        'lng': user_prefs['start_lng'],
        'visit_duration': 0,
        'category': 'start',
        'numReviews': 0,
        'polarity': 0
    }
    locations = [start_location]
    for index, row in df_top.iterrows():
        category = row['category'].lower()
        visit_duration = CATEGORY_VISIT_DURATIONS.get(category, 30)
        loc = {
            'id': row['id'],
            'name': row['name'],
            'lat': row['lat'],
            'lng': row['lng'],
            'visit_duration': visit_duration,
            'category': row['category'],
            'numReviews': int(row['numReviews']) if not pd.isna(row['numReviews']) else 0,
            'polarity': float(row['polarity']) if not pd.isna(row['polarity']) else 0.0
        }
        locations.append(loc)
    return locations

def solve_with_ors_optimization(locations, user_prefs, api_key):
    """Solve the routing problem using ORS optimization endpoint."""
    jobs = []
    job_id_to_location_idx = {}
    start_time_seconds = user_prefs['start_time'] * 60
    end_time_seconds = user_prefs['end_time'] * 60
    for idx, loc in enumerate(locations[1:], start=1):
        job = {
            'id': idx,
            'location': [loc['lng'], loc['lat']],
            'service': loc['visit_duration'] * 60,
            'time_windows': [[start_time_seconds, end_time_seconds]],
            'skills': [1]
        }
        jobs.append(job)
        job_id_to_location_idx[idx] = idx

    vehicle = {
        'id': 1,
        'profile': user_prefs['mode_of_travel'],
        'start': [user_prefs['start_lng'], user_prefs['start_lat']],
        'end': [user_prefs['start_lng'], user_prefs['start_lat']],
        'time_window': [start_time_seconds, end_time_seconds],
        'capacity': [4],
        'skills': [1, 14]
    }

    request_json = {
        'jobs': jobs,
        'vehicles': [vehicle]
    }

    url = 'https://api.openrouteservice.org/optimization'
    headers = {
        'Authorization': api_key,
        'Content-Type': 'application/json'
    }
    response = requests.post(url, json=request_json, headers=headers)

    if response.status_code == 200:
        data = response.json()

        if data.get('code') != 0:
            print("ORS Optimization API returned an error:", data.get('error'))
            return None, None

        route = []
        steps_info = []
        for route_obj in data.get('routes', []):
            vehicle_id = route_obj.get('vehicle')
            steps = route_obj.get('steps', [])
            for step in steps:
                step_type = step.get('type')
                if step_type in ['start', 'end', 'job']:
                    step_id = step.get('id')
                    arrival = step.get('arrival')  # in seconds
                    duration = step.get('duration')  # in seconds
                    if step_type == 'job':
                        loc_idx = job_id_to_location_idx.get(step_id, 0)
                    else:
                        loc_idx = 0
                    steps_info.append({
                        'type': step_type,
                        'location_idx': loc_idx,
                        'arrival': arrival
                    })
                    route.append(loc_idx)
        return route, steps_info
    else:
        print("ORS Optimization API error:", response.text)
        return None, None

def seconds_to_time(seconds):
    """Convert seconds since midnight to HH:MM format."""
    time = (datetime.combine(datetime.today(), datetime.min.time()) + timedelta(seconds=seconds)).time()
    return time.strftime("%H:%M")

def print_solution(locations, steps_info, user_prefs):
    """Print the solution with arrival times."""
    result = ''
    print('\nOptimized Itinerary:')
    result += '\nOptimized Itinerary:\n'
    for step in steps_info:
        loc_idx = step['location_idx']
        loc = locations[loc_idx]
        arrival_time = seconds_to_time(step['arrival'])
        if step['type'] == 'start':
            print(f"{loc['name']} (Start Time: {arrival_time}) -> ", end='')
            result += f"{loc['name']} (Start Time: {arrival_time}) -> "
        elif step['type'] == 'job':
            print(f"{loc['name']} (Arrival: {arrival_time}) -> ", end='')
            result += f"{loc['name']} (Arrival: {arrival_time}) -> "
        elif step['type'] == 'end':
            print(f"{loc['name']} (End Time: {arrival_time})")
            result += f"{loc['name']} (End Time: {arrival_time})"

    unique_locations = set([step['location_idx'] for step in steps_info if step['type'] == 'job'])
    print(f"Total number of locations visited: {len(unique_locations)}")

    result += f"\nTotal number of locations visited: {len(unique_locations)}"
    return result

def plot_route_on_map(locations, steps_info, mode, api_key='YOUR_API_KEY'):
    """Plot the optimized route on a map using Folium, including all top locations."""
    client = openrouteservice.Client(key=api_key)
    

    coords = []
    for step in steps_info:
        loc_idx = step['location_idx']
        loc = locations[loc_idx]
        coords.append((loc['lng'], loc['lat']))
    

    unique_coords = [coords[0]]
    for coord in coords[1:]:
        if coord != unique_coords[-1]:
            unique_coords.append(coord)
    
    try:
        geometry = client.directions(
            coordinates=unique_coords,
            profile=mode,
            format='geojson'
        )['features'][0]['geometry']
        decoded_geometry = geometry['coordinates']
    except Exception as e:
        print("Error fetching directions from ORS:", e)
        decoded_geometry = []

    start_loc = locations[0]
    m = folium.Map(location=[start_loc['lat'], start_loc['lng']], zoom_start=13)

    if decoded_geometry:
        folium.PolyLine(
            locations=[(lat, lng) for lng, lat in decoded_geometry],
            weight=5,
            color='blue',
            opacity=0.8
        ).add_to(m)

    for step in steps_info:
        loc_idx = step['location_idx']
        loc = locations[loc_idx]
        if step['type'] == 'start':
            icon_color = 'red'
            popup_text = f"<b>{loc['name']}</b> (Start)"
        elif step['type'] == 'end':
            icon_color = 'red'
            popup_text = f"<b>{loc['name']}</b> (End)"
        elif loc['category'].lower() == 'restaurant':
            icon_color = 'blue'
            popup_text = (
                f"<b>{loc['name']}</b> (Restaurant)<br>"
                f"Reviews: {loc['numReviews']}<br>"
                f"Polarity: {loc['polarity']}"
            )
        else:
            icon_color = 'green'
            popup_text = (
                f"<b>{loc['name']}</b> ({loc['category'].capitalize()})<br>"
                f"Reviews: {loc['numReviews']}<br>"
                f"Polarity: {loc['polarity']}"
            )
        folium.Marker(
            [loc['lat'], loc['lng']],
            popup=folium.Popup(popup_text, max_width=300),
            icon=folium.Icon(color=icon_color)
        ).add_to(m)

    # Add markers for all locations (including non-visited)
    for idx, loc in enumerate(locations):
        if idx not in [step['location_idx'] for step in steps_info]:
            icon_color = 'gray'  # Different color for non-visited locations
            folium.Marker(
                [loc['lat'], loc['lng']],
                popup=f"{loc['name']} ({loc['category']}) - Not Visited",
                icon=folium.Icon(color=icon_color)
            ).add_to(m)

    # Save the map to an HTML file
    m.save('optimized_route.html')
    print("\nMap has been saved to 'optimized_route.html'. Open this file to view the route.")

    return m

user_prefs = {
    'city': 'Amsterdam',
    'categories': ['attraction', 'restaurant'],  # Added 'restaurant'
    'start_lat': 52.355320008998,
    'start_lng': 4.9574317242814,
    'start_time': 480,   # 8:00 AM
    'end_time': 1200,    # 8:00 PM
    'mode_of_travel': 'driving-car',
    'min_polarity': 4,
    'min_num_reviews': 10,
    'min_restaurants': 2,  # Minimum number of restaurants to visit
    'max_restaurants': 2,   # Maximum number of restaurants to visit
    'underground': True
}

def optimal_route():
    """Main function to run the itinerary optimizer."""

    # Load data
    df = fetch_places(user_prefs['city'], user_prefs['categories'])
    df = df.dropna(subset=['polarity', 'numReviews', 'lat', 'lng'])

    if user_prefs['underground']:
        df = compute_scores_underground(df)
    else:
        df = compute_scores(df)

    # Select top locations
    df_top = select_top_locations(df, user_prefs, N=10)  # Increased N to 10 for more locations

    # Prepare locations
    locations = prepare_locations(df_top, user_prefs)

    # Solve routing problem using ORS optimization
    ORS_API_KEY = '5b3ce3597851110001cf6248ef9ab7f2ff1b4472a4e320f7933b043b'  # Replace with your OpenRouteService API key
    route, steps_info = solve_with_ors_optimization(locations, user_prefs, ORS_API_KEY)

    if route and steps_info:
        # Print solution with arrival times
        print_solution(locations, steps_info, user_prefs)
        # Plot the route on a map
        plot_route_on_map(locations, steps_info, user_prefs['mode_of_travel'], api_key=ORS_API_KEY)
    else:
        print("No solution found.")

optimal_route()
