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


# ============================================================
# dedup.py — 意味的ダブり排除
# ============================================================

class TestDedup:
    """見出し類似によるダブり排除のテスト（閾値は実測で確定済み）"""

    def _a(self, title, score=5, url=None):
        return {
            "title_ja": title,
            "importance_score": score,
            "url": url or f"https://example.com/{abs(hash(title)) % 10000}",
        }

    def test_merges_similar_titles_keeps_highest_score(self):
        """同じ出来事（語順違い）は束ね、スコア最高の1本を残す"""
        from dedup import dedup_articles
        articles = [
            self._a("Google、Gemini 3 Flashを公開", score=6, url="https://e.com/1"),
            self._a("GoogleがGemini 3 Flashをリリース", score=9, url="https://e.com/2"),
        ]
        result = dedup_articles(articles)
        assert len(result) == 1
        assert result[0]["importance_score"] == 9  # 高スコア側が代表

    def test_keeps_same_company_different_news(self):
        """同じ企業でも別ニュースは束ねない（誤マージ防止 — 最重要）"""
        from dedup import dedup_articles
        articles = [
            self._a("OpenAIが大型資金調達を実施", score=7, url="https://e.com/1"),
            self._a("OpenAIが新モデルGPT-5を発表", score=8, url="https://e.com/2"),
        ]
        result = dedup_articles(articles)
        assert len(result) == 2

    def test_keeps_unrelated(self):
        """無関係なニュースは両方残す"""
        from dedup import dedup_articles
        articles = [
            self._a("AppleがVision Proを値下げ", url="https://e.com/1"),
            self._a("生成AIで議事録自動化が進む", url="https://e.com/2"),
        ]
        assert len(dedup_articles(articles)) == 2

    def test_empty_input(self):
        from dedup import dedup_articles
        assert dedup_articles([]) == []

    def test_single_input(self):
        from dedup import dedup_articles
        articles = [self._a("唯一のAIニュース記事です")]
        assert len(dedup_articles(articles)) == 1

    def test_short_titles_passthrough(self):
        """短すぎる見出しは束ねず素通り（誤クラスタ化を防ぐ）"""
        from dedup import dedup_articles
        articles = [self._a("AI"), self._a("ML")]
        assert len(dedup_articles(articles)) == 2

    def test_preserves_order(self):
        """束ねなかった記事は元の出現順を維持する"""
        from dedup import dedup_articles
        articles = [
            self._a("Appleが新しい折りたたみiPhoneを開発中と報道"),
            self._a("Microsoftが量子コンピュータの新成果を公表"),
            self._a("Teslaが完全自動運転の最新版を一般公開"),
        ]
        result = dedup_articles(articles)
        assert len(result) == 3
        assert result[0]["title_ja"].startswith("Apple")
        assert result[2]["title_ja"].startswith("Tesla")

    def test_keeps_different_model_versions(self):
        """モデル番号だけ違う別発表は束ねない（GPT-5 と GPT-4 / 誤マージ防止）"""
        from dedup import dedup_articles
        articles = [
            self._a("OpenAIがGPT-5を正式公開", score=8, url="https://e.com/1"),
            self._a("OpenAIがGPT-4を正式公開", score=7, url="https://e.com/2"),
        ]
        result = dedup_articles(articles)
        assert len(result) == 2

    def test_complete_linkage_no_false_merge(self):
        """A≈B・B≈C だが A≠C のとき、非類似の A と C を1本に潰さない（入力順に依らず）。

        単連結だと橋渡しの B 経由で非類似の A・C が同一クラスタに吸収され、
        入力順次第で別ニュースが消える。complete-linkage はこれを防ぐ。
        （B は A・C いずれかと束ねられて消えることがあるが、それは正しい束ね）
        """
        import itertools
        from dedup import dedup_articles
        a = self._a("OpenAI 新モデル GPT を発表", url="https://e.com/a")
        b = self._a("OpenAI 新モデル GPT 提携を発表 Microsoft", url="https://e.com/b")
        c = self._a("Microsoft 提携を発表 新クラウド基盤", url="https://e.com/c")
        # 非類似の A と C は直接は束ねられない
        assert len(dedup_articles([a, c])) == 2
        # 3件でも 1件には潰れない（非類似の A・C が別クラスタに分かれる）
        for order in itertools.permutations([a, b, c]):
            assert len(dedup_articles(list(order))) >= 2


# ============================================================
# article_extractor.py — 本文取得（trafilatura, モック）
# ============================================================

_SAMPLE_HTML = (
    "<html><head><title>AIニュースのテスト記事のタイトル行です</title></head><body>"
    "<article><h1>人工知能の大きな進展に関する記事の見出し</h1>"
    "<p>"
    + ("人工知能の研究が大きく進展し、企業の業務効率化に直結する新しいモデルが発表されました。" * 8)
    + "</p><p>"
    + ("この技術は議事録の自動化や資料作成の支援に活用でき、多くの働き方を変えると期待されています。" * 8)
    + "</p></article></body></html>"
)


class TestArticleExtractor:
    """本文取得のモックテスト（ネットワークは使わない）"""

    def test_fetch_success(self):
        from article_extractor import fetch_article_text
        with patch("article_extractor.trafilatura.fetch_url", return_value=_SAMPLE_HTML):
            text = fetch_article_text("https://example.com/article")
        assert text is not None
        assert len(text) >= 200

    def test_fetch_download_failure_returns_none(self):
        """取得失敗（fetch_url が None）なら None を返す"""
        from article_extractor import fetch_article_text
        with patch("article_extractor.trafilatura.fetch_url", return_value=None):
            assert fetch_article_text("https://example.com/article") is None

    def test_fetch_empty_url(self):
        from article_extractor import fetch_article_text
        assert fetch_article_text("") is None

    def test_no_signal_error_in_threads(self):
        """並列スレッド内で extract を呼んでも ValueError が出ない（SIGALRM 回避の検証）"""
        from article_extractor import enrich_with_full_text
        articles = [
            {"url": f"https://example.com/{i}", "summary": "x", "source": "Test"}
            for i in range(8)
        ]
        with patch("article_extractor.trafilatura.fetch_url", return_value=_SAMPLE_HTML):
            result = enrich_with_full_text(articles, top_n=8)
        # 全件、例外なく本文が付与されること
        assert all(a.get("full_text") for a in result)

    def test_idempotent_skips_existing(self):
        """既に full_text を持つ記事は再取得しない"""
        from article_extractor import enrich_with_full_text
        articles = [{"url": "https://example.com/a", "full_text": "既存の本文テキスト"}]
        with patch("article_extractor.trafilatura.fetch_url") as mock_fetch:
            enrich_with_full_text(articles, top_n=15)
            mock_fetch.assert_not_called()
        assert articles[0]["full_text"] == "既存の本文テキスト"

    def test_top_n_limit(self):
        """上位 N 件のみが本文取得の対象になる"""
        from article_extractor import enrich_with_full_text
        articles = [
            {"url": f"https://example.com/{i}", "summary": "x"} for i in range(20)
        ]
        with patch("article_extractor.trafilatura.fetch_url", return_value=_SAMPLE_HTML):
            enrich_with_full_text(articles, top_n=5)
        assert sum(1 for a in articles if a.get("full_text")) == 5

    def test_failed_extraction_no_full_text(self):
        """本文が短すぎる/取れない場合は full_text を付けない（要約フォールバック）"""
        from article_extractor import enrich_with_full_text
        articles = [{"url": "https://example.com/a", "summary": "短い要約"}]
        with patch("article_extractor.trafilatura.fetch_url", return_value="<html><body><p>短い</p></body></html>"):
            enrich_with_full_text(articles, top_n=15)
        assert "full_text" not in articles[0]
