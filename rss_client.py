import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import timezone

import feedparser
from dateutil import parser as date_parser
from config import RSS_FEEDS

# RSS取得の並列度（同時接続上限）
_MAX_WORKERS = 8
# フィードごとのタイムアウト（秒）
_FEED_TIMEOUT_SEC = 10


def _fetch_single_feed(feed_info: dict) -> list[dict]:
    """単一のRSSフィードを取得・パースする（スレッドワーカー用）"""
    articles = []
    try:
        feed = feedparser.parse(
            feed_info["url"],
            request_headers={"User-Agent": "ai-news-bot/1.0"},
        )

        for entry in feed.entries:
            # 公開日時を取得（published または updated）
            pub_date = None
            if hasattr(entry, "published"):
                pub_date = entry.published
            elif hasattr(entry, "updated"):
                pub_date = entry.updated

            # 日時をパース
            parsed_date = None
            if pub_date:
                try:
                    parsed_date = date_parser.parse(pub_date)
                    # タイムゾーンがない場合はUTCとして扱う
                    if parsed_date.tzinfo is None:
                        parsed_date = parsed_date.replace(tzinfo=timezone.utc)
                except Exception:
                    pass

            # 概要を取得
            summary = ""
            if hasattr(entry, "summary"):
                summary = entry.summary
            elif hasattr(entry, "description"):
                summary = entry.description

            articles.append({
                "title": entry.title if hasattr(entry, "title") else "No Title",
                "url": entry.link if hasattr(entry, "link") else "",
                "published": parsed_date,
                "summary": summary[:500] if summary else "",  # 最大500文字
                "source": feed_info["name"],
                "region": feed_info["region"],
            })

    except Exception as e:
        print(f"  ⚠️ {feed_info['name']}: {e}")

    return articles


def collect_from_rss_feeds() -> list[dict]:
    """
    複数のRSSフィードからニュース記事を並列収集する

    Returns:
        記事情報のリスト（タイトル、URL、公開日時、ソース名）
    """
    articles = []
    start = time.time()

    print(f"📡 {len(RSS_FEEDS)} フィードを並列取得中（最大{_MAX_WORKERS}スレッド）...")

    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as executor:
        future_to_feed = {
            executor.submit(_fetch_single_feed, feed_info): feed_info
            for feed_info in RSS_FEEDS
        }

        for future in as_completed(future_to_feed):
            feed_info = future_to_feed[future]
            try:
                result = future.result(timeout=_FEED_TIMEOUT_SEC)
                if result:
                    articles.extend(result)
                    print(f"  ✅ {feed_info['name']}: {len(result)} 件")
                else:
                    print(f"  ⏭️  {feed_info['name']}: 0 件")
            except Exception as e:
                print(f"  ⚠️ {feed_info['name']}: {e}")

    elapsed = time.time() - start
    print(f"✅ 合計 {len(articles)} 件の記事を取得しました（{elapsed:.1f}秒）")

    # フィードヘルスチェック: 0件フィードを警告
    feed_counts = {}
    for a in articles:
        src = a.get("source", "Unknown")
        feed_counts[src] = feed_counts.get(src, 0) + 1

    zero_feeds = [
        f["name"] for f in RSS_FEEDS if f["name"] not in feed_counts
    ]
    if zero_feeds:
        print(f"\n⚠️ ヘルスチェック: {len(zero_feeds)} フィードが0件")
        for name in zero_feeds:
            print(f"   - {name}")
        print("   → フィードURLの有効性を確認してください")

    return articles
