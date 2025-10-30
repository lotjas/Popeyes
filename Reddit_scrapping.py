import csv
import json
import time
import re
from collections import Counter
from urllib import error
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup

# ---- NLP deps (lightweight) ----
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    _VADER = SentimentIntensityAnalyzer()
except Exception as _e:
    _VADER = None
    print("[WARN] vaderSentiment not found. Run: pip install vaderSentiment")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (macOS; research-wasp-nlp) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}

# keywords to mark "topics"/barriers
TOPIC_KEYWORDS = ["policy", "guidelines", "wind propulsion", "imo", "port", "regulation", "roi", "cost", "subsid"]

# barrier lexicon for quick tagging
BARRIERS = {
    "economic": ["capex","roi","payback","cost","costs","subsidy","subsidies","grant","funding","finance","price","carbon tax","ets","levy"],
    "regulatory": ["imo","eu ets","certification","class","regulation","permit","compliance","policy","rule","port authority","standard"],
    "operational": ["route","wind","maintenance","crew","training","schedule","retrofit","clearance","berth","draft","weather","operational"]
}

STOPWORDS = set("""
a an the of for and or to is are was were be being been in on with at by from this that these those it its it's as into over under out up down off
you your yours he she they we i me my our their them his her him us
about across after again against all also any because before between both but can could did do does doing during each few further had has have having here how if
just more most no nor not now only other our own same should so some such than then there they this through too until very what when where which who why will would Fuck fucking wanker punch balls cunts
""".split())

POST_URLS = [
    "https://www.reddit.com/r/megalophobia/comments/12a3edu/a_terrifying_size_of_windmills/",
    "https://www.reddit.com/r/megalophobia/comments/15y34nj/first_windpowered_cargo_ship/",
    "https://www.reddit.com/r/Futurology/comments/1bgxqhp/a_cargo_ships_windwing_sails_saved_it_up_to_12/",
]

# ----------------- helpers -----------------
def get(url: str) -> bytes:
    req = Request(url, headers=HEADERS)
    with urlopen(req, timeout=25) as resp:
        status = resp.getcode()
        if status >= 400:
            raise error.HTTPError(url, status, f"HTTP Error {status}", hdrs=None, fp=None)
        return resp.read()

def clean_text(text: str) -> str:
    t = (text or "")
    t = re.sub(r"http\S+|www\.\S+", " ", t)         # URLs
    t = re.sub(r"u/[A-Za-z0-9_-]+|r/[A-Za-z0-9_+-]+", " ", t)  # reddit handles
    t = re.sub(r"[^A-Za-z0-9' -]", " ", t)          # keep letters, digits, spaces, apostrophes, hyphens
    t = re.sub(r"\s+", " ", t).strip()
    return t

def sentiment_score(text: str) -> float:
    if not _VADER:
        return 0.0
    return _VADER.polarity_scores(text or "")["compound"]

def extract_topics_from_text(text: str) -> list[str]:
    text_l = (text or "").lower()
    found = []
    for kw in TOPIC_KEYWORDS:
        if kw in text_l:
            found.append(kw)
    return list(dict.fromkeys(found))

def barrier_tags(text: str) -> list[str]:
    t = (text or "").lower()
    tags = []
    for k, lex in BARRIERS.items():
        if any(w in t for w in lex):
            tags.append(k)
    return tags

def keyphrases(text: str, topn: int = 8) -> list[str]:
    """
    Very small, dependency-free keyword extractor:
    - tokenizes
    - drops stopwords
    - builds unigrams + bigrams
    - ranks by frequency
    """
    t = clean_text(text).lower()
    toks = [w for w in t.split() if w not in STOPWORDS and len(w) > 2]
    if not toks:
        return []
    unis = toks
    bis = [f"{toks[i]} {toks[i+1]}" for i in range(len(toks)-1) if (toks[i] not in STOPWORDS and toks[i+1] not in STOPWORDS)]
    counts = Counter(unis + bis)
    # remove numeric-only tokens
    for k in list(counts.keys()):
        if re.fullmatch(r"\d+", k):
            del counts[k]
    return [k for k,_ in counts.most_common(topn)]

# ----------------- scraping + NLP -----------------
def scrape_reddit() -> list[dict]:
    all_data = []
    for url in POST_URLS:
        print(f"Fetching post JSON: {url}")
        json_url = url.rstrip("/") + "/.json"
        try:
            raw = get(json_url)
            data = json.loads(raw)

            # data[0] -> post, data[1] -> comments
            post = data[0]["data"]["children"][0]["data"]
            post_title = post.get("title", "") or ""
            post_selftext = post.get("selftext", "") or ""
            post_url = "https://www.reddit.com" + post.get("permalink", "").rstrip("/")

            # optional page headings (kept from your design)
            headings_topics = []
            try:
                html = get(url)
                soup = BeautifulSoup(html, "html.parser")
                for h in soup.find_all(["h1","h2","h3","h4","h5","h6"]):
                    t = h.get_text(strip=True)
                    if t:
                        headings_topics.extend(extract_topics_from_text(t))
            except Exception:
                pass

            text_topics = extract_topics_from_text(post_title + "\n" + post_selftext)
            topics = list(dict.fromkeys(text_topics + headings_topics))

            # --- NLP on post ---
            post_text_clean = clean_text(post_title + "\n" + post_selftext)
            post_sent = sentiment_score(post_text_clean)
            post_barriers = barrier_tags(post_text_clean)
            post_kp = keyphrases(post_text_clean)

            # Collect comments (flat list)
            comments = []
            def walk(replies):
                if not isinstance(replies, dict):
                    return
                for ch in replies.get("children", []):
                    if ch.get("kind") != "t1":
                        continue
                    c = ch.get("data", {})
                    body = c.get("body", "") or ""
                    if body and body not in ("[deleted]", "[removed]"):
                        body_clean = clean_text(body)
                        comments.append({
                            "comment_id": c.get("id", ""),
                            "author": c.get("author", ""),
                            "score": c.get("score", 0),
                            "created_utc": c.get("created_utc", None),
                            "body": body,
                            "sentiment": sentiment_score(body_clean),
                            "barriers": "|".join(barrier_tags(body_clean)),
                            "keyphrases": "|".join(keyphrases(body_clean, topn=6)),
                            "matched_topics": "|".join(extract_topics_from_text(body))
                        })
                    repl = c.get("replies")
                    if isinstance(repl, dict):
                        walk(repl.get("data", {}))

            if len(data) > 1 and "data" in data[1]:
                walk(data[1]["data"])

            record = {
                "reddit_name": url.rstrip("/").split("/")[-1],
                "url": post_url,
                "title": post_title,
                "selftext": post_selftext,
                "topics": topics,
                # NLP fields for the post itself
                "post_sentiment": post_sent,
                "post_barriers": post_barriers,
                "post_keyphrases": post_kp,
                "comments": comments,
            }
            all_data.append(record)
            time.sleep(1.5)

        except error.URLError as e:
            print(f"[URL ERROR] {url}: {e}")
        except Exception as e:
            print(f"[ERROR] {url}: {e}")
    return all_data

# ----------------- save -----------------
def save_posts_csv(data, filename="reddit_posts.csv"):
    if not data:
        print("No post data to save.")
        return
    fields = ["reddit_name","url","title","selftext","topics","post_sentiment","post_barriers","post_keyphrases"]
    with open(filename, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for item in data:
            w.writerow({
                "reddit_name": item.get("reddit_name",""),
                "url": item.get("url",""),
                "title": item.get("title",""),
                "selftext": item.get("selftext",""),
                "topics": "|".join(item.get("topics", [])),
                "post_sentiment": item.get("post_sentiment", 0.0),
                "post_barriers": "|".join(item.get("post_barriers", [])),
                "post_keyphrases": "|".join(item.get("post_keyphrases", [])),
            })
    print(f"Saved posts → {filename}")

def save_comments_csv(data, filename="reddit_comments.csv"):
    rows = []
    for item in data:
        for c in item.get("comments", []):
            rows.append({
                "post_title": item.get("title",""),
                "post_url": item.get("url",""),
                "post_topics": "|".join(item.get("topics", [])),
                "comment_id": c.get("comment_id",""),
                "author": c.get("author",""),
                "score": c.get("score",0),
                "created_utc": c.get("created_utc",None),
                "comment_text": c.get("body",""),
                "sentiment": c.get("sentiment",0.0),
                "barriers": c.get("barriers",""),
                "keyphrases": c.get("keyphrases",""),
                "comment_matched_topics": c.get("matched_topics",""),
            })
    if not rows:
        print("No comments to save.")
        return
    fields = ["post_title","post_url","post_topics","comment_id","author","score","created_utc","comment_text","sentiment","barriers","keyphrases","comment_matched_topics"]
    with open(filename, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"Saved comments → {filename}")

# ----------------- main -----------------
def main() -> None:
    data = scrape_reddit()
    if not data:
        print("No data scraped from Reddit.")
        return
    print("Processing the data ...")
    print(f"Total posts: {len(data)}")
    print(f"Total comments fetched: {sum(len(d.get('comments', [])) for d in data)}")
    save_posts_csv(data)
    save_comments_csv(data)

if __name__ == "__main__":
    main()
