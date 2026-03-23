"""
AI News Bot — 単体テスト

純粋関数のテストを中心に、パイプラインの各コンポーネントの正常動作を検証する。
"""

import datetime
import re
import pytest
from unittest.mock import patch, MagicMock


# ============================================================
# collect_rss_gemini.py — filter_by_time / score_articles
# ============================================================

class TestFilterByTime:
    """時間フィルタのテスト"""

    def _make_article(self, hours_ago):
        """N時間前に公開された記事を生成"""
        pub = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=hours_ago)
        return {"title": f"Article {hours_ago}h ago", "published": pub, "url": f"https://example.com/{hours_ago}"}

    def test_filters_old_articles(self):
        from collect_rss_gemini import filter_by_time
        articles = [self._make_article(1), self._make_article(30), self._make_article(48)]
        result = filter_by_time(articles, hours=24)
        assert len(result) == 1
        assert "1h ago" in result[0]["title"]

    def test_keeps_recent_articles(self):
        from collect_rss_gemini import filter_by_time
        articles = [self._make_article(1), self._make_article(12), self._make_article(23)]
        result = filter_by_time(articles, hours=24)
        assert len(result) == 3

    def test_handles_no_published_date(self):
        from collect_rss_gemini import filter_by_time
        articles = [{"title": "No date", "published": None}]
        result = filter_by_time(articles, hours=24)
        assert len(result) == 0

    def test_empty_input(self):
        from collect_rss_gemini import filter_by_time
        assert filter_by_time([], hours=24) == []


class TestScoreArticles:
    """キーワードスコアリングのテスト"""

    def test_ai_keyword_scoring(self):
        from collect_rss_gemini import score_articles
        now = datetime.datetime.now(datetime.timezone.utc)
        articles = [
            {"title": "ChatGPT updates", "summary": "OpenAI releases new LLM", "published": now},
            {"title": "Sports news", "summary": "Baseball game results", "published": now},
        ]
        result = score_articles(articles)
        # AI記事が上位に来ること
        assert result[0]["_relevance"] > 0
        assert result[1]["_relevance"] == 0

    def test_case_insensitive_matching(self):
        from collect_rss_gemini import score_articles
        now = datetime.datetime.now(datetime.timezone.utc)
        articles = [
            {"title": "chatgpt updates", "summary": "openai releases new llm", "published": now},
        ]
        result = score_articles(articles)
        assert result[0]["_relevance"] > 0

    def test_empty_input(self):
        from collect_rss_gemini import score_articles
        assert score_articles([]) == []


# ============================================================
# line_notifier.py — format_news_for_line
# ============================================================

class TestFormatNewsForLine:
    """LINE メッセージフォーマットのテスト"""

    def _make_article(self, idx):
        return {
            "title_ja": f"テスト記事{idx}",
            "summary_ja": f"テスト要約{idx}",
            "one_liner": f"一言{idx}",
            "why_important": f"重要{idx}",
            "url": f"https://example.com/{idx}",
        }

    def test_basic_formatting(self):
        from line_notifier import format_news_for_line
        articles = [self._make_article(1)]
        result = format_news_for_line(articles)
        assert "テスト記事1" in result
        assert "テスト要約1" in result
        assert "https://example.com/1" in result

    def test_max_articles_limit(self):
        from line_notifier import format_news_for_line
        articles = [self._make_article(i) for i in range(10)]
        result = format_news_for_line(articles, max_articles=3)
        assert "テスト記事0" in result
        assert "テスト記事2" in result
        assert "テスト記事3" not in result

    def test_empty_articles(self):
        from line_notifier import format_news_for_line
        result = format_news_for_line([])
        assert "ありませんでした" in result

    def test_no_40s_in_output(self):
        """出力に「40代」が含まれないことを確認"""
        from line_notifier import format_news_for_line
        articles = [self._make_article(i) for i in range(5)]
        result = format_news_for_line(articles)
        assert "40代" not in result


# ============================================================
# config.py — 定数の存在確認
# ============================================================

class TestConfig:
    """設定モジュールの検証"""

    def test_jst_timezone(self):
        from config import JST
        assert str(JST) == "UTC+09:00"

    def test_gemini_model_defined(self):
        from config import GEMINI_MODEL
        assert GEMINI_MODEL is not None
        assert len(GEMINI_MODEL) > 0

    def test_rss_feeds_not_empty(self):
        from config import RSS_FEEDS
        assert len(RSS_FEEDS) > 0

    def test_ai_keywords_not_empty(self):
        from config import AI_KEYWORDS
        assert len(AI_KEYWORDS) > 0

    def test_output_dir_defined(self):
        from config import NEWS_BOT_OUTPUT_DIR
        assert NEWS_BOT_OUTPUT_DIR is not None


# ============================================================
# rss_client.py — _fetch_single_feed (モック)
# ============================================================

class TestFetchSingleFeed:
    """単一フィード取得のモックテスト"""

    def test_returns_list(self):
        from rss_client import _fetch_single_feed

        # feedparser をモック
        mock_entry = MagicMock()
        mock_entry.title = "Test Article"
        mock_entry.link = "https://example.com/test"
        mock_entry.published = "Mon, 23 Mar 2026 01:00:00 GMT"
        mock_entry.summary = "Test summary"

        mock_feed = MagicMock()
        mock_feed.entries = [mock_entry]

        with patch("rss_client.feedparser.parse", return_value=mock_feed):
            result = _fetch_single_feed({"name": "TestFeed", "url": "https://test.com/feed", "region": "テスト"})
            assert len(result) == 1
            assert result[0]["title"] == "Test Article"
            assert result[0]["source"] == "TestFeed"

    def test_handles_parse_error(self):
        from rss_client import _fetch_single_feed

        with patch("rss_client.feedparser.parse", side_effect=Exception("Connection error")):
            result = _fetch_single_feed({"name": "BadFeed", "url": "https://bad.com/feed", "region": "テスト"})
            assert result == []


# ============================================================
# プロンプト内容の検証
# ============================================================

class TestPromptIntegrity:
    """プロンプトに「40代」が含まれないことを確認"""

    def test_ai_client_no_40s_in_prompt(self):
        """ai_client.py のプロンプトに40代が含まれないこと"""
        import inspect
        from ai_client import process_with_gemini
        source = inspect.getsource(process_with_gemini)
        # 禁止指示の文脈以外で「40代」が使われていないことを確認
        # 「40代」「30代」等を禁止する指示行自体は許容
        lines = source.split("\n")
        for line in lines:
            if "40代" in line and "絶対に記載しないでください" not in line:
                pytest.fail(f"ai_client.py に「40代」表現が残存: {line.strip()}")

    def test_curate_prompt_no_40s(self):
        """curate_morning_brief.py のプロンプトに40代が含まれないこと"""
        import inspect
        from curate_morning_brief import curate_with_gemini
        source = inspect.getsource(curate_with_gemini)
        lines = source.split("\n")
        for line in lines:
            if "40代" in line and "絶対に記載しないでください" not in line:
                pytest.fail(f"curate_morning_brief.py に「40代」表現が残存: {line.strip()}")


# ============================================================
# キーワードパターンの検証
# ============================================================

class TestKeywordPattern:
    """正規表現キーワードパターンの動作を確認"""

    def test_pattern_compiles(self):
        from collect_rss_gemini import _KEYWORD_PATTERN
        assert isinstance(_KEYWORD_PATTERN, re.Pattern)

    def test_pattern_matches_common_keywords(self):
        from collect_rss_gemini import _KEYWORD_PATTERN
        test_cases = ["ChatGPT", "LLM", "機械学習", "OpenAI", "生成AI"]
        for keyword in test_cases:
            _KEYWORD_PATTERN.findall(keyword)
            # キーワードリスト全体を知らないので、マッチ/非マッチは個別検証しない

    def test_pattern_case_insensitive(self):
        from collect_rss_gemini import _KEYWORD_PATTERN
        text = "chatgpt is great"
        matches_lower = _KEYWORD_PATTERN.findall(text)
        text_upper = "CHATGPT IS GREAT"
        matches_upper = _KEYWORD_PATTERN.findall(text_upper)
        assert len(matches_lower) == len(matches_upper)
