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

# 公開ポータルURL
WEB_URL = "https://tadfuji.github.io/ai-news-bot/"

# カテゴリ → ハッシュタグ（カテゴリ連動の動的ハッシュタグ生成に使用）
CATEGORY_HASHTAGS = {
    "対話型AI": ["#生成AI", "#ChatGPT"],
    "画像・動画AI": ["#画像生成AI", "#動画生成"],
    "中国AI": ["#中国AI", "#DeepSeek"],
    "ビジネス活用": ["#業務効率化", "#AI活用"],
    "リスク・規制": ["#AI規制", "#AIリスク"],
    "日本市場": ["#日本のAI", "#国内AI"],
    "研究・技術": ["#AI研究", "#LLM"],
}


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

    media_id = _upload_card_media(target_articles)
    try:
        # 1. Post main long-form tweet（画像カード付き）
        print("🚀 Sending main long-form tweet...")
        main_kwargs = {"text": full_text}
        if media_id:
            main_kwargs["media_ids"] = [media_id]
        resp = client.create_tweet(**main_kwargs)
        main_tweet_id = resp.data['id']
        print(f"✅ Main Post complete (ID: {main_tweet_id})")

        # 2. Post reply with URLs (To evade impression penalty)
        print("🔗 Posting links in the reply...")
        time.sleep(2)  # Small buffer
        client.create_tweet(text=links_text, in_reply_to_tweet_id=main_tweet_id)
        print("✅ Links Reply complete.")

    except Exception as e:
        print(f"❌ Failed to post to X: {e}")


def _truncate(text, limit):
    """文字数上限で安全に切り詰める（末尾に省略記号）。"""
    return text if len(text) <= limit else text[:limit - 1] + "…"


def _upload_card_media(articles, theme=""):
    """先頭記事から OGP 画像カードを生成し X(v1.1) へアップロードして media_id を返す。

    画像生成・アップロードに失敗しても None を返し、テキストのみで投稿を継続する
    （配信を止めない）。休眠していた generators/infographic_maker.py を活用。
    """
    if not articles:
        return None
    try:
        from generators.infographic_maker import create_infographic
        top = articles[0]
        card_title = theme or top.get("title_ja", "AI News")
        card_summary = top.get("one_liner") or top.get("summary_ja", "")
        path = os.path.join(NEWS_BOT_OUTPUT_DIR, "x_card.png")
        create_infographic(card_title, card_summary, output_path=path)

        auth = tweepy.OAuth1UserHandler(
            os.environ.get("X_CONSUMER_KEY"),
            os.environ.get("X_CONSUMER_SECRET"),
            os.environ.get("X_ACCESS_TOKEN"),
            os.environ.get("X_ACCESS_TOKEN_SECRET"),
        )
        api = tweepy.API(auth)
        media = api.media_upload(path)
        return media.media_id_string
    except Exception as e:
        print(f"⚠️ X画像カード生成/アップロード失敗（テキストのみで継続）: {e}")
        return None


def generate_hashtags(articles, max_tags=5):
    """記事カテゴリの頻度上位2つからハッシュタグを動的生成する。"""
    counts = {}
    for a in articles:
        c = a.get("category", "")
        if c in CATEGORY_HASHTAGS:
            counts[c] = counts.get(c, 0) + 1
    top = sorted(counts, key=lambda c: counts[c], reverse=True)[:2]
    tags = ["#AI"]
    for c in top:
        for t in CATEGORY_HASHTAGS[c]:
            if t not in tags:
                tags.append(t)
    return " ".join(tags[:max_tags])


def _format_article_tweet(rank, article):
    """1記事1ツイートの本文を組み立てる（URLは必ず末尾に保持）。"""
    one_liner = article.get("one_liner", "")
    title = article.get("title_ja", "No Title")
    action = article.get("action_item", "")
    url = article.get("url", "")

    head = f"{rank}. 💡 {one_liner}" if one_liner else f"{rank}."
    parts = [head, title]
    if action:
        parts.append(f"👉 {action}")
    text = _truncate("\n".join(parts), 200)  # URLを除く本文を抑える
    if url:
        text += f"\n{url}"
    return text


def post_to_x_thread(articles, theme="", morning_comment=""):
    """スレッド形式で投稿する（フック → Top3を1記事1ツイート → 残りの見出し）。

    環境変数 X_THREAD_MODE=1 のときのみ main() から呼ばれる。
    未設定時は既存の post_to_x_single() が使われるため既存挙動を壊さない。
    """
    consumer_key = os.environ.get("X_CONSUMER_KEY")
    consumer_secret = os.environ.get("X_CONSUMER_SECRET")
    access_token = os.environ.get("X_ACCESS_TOKEN")
    access_token_secret = os.environ.get("X_ACCESS_TOKEN_SECRET")

    if not all([consumer_key, consumer_secret, access_token, access_token_secret]):
        print("⚠️ X API Credentials missing. Skipping X post.")
        return

    if not articles:
        return

    client = tweepy.Client(
        consumer_key=consumer_key, consumer_secret=consumer_secret,
        access_token=access_token, access_token_secret=access_token_secret
    )

    hashtags = generate_hashtags(articles)
    top = articles[:3]
    rest = articles[3:10]

    # 1. フックツイート（編集長コメント + テーマ + Top1の一言 + Webリンク）
    hook = ""
    if morning_comment:
        hook += f"{morning_comment}\n\n"
    if theme:
        hook += f"本日のテーマ：{theme}\n\n"
    if top:
        lead = top[0].get("one_liner") or top[0].get("title_ja", "")
        hook += f"💡 {lead}\n\n"
    hook += f"全10件の解説はスレッドへ👇\n{WEB_URL}\n\n{hashtags}"
    hook = _truncate(hook, 270)

    media_id = _upload_card_media(articles, theme=theme)
    print(f"📝 Preparing X thread ({len(top)} highlights + {len(rest)} more)...")
    try:
        hook_kwargs = {"text": hook}
        if media_id:
            hook_kwargs["media_ids"] = [media_id]
        resp = client.create_tweet(**hook_kwargs)
        parent_id = resp.data["id"]
        print(f"✅ Hook tweet posted (ID: {parent_id})")

        # 2-4. Top3 を1記事1ツイートでスレッド化
        for i, article in enumerate(top, 1):
            time.sleep(2)
            r = client.create_tweet(
                text=_format_article_tweet(i, article),
                in_reply_to_tweet_id=parent_id,
            )
            parent_id = r.data["id"]

        # 5. 残りの見出しをまとめてWebへ誘導
        if rest:
            tail = "📰 その他の注目ニュース\n\n"
            for i, article in enumerate(rest, 4):
                lead = article.get("one_liner") or article.get("title_ja", "")
                tail += f"{i}. {lead}\n"
            tail += f"\n▶ 全文はこちら：{WEB_URL}"
            tail = _truncate(tail, 270)
            time.sleep(2)
            client.create_tweet(text=tail, in_reply_to_tweet_id=parent_id)

        print("✅ Thread complete.")
    except Exception as e:
        print(f"❌ Failed to post thread to X: {e}")


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

    # 2. X Distribution（X_THREAD_MODE=1 でスレッド形式、未設定は従来の単一投稿）
    try:
        if os.environ.get("X_THREAD_MODE") == "1":
            post_to_x_thread(
                articles,
                theme=data.get("theme", ""),
                morning_comment=data.get("morning_comment", ""),
            )
        else:
            post_to_x_single(articles)
    except Exception as e:
        print(f"❌ Error sending to X: {e}")


if __name__ == "__main__":
    main()
