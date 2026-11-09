"""Feeds that cannot be read must be recorded as failed, never as a quiet day."""
import datetime as dt
import json
from unittest.mock import patch
from zoneinfo import ZoneInfo

import feedparser

import rss_client
from rss_client import (STATUS_EMPTY, STATUS_FAILED, STATUS_OK,
                        _classify_feed, _fetch_feed_with_status,
                        collect_from_rss_feeds, write_feed_health)

FEED = {"name": "F", "url": "https://example.com/feed", "region": "テスト"}

RSS_ONE = """<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>
<item><title>A</title><link>https://example.com/a</link>
<pubDate>Mon, 09 Nov 2026 01:00:00 GMT</pubDate></item></channel></rss>"""
RSS_NONE = """<?xml version="1.0"?><rss version="2.0"><channel><title>t</title></channel></rss>"""


def _parsed(text, status=None):
    d = feedparser.parse(text)
    if status is not None:
        d["status"] = status
    return d


def test_feed_with_entries_is_ok():
    assert _classify_feed(_parsed(RSS_ONE, 200)) == (STATUS_OK, "")


def test_valid_feed_without_entries_is_empty():
    assert _classify_feed(_parsed(RSS_NONE, 200)) == (STATUS_EMPTY, "")


def test_http_error_is_failed():
    # feedparser returns an empty result for a 404 instead of raising.
    assert _classify_feed(_parsed("", 404)) == (STATUS_FAILED, "HTTP 404")
    assert _classify_feed(_parsed("", 429)) == (STATUS_FAILED, "HTTP 429")


def test_html_page_instead_of_feed_is_failed():
    status, reason = _classify_feed(_parsed("<html><body>moved</body></html>", 200))
    assert status == STATUS_FAILED
    assert reason


def test_network_error_is_failed():
    # What feedparser.parse returns when the connection fails (no status).
    d = feedparser.FeedParserDict(entries=[], bozo=1,
                                  bozo_exception=OSError("timed out"))
    assert _classify_feed(d) == (STATUS_FAILED, "OSError")


def test_exception_during_fetch_is_failed():
    with patch("rss_client.feedparser.parse", side_effect=Exception("boom")):
        articles, status, reason = _fetch_feed_with_status(FEED)
    assert (articles, status, reason) == ([], STATUS_FAILED, "Exception")


def test_articles_unchanged_for_ok_feed():
    with patch("rss_client.feedparser.parse", return_value=_parsed(RSS_ONE, 200)):
        articles, status, _ = _fetch_feed_with_status(FEED)
    assert status == STATUS_OK
    assert [a["title"] for a in articles] == ["A"]
    assert articles[0]["published"].tzinfo is not None


def test_write_feed_health_file(tmp_path):
    now = dt.datetime(2026, 11, 10, 7, 12, tzinfo=ZoneInfo("Asia/Tokyo"))
    results = [
        {"name": "B", "status": STATUS_OK, "count": 3, "reason": ""},
        {"name": "C", "status": STATUS_EMPTY, "count": 0, "reason": ""},
        {"name": "A", "status": STATUS_FAILED, "count": 0, "reason": "HTTP 404"},
    ]
    path = write_feed_health(results, tmp_path, now)
    assert path.name == "feeds-2026-11-10.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert (data["total"], data["ok"], data["empty"], data["failed"]) == (3, 1, 1, 1)
    assert data["feeds"][0]["name"] == "A"  # failed feeds first
    assert data["date"] == "2026-11-10"
    # No temporary files are left behind.
    assert [p.name for p in tmp_path.iterdir()] == ["feeds-2026-11-10.json"]


def test_write_failure_does_not_raise(tmp_path):
    blocker = tmp_path / "health"
    blocker.write_text("not a directory")
    assert write_feed_health([], blocker) is None


def test_collect_records_every_feed(tmp_path):
    feeds = [{"name": n, "url": f"https://example.com/{n}", "region": "テスト"}
             for n in ("ok", "empty", "gone")]
    responses = {
        "https://example.com/ok": _parsed(RSS_ONE, 200),
        "https://example.com/empty": _parsed(RSS_NONE, 200),
        "https://example.com/gone": _parsed("", 410),
    }
    with patch.object(rss_client, "RSS_FEEDS", feeds), \
            patch("rss_client.feedparser.parse", side_effect=lambda url, **_: responses[url]):
        articles = collect_from_rss_feeds(health_dir=tmp_path)
    assert len(articles) == 1
    data = json.loads(next(tmp_path.glob("feeds-*.json")).read_text(encoding="utf-8"))
    by_name = {f["name"]: f for f in data["feeds"]}
    assert by_name["ok"]["status"] == STATUS_OK
    assert by_name["empty"]["status"] == STATUS_EMPTY
    assert by_name["gone"] == {"name": "gone", "status": STATUS_FAILED,
                               "count": 0, "reason": "HTTP 410"}
