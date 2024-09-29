# Save this as app.py
import folium
from folium.plugins import HeatMap
import requests
import pandas as pd
import streamlit as st

def fetch_data(city):
    # API endpoint
    endpoint = "http://tour-pedia.org/api/getPlaces"
    categories = ['accommodation', 'attraction', 'restaurant', 'poi']
    all_data = pd.DataFrame()
    
    for category in categories:
        # Set parameters for the API request
        params = {
            'location': city,   
            'category': category  
        }
        response = requests.get(endpoint, params=params)
        
        # Check if the request was successful
        print(f"Fetching {category} data for {city}... Status Code: {response.status_code}")
        if response.status_code == 200:
            category_data = pd.DataFrame(response.json())
            if not category_data.empty:
                print(f"Fetched {len(category_data)} records for {category} in {city}.")
            else:
                print(f"No data found for {category} in {city}.")
                
            all_data = pd.concat([all_data, category_data], ignore_index=True)
        else:
            print(f"Error fetching {category} data for {city}: {response.status_code}")
    
    if all_data.empty:
        print(f"No data available for {city}.")
        
    return all_data

cities = ['Amsterdam', 'Barcelona', 'Berlin', 'Dubai', 'London', 'Paris', 'Rome', 'Tuscany']
data = {city: fetch_data(city) for city in cities}

for city, df in data.items():
    print(f"\nData for {city}:")
    if not df.empty:
        print(df.head())
    else:
        print(f"No data retrieved for {city}.")



# Define a color mapping for different categories (used for reference)
category_colors = {
    'restaurant': '#33CCFF',  # Light blue for restaurants
    'attraction': '#00CC33',  # Bright green for attractions
    'point of interest': '#FF3333',  # Red for points of interest
    'accommodation': '#000000',  # Black for accommodations
}

def create_heatmap(city, df):
    # Function to create individual heatmaps
    if 'lat' not in df.columns or 'lng' not in df.columns:
        st.write(f"Error: Missing latitude or longitude data for {city}.")
        return None

    df = df.dropna(subset=['lat', 'lng', 'polarity'])

    df = df.head(1000) # Take first 1000 values for performance

    if df.empty:
        st.write(f"No valid data available for creating a map of {city} with the given conditions.")
        return None

    avg_lat = df['lat'].mean()
    avg_lon = df['lng'].mean()
    map_city = folium.Map(location=[avg_lat, avg_lon], zoom_start=13)

    # Create heatmap data
    heat_data = [[row['lat'], row['lng'], row['polarity']] for index, row in df.iterrows() 
                 if row['category'].lower().strip() in ['restaurant', 'attraction', 'point of interest', 'accommodation']]
    
    st.write(f"Number of points in heatmap data for {city}: {len(heat_data)}")
    if not heat_data:
        st.write(f"Warning: No data points available for the heatmap for {city}.")
        return None

    HeatMap(
        heat_data,
        radius=30,         
        blur=25,           
        min_opacity=0.5,   
        max_zoom=10,       
    ).add_to(map_city)

    return map_city

# Example data for multiple cities; replace these with the actual DataFrames
city_data = {
    "Amsterdam": pd.DataFrame(data['Amsterdam']),
    "Barcelona": pd.DataFrame(data['Barcelona']),
    "Berlin": pd.DataFrame(data['Berlin']),
    "Dubai": pd.DataFrame(data['Dubai']),
    "London": pd.DataFrame(data['London']),
    "Paris": pd.DataFrame(data['Paris']),
    "Rome": pd.DataFrame(data['Rome']),
    "Tuscany": pd.DataFrame(data['Tuscany']),
}

# Streamlit page configuration
st.set_page_config(page_title="City Heatmaps", layout="wide")

st.title("Heatmaps of Various Cities")

# Iterate through each city and display its heatmap
for city, df in city_data.items():
    st.subheader(f"Heatmap for {city}")
    city_map = create_heatmap(city, df)
    if city_map:
        # Streamlit allows folium map embedding through iframe
        folium_static = st.components.v1.html(city_map._repr_html_(), height=500, scrolling=True)

# Write in terminal: 'streamlit run all_heat_maps.py' in order to create streamlit app.