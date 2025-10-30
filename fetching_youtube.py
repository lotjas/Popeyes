import requests
import time
import re
from bs4 import BeautifulSoup
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

# -----------------------------
# Step 0: Setup NLP tools
# -----------------------------
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('wordnet')

stop_words = set(stopwords.words('english'))
lemmatizer = WordNetLemmatizer()

def preprocess_text(text):
    """
    Preprocess a single text message.
    
    Steps:
    1. Remove unwanted/empty messages (handled outside if needed)
    2. Clean HTML, URLs, numbers, and punctuation
    3. Case normalization
    4. Tokenization
    5. Stop words removal
    6. Lemmatization
    """
    # Remove HTML
    text = BeautifulSoup(text, "html.parser").get_text()
    # Remove URLs, numbers, punctuation
    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"\d+", "", text)
    text = re.sub(r"[^\w\s]", "", text)
    # Lowercase
    text = text.lower()
    # Tokenization
    tokens = nltk.word_tokenize(text)
    # Stop words removal + lemmatization
    tokens = [lemmatizer.lemmatize(t) for t in tokens if t not in stop_words and t.strip() != '']
    return tokens

# -----------------------------
# Step 1: Fetch YouTube comments
# -----------------------------
api_key = "AIzaSyCcF83kGou5ncw4DtwrRqC-vRlejKyVRtA"

# List of video IDs
video_ids = [
    "MdI191-vNlc",
    "L86znpiEzX0",
    "Rt-tmo0uAIo",
    "KNZlQXBvQCk"
]

base_url = "https://www.googleapis.com/youtube/v3/commentThreads"

def fetch_all_comments(video_id, delay=0.5):
    """
    Fetch all top-level comments from a single YouTube video.
    """
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
        response = requests.get(base_url, params=params)

        if response.status_code == 200:
            data = response.json()
            new_comments = [
                item['snippet']['topLevelComment']['snippet']['textDisplay']
                for item in data.get('items', [])
            ]
            comments.extend(new_comments)
            print(f"  -> Retrieved {len(new_comments)} comments (total: {len(comments)})")

            if 'nextPageToken' in data:
                params['pageToken'] = data['nextPageToken']
                page += 1
                time.sleep(delay)
            else:
                break
        else:
            print(f"Error {response.status_code} for video {video_id}")
            break

    return comments

# Fetch comments for all videos
all_comments = {}
for vid in video_ids:
    comments = fetch_all_comments(vid)
    all_comments[vid] = comments
    print(f"Collected {len(comments)} comments for video {vid}\n")

total = sum(len(v) for v in all_comments.values())
print(f"Done! Retrieved a total of {total} comments from {len(video_ids)} videos.\n")

# -----------------------------
# Step 2: Combine and preprocess
# -----------------------------
# Combine all comments into one list
all_text = [comment for comments in all_comments.values() for comment in comments]

# Preprocess each comment
cleaned_comments = [preprocess_text(comment) for comment in all_text]

# Example: print first 5 preprocessed comments
for i, tokens in enumerate(cleaned_comments[:5]):
    print(f"Comment {i+1} tokens:", tokens)

from collections import Counter

all_tokens = [token for comment in cleaned_comments for token in comment]
word_freq = Counter(all_tokens)
print(word_freq.most_common(20))  # top 20 words

# Install if needed
# pip install nltk

from nltk.sentiment.vader import SentimentIntensityAnalyzer
nltk.download('vader_lexicon')

# Initialize VADER
sia = SentimentIntensityAnalyzer()

# Apply sentiment analysis to each comment (joined tokens back to string)
sentiment_scores = []
for tokens in cleaned_comments:
    text = " ".join(tokens)  # join tokens back to string
    score = sia.polarity_scores(text)  # returns dict with pos, neu, neg, compound
    sentiment_scores.append(score)

# Example: first 5 comments
for i, score in enumerate(sentiment_scores[:5]):
    print(f"Comment {i+1} sentiment:", score)

def classify_sentiment(compound):
    if compound >= 0.05:
        return "Positive"
    elif compound <= -0.05:
        return "Negative"
    else:
        return "Neutral"

sentiment_labels = [classify_sentiment(s['compound']) for s in sentiment_scores]

import pandas as pd

df = pd.DataFrame({
    'comment': [" ".join(tokens) for tokens in cleaned_comments],
    'sentiment': sentiment_labels
})

# Quick summary
print(df['sentiment'].value_counts())
