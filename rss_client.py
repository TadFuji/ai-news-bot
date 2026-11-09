import datetime as dt
import json
import os
import socket
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import feedparser
from dateutil import parser as date_parser
from config import RSS_FEEDS

# RSS取得の並列度（同時接続上限）
_MAX_WORKERS = 8
# フィードごとのタイムアウト（秒）
_FEED_TIMEOUT_SEC = 10

JST = ZoneInfo("Asia/Tokyo")
# Per-feed read results for the morning check (committed by the workflow).
HEALTH_DIR = Path(__file__).resolve().parent / "health"

# Feed read outcomes. "failed" must never be reported as a quiet day.
STATUS_OK = "ok"          # read, with at least one entry
STATUS_EMPTY = "empty"    # read correctly, but the feed had no entries
STATUS_FAILED = "failed"  # could not be read (HTTP error, network, not a feed)


def _classify_feed(feed) -> tuple[str, str]:
    """Return (status, reason) for a feedparser result.

    feedparser does not raise on HTTP errors or broken XML; it returns an
    empty result with ``status`` / ``bozo`` set. Without this check a 404 feed
    looks exactly like a feed that simply had nothing new.
    """
    entries = getattr(feed, "entries", None) or []
    if not isinstance(feed, dict):
        # Test doubles and unexpected objects: judge by entries only.
        return (STATUS_OK, "") if entries else (STATUS_EMPTY, "")
    status = feed.get("status")
    if isinstance(status, int) and status >= 400:
        return STATUS_FAILED, f"HTTP {status}"
    if entries:
        return STATUS_OK, ""
    if feed.get("bozo"):
        exc = feed.get("bozo_exception")
        return STATUS_FAILED, type(exc).__name__ if exc is not None else "unreadable"
    if not feed.get("version"):
        # Parsed without error but not recognised as RSS/Atom (e.g. an HTML page).
        return STATUS_FAILED, "not a feed"
    return STATUS_EMPTY, ""


def _fetch_feed_with_status(feed_info: dict) -> tuple[list[dict], str, str]:
    """単一のRSSフィードを取得・パースし、記事と読み取り結果を返す（スレッドワーカー用）"""
    articles = []
    try:
        feed = feedparser.parse(
            feed_info["url"],
            request_headers={"User-Agent": "ai-news-bot/1.0"},
        )
        status, reason = _classify_feed(feed)

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
        return articles, STATUS_FAILED, type(e).__name__

    return articles, status, reason


def _fetch_single_feed(feed_info: dict) -> list[dict]:
    """単一のRSSフィードを取得・パースする（記事だけを返す）"""
    return _fetch_feed_with_status(feed_info)[0]


def write_feed_health(results: list[dict], health_dir: Path = HEALTH_DIR,
                      now: dt.datetime | None = None) -> Path | None:
    """Save today's per-feed results as health/feeds-YYYY-MM-DD.json (JST).

    A later run on the same day replaces the file, so it always shows the
    latest collection. Failure to write must never stop the collection.
    """
    now = now or dt.datetime.now(JST)
    counts = {s: sum(1 for r in results if r["status"] == s)
              for s in (STATUS_OK, STATUS_EMPTY, STATUS_FAILED)}
    data = {
        "date": now.date().isoformat(),
        "checked_at": now.isoformat(timespec="seconds"),
        "total": len(results),
        **counts,
        "feeds": sorted(results, key=lambda r: (r["status"] != STATUS_FAILED, r["name"])),
    }
    try:
        health_dir = Path(health_dir)
        health_dir.mkdir(parents=True, exist_ok=True)
        path = health_dir / f"feeds-{data['date']}.json"
        fd, tmp = tempfile.mkstemp(dir=health_dir, prefix=".feeds-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.write("\n")
            os.replace(tmp, path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise
        return path
    except Exception as e:
        print(f"⚠️ フィードの読み取り結果を保存できませんでした: {type(e).__name__}")
        return None


def collect_from_rss_feeds(health_dir: Path = HEALTH_DIR) -> list[dict]:
    """
    複数のRSSフィードからニュース記事を並列収集する

    Returns:
        記事情報のリスト（タイトル、URL、公開日時、ソース名）
    """
    articles = []
    results = []
    start = time.time()

    # feedparser.parse は内部の urllib にタイムアウトを渡さないため、ソケットの
    # グローバル既定で足切りする。これが無いと無応答フィード1本で全体が永久待ちになり、
    # ジョブの 60 分タイムアウトでその日の配信が全損する。
    # （下の future.result(timeout=...) は as_completed が完了済み future しか
    # 返さないため足切りとしては機能しない — こちらが唯一の実効タイムアウト）
    socket.setdefaulttimeout(_FEED_TIMEOUT_SEC)

    print(f"📡 {len(RSS_FEEDS)} フィードを並列取得中（最大{_MAX_WORKERS}スレッド）...")

    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as executor:
        future_to_feed = {
            executor.submit(_fetch_feed_with_status, feed_info): feed_info
            for feed_info in RSS_FEEDS
        }

        for future in as_completed(future_to_feed):
            feed_info = future_to_feed[future]
            try:
                result, status, reason = future.result(timeout=_FEED_TIMEOUT_SEC)
            except Exception as e:
                result, status, reason = [], STATUS_FAILED, type(e).__name__
                print(f"  ⚠️ {feed_info['name']}: {e}")
            articles.extend(result)
            results.append({"name": feed_info["name"], "status": status,
                            "count": len(result), "reason": reason})
            if status == STATUS_FAILED:
                print(f"  ❌ {feed_info['name']}: 読み取れません（{reason}）")
            elif result:
                print(f"  ✅ {feed_info['name']}: {len(result)} 件")
            else:
                print(f"  ⏭️  {feed_info['name']}: 0 件")

    elapsed = time.time() - start
    print(f"✅ 合計 {len(articles)} 件の記事を取得しました（{elapsed:.1f}秒）")

    # フィードヘルスチェック: 読み取れなかったフィードと 0 件のフィードを分けて警告
    failed = [r for r in results if r["status"] == STATUS_FAILED]
    empty = [r for r in results if r["status"] == STATUS_EMPTY]
    if failed:
        print(f"\n❌ ヘルスチェック: {len(failed)} フィードを読み取れませんでした")
        for r in sorted(failed, key=lambda r: r["name"]):
            print(f"   - {r['name']}（{r['reason']}）")
        print("   → フィードURLの有効性を確認してください")
    if empty:
        print(f"\n⏭️ ヘルスチェック: {len(empty)} フィードは読み取れたが 0 件")
        for r in sorted(empty, key=lambda r: r["name"]):
            print(f"   - {r['name']}")

    path = write_feed_health(results, health_dir)
    if path:
        print(f"📝 フィードの読み取り結果: {path.name}")

    return articles
