import os
import json
import glob
import time

import tweepy
from dotenv import load_dotenv
from config import NEWS_BOT_OUTPUT_DIR
from line_notifier import send_news_to_line

# Load Env
load_dotenv()

# X (Twitter) の長文ポスト上限（目安）
_X_MAX_CHARS = 25000


def get_latest_report():
    # Find latest report JSON in output/ (morning_brief preferred, ai_news as fallback)
    files = glob.glob(os.path.join(NEWS_BOT_OUTPUT_DIR, "morning_brief_*.json"))
    if not files:
        files = glob.glob(os.path.join(NEWS_BOT_OUTPUT_DIR, "ai_news_*.json"))
    if not files:
        return None
    # Sort by mtime
    latest_file = max(files, key=os.path.getmtime)
    return latest_file


def post_to_x_single(articles):
    """
    Post Top 10 articles as a single long-form post on X.
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

    print(f"📝 Preparing Single X Post ({len(target_articles)} articles)...")

    # Aggregate all content
    full_text = "【AI NEWS TOP 10 🚀 デイリーダイジェスト】\n\n"
    links_text = "【各記事のソースURL 🔗】\n\n"

    for i, article in enumerate(target_articles, 1):
        title = article.get('title_ja', 'No Title')
        summary = article.get('summary_ja', '')
        one_liner = article.get('one_liner', '')
        action_item = article.get('action_item', '')
        url = article.get('url', '')

        # Main Post Body
        if one_liner:
            full_text += f"{i}. 💡 {one_liner}\n"
            full_text += f"{title}\n\n"
        else:
            full_text += f"{i}. {title}\n\n"
        full_text += f"{summary}\n"
        if action_item:
            full_text += f"👉 {action_item}\n"
        full_text += "\n"

        # Link Collections for Reply
        links_text += f"{i}. {url}\n"

    full_text += "（詳細はリプライ欄のソースURLをご参照ください 👇）\n\n"
    full_text += "#AI #Tech #AINews"

    # 文字数チェック
    if len(full_text) > _X_MAX_CHARS:
        print(f"   ⚠️ 本文が{len(full_text)}文字（上限{_X_MAX_CHARS}）— 末尾を切り詰め")
        full_text = full_text[:_X_MAX_CHARS - 50] + "\n\n（続きはリプライ欄で）\n#AI #Tech #AINews"

    try:
        # 1. Post main long-form tweet
        print("🚀 Sending main long-form tweet...")
        resp = client.create_tweet(text=full_text)
        main_tweet_id = resp.data['id']
        print(f"✅ Main Post complete (ID: {main_tweet_id})")

        # 2. Post reply with URLs (To evade impression penalty)
        print("🔗 Posting links in the reply...")
        time.sleep(2)  # Small buffer
        client.create_tweet(text=links_text, in_reply_to_tweet_id=main_tweet_id)
        print("✅ Links Reply complete.")

    except Exception as e:
        print(f"❌ Failed to post to X: {e}")


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
        print(f"❌ Error sending to LINE: {e}")

    # 2. X Distribution
    try:
        post_to_x_single(articles)
    except Exception as e:
        print(f"❌ Error sending to X: {e}")


if __name__ == "__main__":
    main()
