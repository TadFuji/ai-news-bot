"""jev_selector — Jev による記事選定のテスト（API は呼ばない）"""

import datetime

import pytest

import jev_client
import jev_selector


def _answers(interest, not_ai=0.0, promo=0.0):
    return {
        "interest": {"score": interest, "confidence": 0.9},
        "category": {"choice": "not_ai" if not_ai >= 0.5 else "chat_ai",
                     "probabilities": {"not_ai": not_ai}},
        "promo": {"noul": promo},
    }


def _article(i, title=None):
    return {
        "title": title or f"Distinct headline number {i} about topic {i * 7919}",
        "url": f"https://example.com/{i}",
        "summary": f"<p>Summary {i}</p>",
        "source": "Example",
        "published": datetime.datetime(2026, 9, 19, tzinfo=datetime.timezone.utc),
    }


def _fake_decide(table):
    def decide(state, questions, key):
        assert set(questions) == {"interest", "category", "promo"}
        assert "source" not in state  # the source is deliberately not sent
        ans = table[state["headline"]]
        if isinstance(ans, Exception):
            raise ans
        return {"answers": ans, "usage": {"cost": 0.00005}, "elapsed_ms": 1}
    return decide


@pytest.fixture
def key(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")


class TestRankOf:
    def test_interest_drives_rank(self):
        assert jev_selector.rank_of(_answers(3.0)) > jev_selector.rank_of(_answers(1.0))

    def test_non_ai_is_excluded(self):
        assert jev_selector.rank_of(_answers(4.0, not_ai=0.6)) < 0

    def test_clear_ad_is_excluded(self):
        assert jev_selector.rank_of(_answers(4.0, promo=0.8)) < 0

    def test_low_promo_is_not_penalised(self):
        assert jev_selector.rank_of(_answers(2.0, promo=0.2)) == pytest.approx(2.0)


class TestSelectArticles:
    def test_no_key_falls_back(self, monkeypatch):
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        assert jev_selector.select_articles([_article(1)], decide=_fake_decide({})) is None

    def test_top_n_in_jev_order_with_exclusions(self, key):
        arts = [_article(i) for i in range(1, 16)]
        table = {a["title"]: _answers(i / 4) for i, a in enumerate(arts, 1)}
        table[arts[-1]["title"]] = _answers(4.0, not_ai=0.9)   # best score but not AI
        table[arts[-2]["title"]] = _answers(4.0, promo=0.95)   # best score but an ad
        picked = jev_selector.select_articles(arts, n=10, decide=_fake_decide(table))
        assert [a["url"] for a in picked] == [f"https://example.com/{i}" for i in range(13, 3, -1)]
        assert [a["jev_rank"] for a in picked] == list(range(1, 11))
        assert all("importance_score" not in a for a in picked)

    def test_same_event_is_bundled(self, key):
        arts = [_article(1, "OpenAI launches GPT-6 Astra model for everyone"),
                _article(2, "OpenAI launches GPT-6 Astra model for everyone today"),
                _article(3)]
        table = {arts[0]["title"]: _answers(3.0), arts[1]["title"]: _answers(2.9),
                 arts[2]["title"]: _answers(1.0)}
        picked = jev_selector.select_articles(arts, n=10, decide=_fake_decide(table))
        assert [a["url"] for a in picked] == ["https://example.com/1", "https://example.com/3"]

    def test_duplicate_urls_are_scored_and_counted_once(self, key):
        arts = [_article(i) for i in range(1, 4)]
        arts += [dict(arts[0]), dict(arts[1])]  # same URLs from other feeds
        table = {a["title"]: _answers(2.0) for a in arts}
        table[arts[2]["title"]] = _answers(3.0, not_ai=0.9)
        calls = []

        def decide(state, questions, k):
            calls.append(state["headline"])
            return _fake_decide(table)(state, questions, k)
        picked = jev_selector.select_articles(arts, decide=decide)
        assert len(calls) == 3
        assert [a["url"] for a in picked] == ["https://example.com/1", "https://example.com/2"]

    def test_too_many_failures_fall_back(self, key):
        arts = [_article(i) for i in range(1, 11)]
        table = {a["title"]: jev_client.JevError("HTTP 500") for a in arts}
        table[arts[0]["title"]] = _answers(3.0)
        assert jev_selector.select_articles(arts, decide=_fake_decide(table)) is None

    def test_few_failures_are_skipped(self, key):
        arts = [_article(i) for i in range(1, 11)]
        table = {a["title"]: _answers(2.0) for a in arts}
        table[arts[0]["title"]] = jev_client.JevError("connection failed (TimeoutError)")
        picked = jev_selector.select_articles(arts, decide=_fake_decide(table))
        assert len(picked) == 9 and "https://example.com/1" not in {a["url"] for a in picked}


class TestCollectFallback:
    def test_unexpected_error_falls_back(self, monkeypatch):
        import collect_rss_gemini

        def boom(*a, **k):
            raise RuntimeError("unexpected")
        monkeypatch.setattr(jev_selector, "select_articles", boom)
        monkeypatch.setattr("curate_morning_brief.get_delivered_urls", lambda days=3: set())
        assert collect_rss_gemini.select_with_jev([_article(1)]) is None

    def test_delivered_urls_are_excluded_before_jev(self, monkeypatch):
        import collect_rss_gemini
        seen = {}

        def capture(articles, n=10):
            seen["urls"] = [a["url"] for a in articles]
            return articles
        monkeypatch.setattr(jev_selector, "select_articles", capture)
        monkeypatch.setattr("curate_morning_brief.get_delivered_urls",
                            lambda days=3: {"https://example.com/1"})
        collect_rss_gemini.select_with_jev([_article(1), _article(2)])
        assert seen["urls"] == ["https://example.com/2"]


class TestScoreAllSafety:
    def test_fatal_status_stops_scoring(self, key):
        arts = [_article(i) for i in range(1, 40)]
        calls = []

        def decide(state, questions, k):
            calls.append(1)
            raise jev_client.JevError("HTTP 401", status=401)
        assert jev_selector.select_articles(arts, decide=decide) is None
        assert len(calls) < len(arts) * 2  # no retry passes after a key error

    def test_deadline_skips_remaining_calls(self, key):
        arts = [_article(i) for i in range(1, 6)]
        table = {a["title"]: _answers(2.0) for a in arts}
        res = jev_selector.score_all(arts, "k", _fake_decide(table), deadline_sec=-1)
        assert res == {}

    def test_malformed_answers_count_as_failures(self, key):
        arts = [_article(i) for i in range(1, 6)]
        table = {a["title"]: {"interest": {"score": 2.0}} for a in arts}  # no category/promo
        assert jev_selector.select_articles(arts, decide=_fake_decide(table)) is None


class TestJevClient:
    def _raise(self, exc):
        def urlopen(*a, **k):
            raise exc
        return urlopen

    def test_http_error_hides_body_and_key(self, monkeypatch):
        import io
        import urllib.error
        err = urllib.error.HTTPError("https://x", 402, "Payment Required", {},
                                     io.BytesIO(b"secret-body echo test-key"))
        monkeypatch.setattr(jev_client.urllib.request, "urlopen", self._raise(err))
        with pytest.raises(jev_client.JevError) as e:
            jev_client.decide({"headline": "h"}, {}, "test-key")
        assert str(e.value) == "HTTP 402" and e.value.status == 402

    def test_incomplete_read_becomes_jev_error(self, monkeypatch):
        import http.client
        monkeypatch.setattr(jev_client.urllib.request, "urlopen",
                            self._raise(http.client.IncompleteRead(b"partial")))
        with pytest.raises(jev_client.JevError) as e:
            jev_client.decide({"headline": "h"}, {}, "k")
        assert "IncompleteRead" in str(e.value) and e.value.status is None


class TestPipelineGlue:
    def test_dropped_stage1_picks_are_restored_in_jev_order(self):
        import collect_rss_gemini
        picks = [dict(_article(i), jev_rank=i, full_text="body") for i in (1, 2, 3)]
        processed = [dict(picks[2], title_ja="三"), dict(picks[0], title_ja="一")]
        for a in processed:
            a.pop("full_text")
        out = collect_rss_gemini.keep_all_jev_picks(processed, picks)
        assert [a["jev_rank"] for a in out] == [1, 2, 3]
        assert "full_text" not in out[1] and isinstance(out[1]["published"], str)

    def test_brief_is_reordered_by_jev_rank(self):
        from curate_morning_brief import order_by_jev_rank
        cands = [{"url": f"u{i}", "jev_rank": i} for i in (1, 2, 3)]
        brief = {"articles": [{"url": "u3"}, {"url": "x"}, {"url": "u1"}, {"url": "u2"}]}
        order_by_jev_rank(brief, cands)
        assert [a["url"] for a in brief["articles"]] == ["u1", "u2", "u3", "x"]

    def test_keyword_day_keeps_gemini_order(self):
        from curate_morning_brief import order_by_jev_rank
        brief = {"articles": [{"url": "b"}, {"url": "a"}]}
        order_by_jev_rank(brief, [{"url": "a"}, {"url": "b"}])
        assert [a["url"] for a in brief["articles"]] == ["b", "a"]
