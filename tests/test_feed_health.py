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
    assert reason.startswith("not a feed")


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
                               "count": 0, "reason": "HTTP 410", "failed_streak": 1}


# --- Added after the independent review (2026-11-10) ---

def _with_bozo(text, exc, ctype=None, status=200):
    d = _parsed(text, status)
    d["bozo"] = 1
    d["bozo_exception"] = exc
    if ctype:
        d["headers"] = {"content-type": ctype}
    return d


def test_valid_empty_feed_with_mild_warnings_is_empty():
    # A correct RSS with no items served as text/html or with a charset
    # mismatch is still a readable feed, not a failure.
    for name in ("NonXMLContentType", "CharacterEncodingOverride"):
        exc = type(name, (Exception,), {})("warning")
        assert _classify_feed(_with_bozo(RSS_NONE, exc, "text/html")) == (STATUS_EMPTY, "")


def test_valid_feed_with_serious_parse_error_is_failed():
    exc = type("SAXParseException", (Exception,), {})("broken")
    assert _classify_feed(_with_bozo(RSS_NONE, exc)) == (STATUS_FAILED, "SAXParseException")


def test_html_page_reason_names_content_type():
    exc = type("SAXParseException", (Exception,), {})("not xml")
    d = _with_bozo("<html><body>hi</body></html>", exc, "text/html; charset=utf-8", 301)
    assert _classify_feed(d) == (STATUS_FAILED, "not a feed (text/html; charset=utf-8)")


def test_redirect_status_is_not_a_failure():
    # ArXiv answers 302 and is sometimes empty; Mistral answers 301 with items.
    assert _classify_feed(_parsed(RSS_NONE, 302)) == (STATUS_EMPTY, "")
    assert _classify_feed(_parsed(RSS_ONE, 301)) == (STATUS_OK, "")


def test_connection_error_is_failed():
    import urllib.error
    d = feedparser.FeedParserDict(entries=[], bozo=1,
                                  bozo_exception=urllib.error.URLError("refused"))
    assert _classify_feed(d) == (STATUS_FAILED, "URLError")


def test_read_timeout_is_failed():
    with patch("rss_client.feedparser.parse", side_effect=TimeoutError("read")):
        _, status, reason = _fetch_feed_with_status(FEED)
    assert (status, reason) == (STATUS_FAILED, "TimeoutError")


def test_error_status_with_entries_is_failed_but_keeps_articles():
    with patch("rss_client.feedparser.parse", return_value=_parsed(RSS_ONE, 503)):
        articles, status, reason = _fetch_feed_with_status(FEED)
    assert (len(articles), status, reason) == (1, STATUS_FAILED, "HTTP 503")


def _day(d):
    return dt.datetime(2026, 11, d, 7, 12, tzinfo=ZoneInfo("Asia/Tokyo"))


def _streaks(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    return {f["name"]: f["failed_streak"] for f in data["feeds"]}


def test_failed_streak_counts_consecutive_days(tmp_path):
    fail = {"name": "X", "status": STATUS_FAILED, "count": 0, "reason": "HTTP 404"}
    ok = {"name": "Y", "status": STATUS_OK, "count": 2, "reason": ""}
    write_feed_health([fail, ok], tmp_path, _day(10))
    write_feed_health([fail, {**ok, "status": STATUS_FAILED}], tmp_path, _day(11))
    path = write_feed_health([fail, ok], tmp_path, _day(12))
    assert _streaks(path) == {"X": 3, "Y": 0}
    # A day without a record breaks the streak.
    path = write_feed_health([fail, ok], tmp_path, _day(14))
    assert _streaks(path)["X"] == 1


def test_same_day_rerun_does_not_double_count(tmp_path):
    fail = {"name": "X", "status": STATUS_FAILED, "count": 0, "reason": "HTTP 404"}
    write_feed_health([fail], tmp_path, _day(10))
    write_feed_health([fail], tmp_path, _day(11))
    path = write_feed_health([fail], tmp_path, _day(11))
    assert _streaks(path) == {"X": 2}


def test_broken_previous_record_restarts_streak(tmp_path):
    (tmp_path / "feeds-2026-11-09.json").write_text("{not json", encoding="utf-8")
    fail = {"name": "X", "status": STATUS_FAILED, "count": 0, "reason": "HTTP 404"}
    assert _streaks(write_feed_health([fail], tmp_path, _day(10))) == {"X": 1}


def test_collect_returns_articles_when_saving_fails(tmp_path):
    blocker = tmp_path / "health"
    blocker.write_text("not a directory")
    feeds = [{"name": "ok", "url": "https://example.com/ok", "region": "テスト"}]
    with patch.object(rss_client, "RSS_FEEDS", feeds), \
            patch("rss_client.feedparser.parse", return_value=_parsed(RSS_ONE, 200)):
        articles = collect_from_rss_feeds(health_dir=blocker)
    assert len(articles) == 1


def test_collect_writes_nothing_locally_by_default(tmp_path, monkeypatch):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.setattr(rss_client, "HEALTH_DIR", tmp_path / "health")
    feeds = [{"name": "ok", "url": "https://example.com/ok", "region": "テスト"}]
    with patch.object(rss_client, "RSS_FEEDS", feeds), \
            patch("rss_client.feedparser.parse", return_value=_parsed(RSS_ONE, 200)):
        collect_from_rss_feeds()
    assert not (tmp_path / "health").exists()
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    with patch.object(rss_client, "RSS_FEEDS", feeds), \
            patch("rss_client.feedparser.parse", return_value=_parsed(RSS_ONE, 200)):
        collect_from_rss_feeds()
    assert (tmp_path / "health").exists()
