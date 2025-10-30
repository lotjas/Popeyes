import requests
import time

# Your YouTube Data API key
api_key = "AIzaSyCcF83kGou5ncw4DtwrRqC-vRlejKyVRtA"

# List of YouTube video IDs
video_ids = [
    "MdI191-vNlc",
    "L86znpiEzX0",
    "Rt-tmo0uAIo",
    "KNZlQXBvQCk"
]

# Base URL for YouTube commentThreads API
base_url = "https://www.googleapis.com/youtube/v3/commentThreads"

def fetch_all_comments(video_id, delay=0.5):
    """
    Fetch all top-level comments from a single YouTube video.
    """
    params = {
        'part': 'snippet',
        'videoId': video_id,
        'maxResults': 100,  # Maximum allowed per request
        'textFormat': 'plainText',
        'key': api_key,
    }

    comments = []
    page = 1

    while True:
        print(f"Getting page {page} for video {video_id}...")
        response = requests.get(base_url, params=params)

        if response.status_code == 200:
            data = response.json()
            new_comments = [
                item['snippet']['topLevelComment']['snippet']['textDisplay']
                for item in data.get('items', [])
            ]
            comments.extend(new_comments)
            print(f"  -> Retrieved {len(new_comments)} comments (total: {len(comments)})")

            # Check for next page
            if 'nextPageToken' in data:
                params['pageToken'] = data['nextPageToken']
                page += 1
                time.sleep(delay)  # avoid hitting quota limits
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
