import os
import json
import glob
import tweepy
from dotenv import load_dotenv
from config import NEWS_BOT_OUTPUT_DIR
from line_notifier import send_news_to_line

# Load Env
load_dotenv()

def get_latest_report():
    # Find latest JSON in output/
    files = glob.glob(os.path.join(NEWS_BOT_OUTPUT_DIR, "*.json"))
    if not files:
        return None
    # Sort by mtime
    latest_file = max(files, key=os.path.getmtime)
    return latest_file

import time

def post_to_x_thread(articles):
    """
    Post a 10-tweet thread to X.
    Rules:
    - Post ALL Top 10 articles (as a thread).
    - NO URLs in the text (Algorithm optimization).
    """
    consumer_key = os.environ.get("X_CONSUMER_KEY")
    consumer_secret = os.environ.get("X_CONSUMER_SECRET")
    access_token = os.environ.get("X_ACCESS_TOKEN")
    access_token_secret = os.environ.get("X_ACCESS_TOKEN_SECRET")

    if not all([consumer_key, consumer_secret, access_token, access_token_secret]):
        print("⚠️ X API Credentials missing. Skipping X post.")
        return

    client = tweepy.Client(
        consumer_key=consumer_key, consumer_secret=consumer_secret,
        access_token=access_token, access_token_secret=access_token_secret
    )
    
    if not articles:
        return

    # Process up to 10 articles
    target_articles = articles[:10]
    last_tweet_id = None
    
    print(f"🧵 Starting X Thread ({len(target_articles)} tweets)...")

    for i, article in enumerate(target_articles, 1):
        title = article.get('title_ja', 'No Title')
        summary = article.get('summary_ja', '')
        
        # Formatting: 140 full-width chars max (approx).
        # We prioritize Title + Summary.
        # Format:
        # 【1/10】Title
        # Summary
        # #Hash
        
        header = f"【{i}/{len(target_articles)}】"
        
        # Simple truncation strategy
        # 280 chars limit. Japanese chars count as 2. 
        # Roughly 120 Japanese chars to be safe.
        if len(summary) > 80:
            summary = summary[:79] + "..."
            
        tweet_text = f"{header}{title}\n\n{summary}\n\n#AI #Tech"
        
        try:
            if last_tweet_id is None:
                # First Tweet
                resp = client.create_tweet(text=tweet_text)
            else:
                # Reply to previous
                resp = client.create_tweet(text=tweet_text, in_reply_to_tweet_id=last_tweet_id)
            
            last_tweet_id = resp.data['id']
            print(f"   ✅ Posted {i}/10")
            
            # Wait a bit to prevent rate limits or disorder
            time.sleep(2)
            
        except Exception as e:
            print(f"   ❌ Failed to post tweet {i}: {e}")
            # If one fails, maybe continue? But thread breaks. 
            # We try to continue attaching to the last *successful* one if possible, 
            # but if last_tweet_id is None, we can't chain.
            if last_tweet_id is None: 
                print("   ⚠️ Main tweet failed, stopping thread.")
                break

    print("✅ X Thread posting complete.")

from datetime import datetime

def main():
    print("🚀 Starting Daily Distribution...")
    
    report_path = get_latest_report()
    if not report_path:
        print("❌ No report found to distribute.")
        return

    print(f"📄 Loading report: {report_path}")
    with open(report_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    articles = data.get("articles", [])
    if not articles:
        print("⚠️ No articles in report.")
        return

    # 1. LINE Distribution
    try:
        send_news_to_line(articles)
    except Exception as e:
        print(f"DATA Error sending to LINE: {e}")

    # 2. X Distribution
    try:
        post_to_x_thread(articles)
    except Exception as e:
        print(f"DATA Error sending to X: {e}")

if __name__ == "__main__":
    main()
