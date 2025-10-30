import requests
import time

# The API key is your key to the YouTube API. You will neeed to get your own. To do so, visit https://developers.google.com/youtube/v3/getting-started
# TODO Enter your API key here
api_key = "AIzaSyCcF83kGou5ncw4DtwrRqC-vRlejKyVRtA"
#. Your solution here ...
video_id = "kRGx-E96whI"
# Replace with the ID of the video you are interested in. 
# You can find the ID by going to a video in Youtube, and getting the string after v= in the URL. For instance, i0EfLMe5FGk in https://www.youtube.com/watch?v=i0EfLMe5FGk

url = f"https://www.googleapis.com/youtube/v3/commentThreads"
params = {
    'part': 'snippet',
    'videoId': video_id,
    'maxResults': 100,  # max number of comments to fetch 
    'textFormat': 'plainText',
    'key': api_key,
}

all_comments = []

maximum_pages = 3 #How many pages to get at most

for page in range(maximum_pages):
    print(f"Getting page {page}...")
    response = requests.get(url, params=params)
    if response.status_code == 200:
        result_json = response.json()
        all_comments.extend([item['snippet']['topLevelComment']['snippet']['textDisplay'] for item in result_json.get('items', [])])

        # Many APIs provide the result page by page. If there is another page, this API returns a nextPageToken, that we can
        # send to the API to get the next page in line. If there are no more comments, there will be no such token.
        if 'nextPageToken' in result_json:
            params['pageToken'] = result_json['nextPageToken']
            
            # Ensure you don't hit the quota limits by adding a delay
            time.sleep(1)
        else: #No token, so no more pages
            break
    else:
        print("Error: ", response.status_code)
        break

# Now 'all_comments' list contains all the comments from the video
print(f"Done. Fetched {len(all_comments)} comments!")
