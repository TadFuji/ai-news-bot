"""
配信の頑健化（2026-08-31 の総点検で入れた修正）のテスト。

- LINE テキスト 5,000 字上限の切り詰め（超過は API 400 で配信全損になるため）
- Gemini 出力 URL の候補照合（モデルの URL 改変が配信・再配信事故になるため）
- 週刊コラムの同日二重配信ガード（朝刊側と同じ方式の移植）
- X 投稿関数がチャネル成否を戻り値で返すこと（欠配の無音化を防ぐ配線の前提）
"""

import datetime

import pytest
from unittest.mock import patch

from config import JST


class Reached(Exception):
    """処理本体に到達したことを示す番兵。"""


def _reach():
    raise Reached


# ============================================================
# line_notifier.py — send_to_line の上限切り詰め
# ============================================================

class TestLineTextLimit:

    def _capture(self, ln, text):
        sent = {}

        def fake_push(messages):
            sent["text"] = messages[0].text
            return True

        with patch.object(ln, "_push_messages", side_effect=fake_push):
            result = ln.send_to_line(text)
        return result, sent["text"]

    def test_long_text_is_truncated_to_limit(self):
        import line_notifier as ln

        result, text = self._capture(ln, "あ" * (ln._LINE_TEXT_LIMIT + 1000))
        assert result is True
        assert len(text) <= ln._LINE_TEXT_LIMIT
        assert text.endswith("…")

    def test_short_text_passes_unchanged(self):
        import line_notifier as ln

        _, text = self._capture(ln, "こんにちは")
        assert text == "こんにちは"


# ============================================================
# curate_morning_brief.py — keep_known_urls
# ============================================================

class TestKeepKnownUrls:

    def test_drops_articles_with_unknown_urls(self):
        from curate_morning_brief import keep_known_urls

        articles = [
            {"url": "https://example.com/a", "title_ja": "実在"},
            {"url": "https://example.com/hallucinated", "title_ja": "改変"},
        ]
        kept = keep_known_urls(articles, {"https://example.com/a"})

        assert [a["url"] for a in kept] == ["https://example.com/a"]

    def test_keeps_all_when_urls_are_known(self):
        from curate_morning_brief import keep_known_urls

        articles = [{"url": "https://example.com/a"}, {"url": "https://example.com/b"}]
        candidate_urls = {"https://example.com/a", "https://example.com/b"}

        assert keep_known_urls(articles, candidate_urls) == articles


# ============================================================
# generate_weekly_column.py — 同日二重配信ガード
# ============================================================

NOW = datetime.datetime(2026, 8, 30, 9, 47, tzinfo=JST)  # 日曜


class TestAlreadyGeneratedToday:

    def test_true_when_today_column_exists(self, tmp_path):
        from generate_weekly_column import already_generated_today

        (tmp_path / "weekly_column_20260830.md").write_text("x", encoding="utf-8")
        assert already_generated_today(columns_dir=str(tmp_path), now=NOW) is True

    def test_false_when_no_column(self, tmp_path):
        from generate_weekly_column import already_generated_today

        assert already_generated_today(columns_dir=str(tmp_path), now=NOW) is False


class TestWeeklyGuardWiring:
    """main() がガードを実際に見ているか（朝刊側 TestMainGuardWiring と同じ構図）。"""

    def _publish_today(self, monkeypatch, tmp_path):
        import generate_weekly_column as gw

        cols = tmp_path / "columns"
        cols.mkdir()
        today = datetime.datetime.now(JST).strftime("%Y%m%d")
        (cols / f"weekly_column_{today}.md").write_text("x", encoding="utf-8")
        monkeypatch.setattr(gw, "DOCS_DIR", str(tmp_path))
        monkeypatch.setattr(gw, "get_weekly_highlights", _reach)
        return gw

    def test_stops_when_today_already_generated(self, monkeypatch, tmp_path):
        gw = self._publish_today(monkeypatch, tmp_path)
        monkeypatch.delenv("FORCE_REDELIVER", raising=False)

        gw.main()

    def test_stops_when_force_redeliver_is_zero(self, monkeypatch, tmp_path):
        """workflow の非強制実行は '0'（truthy な文字列）を渡す。"""
        gw = self._publish_today(monkeypatch, tmp_path)
        monkeypatch.setenv("FORCE_REDELIVER", "0")

        gw.main()

    def test_proceeds_when_force_redeliver_is_set(self, monkeypatch, tmp_path):
        gw = self._publish_today(monkeypatch, tmp_path)
        monkeypatch.setenv("FORCE_REDELIVER", "1")

        with pytest.raises(Reached):
            gw.main()


# ============================================================
# distribute_daily.py — チャネル成否の戻り値
# ============================================================

class TestXPostReturnsStatus:

    def _clear_creds(self, monkeypatch):
        for key in (
            "X_CONSUMER_KEY", "X_CONSUMER_SECRET",
            "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET",
        ):
            monkeypatch.delenv(key, raising=False)

    def test_single_returns_false_without_credentials(self, monkeypatch):
        import distribute_daily as dd

        self._clear_creds(monkeypatch)
        assert dd.post_to_x_single([{"title_ja": "t"}]) is False

    def test_thread_returns_false_without_credentials(self, monkeypatch):
        import distribute_daily as dd

        self._clear_creds(monkeypatch)
        assert dd.post_to_x_thread([{"title_ja": "t"}]) is False
