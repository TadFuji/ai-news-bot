"""
同日二重配信の防止と、配信済みURLの参照先のテスト。

GitHub の定時起動が遅れて手動実行と重なると、同じ日に2回配信されていた。
配信済みの判定は公開済みの docs/YYYY-MM-DD.json を唯一の根拠にする
（output/ は CI のチェックアウトに含まれず、常に空になるため）。
"""

import datetime
import json

from config import JST
from curate_morning_brief import already_delivered_today, get_delivered_urls


NOW = datetime.datetime(2026, 8, 28, 6, 47, tzinfo=JST)


def _write(docs_dir, date_str, urls=()):
    payload = {"articles": [{"url": u} for u in urls]}
    (docs_dir / f"{date_str}.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )


class TestAlreadyDeliveredToday:
    """本日分が公開済みかの判定"""

    def test_true_when_today_published(self, tmp_path):
        _write(tmp_path, "2026-08-28")
        assert already_delivered_today(docs_dir=str(tmp_path), now=NOW) is True

    def test_false_when_only_yesterday_published(self, tmp_path):
        _write(tmp_path, "2026-08-27")
        assert already_delivered_today(docs_dir=str(tmp_path), now=NOW) is False

    def test_false_when_docs_empty(self, tmp_path):
        assert already_delivered_today(docs_dir=str(tmp_path), now=NOW) is False


class TestGetDeliveredUrls:
    """過去N日間の配信済みURLの収集"""

    def test_collects_from_past_three_days(self, tmp_path):
        _write(tmp_path, "2026-08-27", ["https://example.com/a"])
        _write(tmp_path, "2026-08-25", ["https://example.com/c"])

        urls = get_delivered_urls(days=3, docs_dir=str(tmp_path), now=NOW)

        assert urls == {"https://example.com/a", "https://example.com/c"}

    def test_excludes_days_outside_window(self, tmp_path):
        _write(tmp_path, "2026-08-24", ["https://example.com/old"])

        urls = get_delivered_urls(days=3, docs_dir=str(tmp_path), now=NOW)

        assert urls == set()

    def test_today_is_not_treated_as_past(self, tmp_path):
        """当日分は対象外。同じ日の再実行は already_delivered_today が止める。"""
        _write(tmp_path, "2026-08-28", ["https://example.com/today"])

        urls = get_delivered_urls(days=3, docs_dir=str(tmp_path), now=NOW)

        assert urls == set()
