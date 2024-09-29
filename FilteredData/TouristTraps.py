import aiohttp
import asyncio
import pandas as pd
import numpy as np
import time

#The implementation of the async and aiohttp libraries were copied from ChatGPT to reduce run times by fetching data concurrently
async def fetch(session, url):
    try:
        async with session.get(url) as response:
            return await response.json()
    except Exception as e:
        print(f"Error fetching data from the API: {e}")
        return None

async def fetch_places_async(session, location, category):
    url = f"http://tour-pedia.org/api/getPlaces?location={location}&category={category}"
    return await fetch(session, url)

async def fetch_place_details(session, place_id):
    url = f"http://tour-pedia.org/api/getReviewsByPlaceId?placeId={place_id}"
    return await fetch(session, url)


async def filter_tourist_traps(session, places, min_polarity, min_reviews, max_reviews):
    filtered_places = []
    variances = [] 

    for place in places:
        if place.get('polarity', 0) >= min_polarity and min_reviews <= place.get('numReviews', 0) <= max_reviews:

            reviews = await fetch_place_details(session, place.get('id'))
            if not reviews or not isinstance(reviews, list):
                print(f"Unexpected 'reviews' format for place: {place.get('name', 'Unknown')}")
                continue

            monthly_reviews = [0] * 12

            for review in reviews:
                if isinstance(review, dict):
                    timestamp = review.get('time', '')
                    if len(timestamp) >= 7:
                        try:
                            month_index = int(timestamp[5:7]) - 1
                            monthly_reviews[month_index] += 1
                        except ValueError:
                            print(f"Invalid month value in timestamp: {timestamp}")
                    else:
                        print(f"Invalid timestamp format for review: {review}")
                else:
                    print(f"Unexpected review format: {review}")

            review_variance = np.var(monthly_reviews)
            place['monthly_reviews'] = monthly_reviews
            place['review_variance'] = review_variance
            variances.append(review_variance)
            filtered_places.append(place)

    if variances:
        variance_threshold = np.percentile(variances, 95)
        filtered_places = [place for place in filtered_places if place['review_variance'] >= variance_threshold]

    return filtered_places

def save_to_csv(places, location):
    df = pd.DataFrame(places)
    df = df[['name', 'category', 'location', 'lat', 'lng', 'polarity', 'numReviews', 'monthly_reviews', 'review_variance']]
    df = df.sort_values(by=['numReviews', 'polarity'], ascending=[False, False])
    filename = f'tourist_traps_{location.lower()}.csv'
    df.to_csv(filename, index=False)
    print(f"Data saved to {filename}")

async def main():
    locations = ['Amsterdam', 'Tuscany', 'Barcelona', 'Berlin', 'Dubai', 'London', 'Paris', 'Rome']
    categories = ['poi', 'restaurant', 'attraction']
    min_polarity = 6
    min_reviews = 10
    max_reviews = 1000

    async with aiohttp.ClientSession() as session:
        for location in locations:
            all_places = []
            tasks = []

            for category in categories:
                tasks.append(fetch_places_async(session, location, category))
            
            results = await asyncio.gather(*tasks)

            for places in results:
                if places:
                    tourist_traps = await filter_tourist_traps(session, places, min_polarity, min_reviews, max_reviews)
                    all_places.extend(tourist_traps)

            if all_places:
                save_to_csv(all_places, location)
            else:
                print(f"No tourist traps found with the given criteria for {location}.")

if __name__ == "__main__":
    start_time = time.time()
    asyncio.run(main())
    print(f"Time taken: {time.time() - start_time:.2f} seconds")
