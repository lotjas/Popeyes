import requests
import time
from urllib.parse import urlparse, parse_qs

# Your YouTube Data API key
api_key = "AIzaSyCcF83kGou5ncw4DtwrRqC-vRlejKyVRtA"

# Full YouTube URLs (you can paste them directly)
urls = [
    "https://www.youtube.com/watch?v=MdI191-vNlc&t=9s",
    "https://www.youtube.com/watch?v=L86znpiEzX0&t=20s",
    "https://www.youtube.com/watch?v=Rt-tmo0uAIo",
    "https://www.youtube.com/watch?v=KNZlQXBvQCk"
]

# Helper function to extract the video ID from a full YouTube URL
def extract_video_id(url):
    query = parse_qs(urlparse(url).query)
    return query.get("v", [None])[0]

# Convert URLs to video IDs
video_ids = [extract_video_id(url) for url in urls]

url = "https://www.googleapis.com/youtube/v3/commentThreads"

def fetch_all_comments(video_id):
    """Fetch all top-level comments from one YouTube video."""
    params = {
        'part': 'snippet',
        'videoId': video_id,
        'maxResults': 100,
        'textFormat': 'plainText',
        'key': api_key,
    }

    comments = []
    page = 1

    while True:
        print(f"Getting page {page} for video {video_id}...")
        response = requests.get(url, params=params)

        if response.status_code == 200:
            data = response.json()
            comments.extend([
                item['snippet']['topLevelComment']['snippet']['textDisplay']
                for item in data.get('items', [])
            ])

            # Check for next page
            if 'nextPageToken' in data:
                params['pageToken'] = data['nextPageToken']
                page += 1
                time.sleep(0.5)  # short delay to avoid hitting quota limits
            else:
                break
        else:
            print(f"Error {response.status_code} for video {video_id}")
            break

    return comments


# Collect comments for all videos
all_comments = {}

for vid in video_ids:
    comments = fetch_all_comments(vid)
    all_comments[vid] = comments
    print(f"Collected {len(comments)} comments for video {vid}\n")

# Summary
total = sum(len(v) for v in all_comments.values())
print(f"Done! Retrieved a total of {total} comments from {len(video_ids)} videos.")
