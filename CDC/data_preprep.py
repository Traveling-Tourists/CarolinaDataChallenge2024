import requests
import pandas as pd

def fetch_places(location, category):
    url = f"http://tour-pedia.org/api/getPlaces?location={location}&category={category}"
    try:
        response = requests.get(url)
        response.raise_for_status()  
        places = response.json() 
        return places
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from the API for {location}: {e}")
        return []  
    
def filter_and_sort_places(places, min_reviews, max_reviews):
    filtered_places = [place for place in places if min_reviews <= place.get('numReviews', 0) <= max_reviews]
    
    df = pd.DataFrame(filtered_places)
    
    df = df.sort_values(by=['polarity', 'numReviews'], ascending=[False, True])
    
    return df

def save_to_csv(df, location):
    filename = f'combined_places_{location.lower()}.csv'
    df.to_csv(filename, index=False)
    print(f"Data saved to {filename}")

def main():
    locations = ['Amsterdam', 'Tuscany', 'Barcelona', 'Berlin', 'Dubai', 'London', 'Paris', 'Rome']
    categories = ['poi', 'restaurant', 'attraction', 'accommodation']
    min_reviews = 10
    max_reviews = 10000
    
    for location in locations:
        all_places = []
        for category in categories:
            places = fetch_places(location, category)
            if places:
                all_places.extend(places)
        
        if all_places:
            top_underground_places = filter_and_sort_places(all_places, min_reviews, max_reviews)
            if not top_underground_places.empty:
                print(f"Filtered places for {location}:")
                print(top_underground_places)
                
                save_to_csv(top_underground_places, location)
            else:
                print(f"No places with between {min_reviews} and {max_reviews} reviews found for {location}.")
        else:
            print(f"No places found for {location}.")

if __name__ == "__main__":
    main()
