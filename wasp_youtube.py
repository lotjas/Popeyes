import requests
import time
import re
from bs4 import BeautifulSoup
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from collections import Counter
import pandas as pd

nltk.download('punkt')
nltk.download('stopwords')
nltk.download('wordnet')
nltk.download('vader_lexicon')

API_KEY = "AIzaSyCcF83kGou5ncw4DtwrRqC-vRlejKyVRtA"
VIDEO_IDS = ["MdI191-vNlc", "L86znpiEzX0", "Rt-tmo0uAIo", "KNZlQXBvQCk"]
BASE_URL = "https://www.googleapis.com/youtube/v3/commentThreads"

stop_words = set(stopwords.words('english'))
lemmatizer = WordNetLemmatizer()
sia = SentimentIntensityAnalyzer()

def preprocess_text(text):
    # Remove HTML
    text = BeautifulSoup(text, "html.parser").get_text()
    # Remove URLs, numbers, punctuation
    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"\d+", "", text)
    text = re.sub(r"[^\w\s]", "", text)
    # Lowercase
    text = text.lower()
    # Tokenize
    tokens = nltk.word_tokenize(text)
    # Remove stop words & lemmatize
    tokens = [lemmatizer.lemmatize(t) for t in tokens if t not in stop_words and t.strip()]
    return tokens

def fetch_all_comments(video_id, delay=0.5):
    """
    Fetch all top-level comments from a YouTube video using the API.
    """
    params = {
        'part': 'snippet',
        'videoId': video_id,
        'maxResults': 100,
        'textFormat': 'plainText',
        'key': API_KEY,
    }

    comments = []
    page = 1

    while True:
        print(f"[INFO] Fetching page {page} for video {video_id}...")
        response = requests.get(BASE_URL, params=params)

        if response.status_code != 200:
            print(f"[ERROR] {response.status_code} for video {video_id}")
            break

        data = response.json()
        new_comments = [
            item['snippet']['topLevelComment']['snippet']['textDisplay']
            for item in data.get('items', [])
        ]

        comments.extend(new_comments)
        print(f"  → Retrieved {len(new_comments)} comments (total: {len(comments)})")

        if 'nextPageToken' in data:
            params['pageToken'] = data['nextPageToken']
            page += 1
            time.sleep(delay)
        else:
            break

    return comments

def classify_sentiment(compound_score):
    """Classify sentiment based on VADER compound score."""
    if compound_score >= 0.05:
        return "Positive"
    elif compound_score <= -0.05:
        return "Negative"
    else:
        return "Neutral"

if __name__ == "__main__":
    all_comments = {}

    for vid in VIDEO_IDS:
        comments = fetch_all_comments(vid)
        all_comments[vid] = comments
        print(f"[DONE] Collected {len(comments)} comments for video {vid}\n")

    total_comments = sum(len(v) for v in all_comments.values())
    print(f"[SUMMARY] Retrieved a total of {total_comments} comments from {len(VIDEO_IDS)} videos.\n")

    all_text = [comment for comments in all_comments.values() for comment in comments]

    print("[INFO] Preprocessing comments...")
    cleaned_comments = [preprocess_text(comment) for comment in all_text]

    all_tokens = [token for comment in cleaned_comments for token in comment]
    word_freq = Counter(all_tokens)
    print("\nTop 20 most common words:")
    for word, freq in word_freq.most_common(20):
        print(f"  {word}: {freq}")

    print("\n[INFO] Performing sentiment analysis...")
    sentiment_scores = [sia.polarity_scores(" ".join(tokens)) for tokens in cleaned_comments]
    sentiment_labels = [classify_sentiment(s['compound']) for s in sentiment_scores]

    df_cleaned = pd.DataFrame({
        'comment': [" ".join(tokens) for tokens in cleaned_comments],
        'sentiment': sentiment_labels
    })

    df_readable = pd.DataFrame({
        'comment': all_text,
        'sentiment': sentiment_labels
    })

    df_cleaned.to_csv("youtube_comments_cleaned.csv", index=False)
    df_readable.to_csv("youtube_comments_readable.csv", index=False)

    print("\nSentiment distribution:")
    print(df_cleaned['sentiment'].value_counts())

    print("\n[EXPORT COMPLETE]")
    print("→ youtube_comments_cleaned.csv (processed version)")
    print("→ youtube_comments_readable.csv (original version)")
