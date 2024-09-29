import pandas as pd
import folium
import streamlit as st
from streamlit_folium import st_folium
import os
import math

def load_data(csv_folder, location):
    all_places = []
    
    for file in os.listdir(csv_folder):
        if file.endswith(".csv") and location.lower() in file.lower():
            file_path = os.path.join(csv_folder, file)
            df = pd.read_csv(file_path)
            all_places.extend(df.to_dict(orient='records'))
    
    df = pd.DataFrame(all_places)
    return df.sort_values(by=['polarity', 'numReviews'], ascending=[False, True])

#folium map was created using assistance from generatve tools
def create_map(df, location, n_places, selected_categories):
    folium_map = folium.Map(zoom_start=12)

    category_color_map = {
        'poi': 'blue',
        'restaurant': 'green',
        'attraction': 'red',
        'accommodation': 'gray'
    }

    df_filtered = df[df['category'].isin(selected_categories)].head(n_places)

    locations = []

    for _, row in df_filtered.iterrows():
        category = row['category']
        locations.append([row['lat'], row['lng']])  
        
        folium.Marker(
            location=[row['lat'], row['lng']],
            popup=folium.Popup(f"<strong>{row['name']}</strong><br>Category: {category}<br>Polarity: {row['polarity']}<br>Reviews: {row['numReviews']}", max_width=250),
            tooltip=row['name'],
            icon=folium.Icon(color=category_color_map.get(category, 'gray'), icon='info-sign')  
        ).add_to(folium_map)

    if locations:
        folium_map.fit_bounds(locations) 

    return folium_map

def main():
    st.title("Underground spot discovery map")

    locations = ['Amsterdam', 'Tuscany', 'Barcelona', 'Berlin', 'Dubai', 'London', 'Paris', 'Rome']
    location = st.selectbox("Select a Location", locations)

    csv_folder = os.path.dirname(os.path.abspath(__file__))
    df = load_data(csv_folder, location)

    categories = df['category'].unique()

    selected_categories = st.multiselect("Select Categories to Display", categories, default=categories)

    n_places = st.slider("Number of Underground Places to Show", min_value=1, max_value= math.floor(len(df)), value=25)
    
    folium_map = create_map(df, location, n_places, selected_categories)

    st.write(f"Displaying the top {n_places} underground places in {location} for selected categories: {', '.join(selected_categories)}")

    st_folium(folium_map, width=700, height=500)

if __name__ == "__main__":
    main()