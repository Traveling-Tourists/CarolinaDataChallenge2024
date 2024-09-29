import pandas as pd
import folium
import streamlit as st
from streamlit_folium import st_folium
import os
from folium.plugins import HeatMap
from optimal_route import (
    compute_scores_underground,
    select_top_locations,
    prepare_locations,
    solve_with_ors_optimization,
    plot_route_on_map,
    compute_scores,
    fetch_places,
    print_solution
)

# Function to load data
def load_data(csv_folder, location):
    all_places = []
    
    for file in os.listdir(csv_folder):
        if file.endswith(".csv") and location.lower() in file.lower():
            file_path = os.path.join(csv_folder, file)
            df = pd.read_csv(file_path)
            all_places.extend(df.to_dict(orient='records'))
    
    df = pd.DataFrame(all_places)
    return df.sort_values(by=['polarity', 'numReviews'], ascending=[False, True])

# Function to create map with optional heatmap and pins
def create_map(df, location, n_places, selected_categories, show_heatmap, show_pins):
    folium_map = folium.Map(zoom_start=12)

    category_color_map = {
        'poi': 'blue',
        'restaurant': 'green',
        'attraction': 'red',
        'accommodation': 'gray'
    }

    df_filtered = df[df['category'].isin(selected_categories)].head(n_places)

    heat_data = [[row['lat'], row['lng'], row['polarity']] for _, row in df_filtered.iterrows()]

    if show_heatmap and heat_data:
        HeatMap(heat_data, radius=20, blur=15, min_opacity=0.4).add_to(folium_map)

    locations = []

    if show_pins:
        for _, row in df_filtered.iterrows():
            category = row['category']
            locations.append([row['lat'], row['lng']])  
            
            folium.Marker(
                location=[row['lat'], row['lng']],
                popup=folium.Popup(
                    f"<strong>{row['name']}</strong><br>Category: {category}<br>Polarity: {row['polarity']}<br>Reviews: {row['numReviews']}",
                    max_width=250
                ),
                tooltip=row['name'],
                icon=folium.Icon(color=category_color_map.get(category, 'gray'), icon='info-sign')  
            ).add_to(folium_map)
    
    if not show_pins and show_heatmap:
        locations = [[lat, lng] for lat, lng, _ in heat_data]

    if locations:
        folium_map.fit_bounds(locations)
    
    return folium_map

def main():
    st.title("Underground Spot Discovery Map")

    locations = ['Amsterdam', 'Tuscany', 'Barcelona', 'Berlin', 'Dubai', 'London', 'Paris', 'Rome']
    location = st.sidebar.selectbox("Select a Location", locations)

    csv_folder = os.path.dirname(os.path.abspath(__file__))
    df = load_data(csv_folder, location)
    
    categories = df['category'].unique()

    selected_categories = st.sidebar.multiselect("Select Categories to Display", categories, default=categories)

    with st.expander("Set Discovery Map Preferences"):
        n_places = st.slider("Number of Underground Places to Show", min_value=1, max_value=len(df), value=150)

        show_heatmap = st.checkbox("Show Heatmap", value=True)

        show_pins = st.checkbox("Show Pins", value=True)

    folium_map = create_map(df, location, n_places, selected_categories, show_heatmap, show_pins)

    if selected_categories:
        if n_places > 150:
            st.write(f"Displaying the top {', '.join(selected_categories)} in {location}")
        else:
            st.write(f"Displaying the top {n_places} underground {', '.join(selected_categories)} in {location}")
    else:
        st.write("Displaying no points")

    st_folium(folium_map, width=700, height=500)
    
    st.title("Itinerary Optimization")

    # User inputs for route optimization
    with st.expander("Set Itinerary Preferences"):
        start_lat = st.number_input("Start Latitude", value=df.iloc[0]['lat'], format="%.6f")
        start_lng = st.number_input("Start Longitude", value=df.iloc[0]['lng'], format="%.6f")
        start_time = st.slider("Start Time (minutes from midnight)", 0, 1440, 480)
        end_time = st.slider("End Time (minutes from midnight)", 0, 1440, 1200)
        mode_of_travel = st.selectbox("Mode of Travel", ['driving-car', 'cycling-regular', 'foot-walking'])
        min_polarity = st.slider("Minimum Polarity", min_value=0.0, max_value=9.0, value=4.0)
        min_num_reviews = st.slider("Minimum Number of Reviews", min_value=0, max_value=200, value=10)
        underground = st.checkbox("Underground Only", value=False)

    calculate_route = st.button("Calculate Optimal Itinerary")

    if calculate_route:
        if True:
            # Define user preferences based on inputs
            user_prefs = {
                'city': location,
                'categories': selected_categories,
                'start_lat': start_lat,
                'start_lng': start_lng,
                'start_time': start_time,   # in minutes
                'end_time': end_time,    # in minutes
                'mode_of_travel': mode_of_travel,
                'min_polarity': min_polarity,
                'min_num_reviews': min_num_reviews,
                'min_restaurants': 2,
                'max_restaurants': 2,
                'underground': underground
            }

            df = fetch_places(user_prefs['city'], user_prefs['categories'])
            df = df.dropna(subset=['polarity', 'numReviews', 'lat', 'lng'])

            if user_prefs['underground']:
                df = compute_scores_underground(df)
            else:
                df = compute_scores(df)

            df_top = select_top_locations(df, user_prefs, N=10)

            locations = prepare_locations(df_top, user_prefs)

            ORS_API_KEY = '5b3ce3597851110001cf6248ef9ab7f2ff1b4472a4e320f7933b043b'  # Replace with your OpenRouteService API key
            route, steps_info = solve_with_ors_optimization(locations, user_prefs, ORS_API_KEY)

            if route and steps_info:
            # Print solution with arrival times
                st.session_state['route'] = print_solution(locations, steps_info, user_prefs)
                # Plot the route on a map
                optimized_map = plot_route_on_map(locations, steps_info, user_prefs['mode_of_travel'], api_key=ORS_API_KEY)
                st.session_state['optimized_map'] = optimized_map
            else:
                print("No solution found.")
        
        if 'optimized_map' in st.session_state:
            st.write(st.session_state['route'])
            st_folium(st.session_state['optimized_map'], width=700, height=500)
    else:
        if 'optimized_map' in st.session_state:
            st.write(st.session_state['route'])
            st_folium(st.session_state['optimized_map'], width=700, height=500)

if __name__ == "__main__":
    main()
