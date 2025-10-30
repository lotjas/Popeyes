# reddit_sentiment_fixed.py
import os, csv, time, sys
import praw
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

USER_AGENT = "wasp-research/1.0 by u/trttpe7580"  # include your username

CLIENT_ID = (os.getenv("REDDIT_CLIENT_ID") or "").strip()
CLIENT_SECRET = (os.getenv("REDDIT_CLIENT_SECRET") or "").strip()

if not CLIENT_ID or not CLIENT_SECRET:
    print("ERROR: Set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET in your environment.", file=sys.stderr)
    sys.exit(1)

reddit = praw.Reddit(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    user_agent=USER_AGENT,
)
reddit.read_only = True

# sanity check to fail fast if auth is wrong
try:
    _ = next(reddit.subreddit("python").hot(limit=1))
except Exception as e:
    print("Reddit authentication failed (HTTP 401). Check your app type (must be 'script'), "
          "client id/secret (no trailing spaces), and user_agent.", file=sys.stderr)
    raise

analyzer = SentimentIntensityAnalyzer()
def vs(text: str) -> float:
    return analyzer.polarity_scores(text or "")["compound"]

SUBREDDITS = ["megalophobia", "Futurology"]
POST_LIMIT = 20

posts, comments = [], []

for sub in SUBREDDITS:
    print(f"\nFetching from r/{sub} ...")
    for s in reddit.subreddit(sub).hot(limit=POST_LIMIT):
        post_url = f"https://www.reddit.com{s.permalink}".rstrip("/")
        post_text = (s.title or "") + "\n" + (s.selftext or "")
        posts.append({
            "subreddit": sub,
            "post_id": s.id,
            "title": s.title or "",
            "selftext": s.selftext or "",
            "url": post_url,
            "score": s.score,
            "num_comments": s.num_comments,
            "created_utc": s.created_utc,
            "sentiment": vs(post_text),
        })
        s.comments.replace_more(limit=0)
        for c in s.comments.list():
            body = c.body or ""
            if body in ("[deleted]", "[removed]"):
                continue
            comments.append({
                "subreddit": sub,
                "post_id": s.id,
                "post_title": s.title or "",
                "post_url": post_url,
                "comment_id": c.id,
                "parent_id": c.parent_id,
                "author": (c.author.name if c.author else ""),
                "score": c.score,
                "created_utc": c.created_utc,
                "text": body,
                "sentiment": vs(body),
            })
        time.sleep(0.3)

if posts:
    with open("reddit_posts_sentiment.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(posts[0].keys()))
        w.writeheader(); w.writerows(posts)

if comments:
    with open("reddit_comments_sentiment.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(comments[0].keys()))
        w.writeheader(); w.writerows(comments)

print(f"\n✅ Saved {len(posts)} posts and {len(comments)} comments with sentiment scores.")
