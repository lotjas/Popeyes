import csv
import json
import time
import re
import requests
from collections import Counter
from bs4 import BeautifulSoup
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import nltk

# ---- Setup ----
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('wordnet')
nltk.download('vader_lexicon')

# ---- API CONFIG ----
API_KEY = "AIzaSyCcF83kGou5ncw4DtwrRqC-vRlejKyVRtA"
VIDEO_IDS = [
    "MdI191-vNlc",
    "L86znpiEzX0",
    "Rt-tmo0uAIo",
    "KNZlQXBvQCk"
]
BASE_URL = "https://www.googleapis.com/youtube/v3/commentThreads"

# ---- NLP setup ----
stop_words = set(stopwords.words('english'))
lemmatizer = WordNetLemmatizer()
sia = SentimentIntensityAnalyzer()

# ---- Keyword + Barrier definitions ----
TOPIC_KEYWORDS = ["climate", "wind", "ship", "transport", "policy", "subsidy", "cost", "port"]
BARRIERS = {
    "economic": ["cost", "price", "roi", "funding", "subsidy", "grant", "finance"],
    "regulatory": ["policy", "regulation", "imo", "permit", "law", "standard"],
    "operational": ["maintenance", "crew", "training", "weather", "retrofit", "schedule"]
}

# ---- Helpers ----
def clean_text(text: str) -> str:
    text = BeautifulSoup(text, "html.parser").get_text()
    text = re.sub(r"http\S+", " ", text)
    text = re.sub(r"[^A-Za-z0-9' -]", " ", text)
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text

def keyphrases(text: str, topn: int = 6) -> list[str]:
    toks = [t for t in re.findall(r"\b[a-z]{3,}\b", text.lower()) if t not in stop_words]
    if not toks:
        return []
    bis = [f"{toks[i]} {toks[i+1]}" for i in range(len(toks)-1)]
    counts = Counter(toks + bis)
    return [k for k, _ in counts.most_common(topn)]

def extract_topics_from_text(text: str) -> list[str]:
    t = text.lower()
    return [kw for kw in TOPIC_KEYWORDS if kw in t]

def barrier_tags(text: str) -> list[str]:
    t = text.lower()
    tags = []
    for k, lex in BARRIERS.items():
        if any(w in t for w in lex):
            tags.append(k)
    return tags

def sentiment_label(score: float) -> str:
    if score >= 0.05:
        return "Positive"
    elif score <= -0.05:
        return "Negative"
    else:
        return "Neutral"

# ---- Fetch comments ----
def fetch_youtube_comments(video_id: str, delay=0.5) -> list[dict]:
    params = {
        "part": "snippet",
        "videoId": video_id,
        "maxResults": 100,
        "textFormat": "plainText",
        "key": API_KEY
    }

    comments = []
    page = 1
    while True:
        print(f"Fetching comments page {page} for {video_id}...")
        resp = requests.get(BASE_URL, params=params)
        if resp.status_code != 200:
            print(f"[ERROR] {resp.status_code} - {resp.text}")
            break
        data = resp.json()
        items = data.get("items", [])
        for item in items:
            snippet = item["snippet"]["topLevelComment"]["snippet"]
            text = snippet.get("textDisplay", "")
            if not text.strip():
                continue
            clean = clean_text(text)
            sent_score = sia.polarity_scores(clean)["compound"]
            sent_label = sentiment_label(sent_score)
            comments.append({
                "video_id": video_id,
                "author": snippet.get("authorDisplayName", ""),
                "like_count": snippet.get("likeCount", 0),
                "published_at": snippet.get("publishedAt", ""),
                "text": text,
                "clean_text": clean,
                "sentiment_score": sent_score,
                "sentiment_label": sent_label,
                "keyphrases": "|".join(keyphrases(clean)),
                "barriers": "|".join(barrier_tags(clean)),
                "topics": "|".join(extract_topics_from_text(clean))
            })
        if "nextPageToken" not in data:
            break
        params["pageToken"] = data["nextPageToken"]
        page += 1
        time.sleep(delay)
    return comments

# ---- Main scrape ----
def scrape_youtube() -> list[dict]:
    all_comments = []
    for vid in VIDEO_IDS:
        comms = fetch_youtube_comments(vid)
        print(f"→ {len(comms)} comments fetched for video {vid}")
        all_comments.extend(comms)
        time.sleep(1)
    print(f"Total comments fetched: {len(all_comments)}")
    return all_comments

# ---- Save results ----
def save_comments_csv(data, filename="youtube_comments.csv"):
    if not data:
        print("No comments to save.")
        return
    fields = ["video_id","author","like_count","published_at","text","clean_text","sentiment_score","sentiment_label","keyphrases","barriers","topics"]
    with open(filename, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(data)
    print(f"Saved → {filename}")

# ---- Main ----
def main():
    comments = scrape_youtube()
    save_comments_csv(comments)

if __name__ == "__main__":
    main()
