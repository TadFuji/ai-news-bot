"""Offline tests for Flex inference, Standard fallback, and 50% usage metering."""
import datetime as dt
import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import ai_client
import config
import curate_morning_brief
import generate_weekly_column
import usage_meter
from generators import infographic_maker


def _fake_usage(prompt=1_000_000, candidates=1_000_000):
    return SimpleNamespace(
        prompt_token_count=prompt,
        cached_content_token_count=0,
        candidates_token_count=candidates,
        thoughts_token_count=0,
        tool_use_prompt_token_count=0,
        total_token_count=prompt + candidates,
    )


def _sample_articles():
    return [
        {
            "title": "Test AI Release",
            "source": "Example",
            "region": "米国",
            "summary": "Summary body",
            "url": "https://example.com/1",
            "published": dt.datetime(2026, 11, 16, 0, 0, tzinfo=dt.timezone.utc),
            "importance_score": 9,
            "category": "研究・技術",
        }
    ]


class _FakeModels:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class _FakeClient:
    def __init__(self, outcomes):
        self.models = _FakeModels(outcomes)


def _tier_val(cfg):
    t = getattr(cfg, "service_tier", None)
    return getattr(t, "value", t)


def _thinking_val(cfg):
    tc = getattr(cfg, "thinking_config", None)
    lvl = getattr(tc, "thinking_level", None) if tc is not None else None
    return getattr(lvl, "value", lvl)


class FlexInferenceTests(unittest.TestCase):
    def test_stage1_uses_flex_with_low_thinking_and_bills_half(self):
        payload = json.dumps([
            {
                "index": 1,
                "title_ja": "テスト",
                "summary_ja": "要約",
                "one_liner": "一言",
                "why_important": "重要",
                "action_item": "行動",
                "category": "研究・技術",
                "importance_score": 9,
                "reason": "理由",
            }
        ])
        fake_client = _FakeClient([SimpleNamespace(text=payload, usage_metadata=_fake_usage())])
        meter = usage_meter.UsageMeter()
        meter.enabled = True
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "dummy-key"}), \
             patch.object(ai_client.genai, "Client", return_value=fake_client), \
             patch.object(ai_client, "meter", meter):
            res = ai_client.process_with_gemini(_sample_articles(), max_articles=10)

        self.assertEqual(len(res), 1)
        cfg = fake_client.models.calls[0]["config"]
        self.assertEqual(_tier_val(cfg), "flex")
        self.assertEqual(_thinking_val(cfg), "LOW")
        self.assertEqual(getattr(cfg.http_options, "timeout", None), config.GEMINI_FLEX_TIMEOUT_MS)
        self.assertAlmostEqual(meter.totals()["usd"], 4.5, places=6)

    def test_stage1_retries_flex_once_then_falls_back_to_standard(self):
        payload = json.dumps([
            {
                "index": 1,
                "title_ja": "復旧",
                "summary_ja": "要約",
                "one_liner": "一言",
                "why_important": "重要",
                "action_item": "行動",
                "category": "研究・技術",
                "importance_score": 8,
                "reason": "理由",
            }
        ])
        # Single 503 -> 2nd attempt still uses Flex (50% price)
        fake_flex_retry = _FakeClient([
            RuntimeError("503 Service Unavailable"),
            SimpleNamespace(text=payload, usage_metadata=_fake_usage()),
        ])
        meter_flex = usage_meter.UsageMeter()
        meter_flex.enabled = True
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "dummy-key"}), \
             patch.object(ai_client.genai, "Client", return_value=fake_flex_retry), \
             patch.object(ai_client, "meter", meter_flex), \
             patch.object(ai_client.time, "sleep"):
            res_flex = ai_client.process_with_gemini(_sample_articles(), max_articles=10)

        self.assertEqual(res_flex[0]["title_ja"], "復旧")
        self.assertEqual(len(fake_flex_retry.models.calls), 2)
        self.assertEqual(_tier_val(fake_flex_retry.models.calls[0]["config"]), "flex")
        self.assertEqual(_tier_val(fake_flex_retry.models.calls[1]["config"]), "flex")
        self.assertAlmostEqual(meter_flex.totals()["usd"], 4.5, places=6)

        # Two consecutive Flex failures -> 3rd attempt falls back to Standard
        fake_client = _FakeClient([
            RuntimeError("503 Service Unavailable"),
            RuntimeError("503 Service Unavailable"),
            SimpleNamespace(text=payload, usage_metadata=_fake_usage()),
        ])
        meter = usage_meter.UsageMeter()
        meter.enabled = True
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "dummy-key"}), \
             patch.object(ai_client.genai, "Client", return_value=fake_client), \
             patch.object(ai_client, "meter", meter), \
             patch.object(ai_client.time, "sleep"):
            res = ai_client.process_with_gemini(_sample_articles(), max_articles=10)

        self.assertEqual(res[0]["title_ja"], "復旧")
        self.assertEqual(len(fake_client.models.calls), 3)
        self.assertEqual(_tier_val(fake_client.models.calls[0]["config"]), "flex")
        self.assertEqual(_tier_val(fake_client.models.calls[1]["config"]), "flex")
        self.assertIsNone(_tier_val(fake_client.models.calls[2]["config"]))
        self.assertIsNone(getattr(fake_client.models.calls[2]["config"], "http_options", None))
        self.assertAlmostEqual(meter.totals()["usd"], 9.0, places=6)

    def test_stage1_aborts_immediately_on_invalid_api_key(self):
        fake_client = _FakeClient([
            RuntimeError("400 INVALID_ARGUMENT: API key not valid"),
            SimpleNamespace(text="[]", usage_metadata=_fake_usage()),
        ])
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "bad-key"}), \
             patch.object(ai_client.genai, "Client", return_value=fake_client), \
             patch.object(ai_client.time, "sleep") as mock_sleep:
            res = ai_client.process_with_gemini(_sample_articles(), max_articles=10)

        self.assertEqual(len(fake_client.models.calls), 1)
        mock_sleep.assert_not_called()
        self.assertEqual(res[0]["url"], "https://example.com/1")

    def test_stage2_curate_flex_and_standard_fallback(self):
        payload = json.dumps({
            "theme": "テストテーマ",
            "morning_comment": "一言",
            "articles": [
                {
                    "title_ja": "テスト",
                    "summary_ja": "要約",
                    "one_liner": "一言",
                    "why_important": "重要",
                    "action_item": "行動",
                    "category": "研究・技術",
                    "source": "Example",
                    "url": "https://example.com/1",
                }
            ],
        })
        fake_client = _FakeClient([
            RuntimeError("503 Flex busy"),
            RuntimeError("INVALID_ARGUMENT on flex tier"),
            SimpleNamespace(text=payload, usage_metadata=_fake_usage()),
        ])
        meter = usage_meter.UsageMeter()
        meter.enabled = True
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "dummy-key"}), \
             patch.object(curate_morning_brief.genai, "Client", return_value=fake_client), \
             patch.object(curate_morning_brief, "meter", meter), \
             patch.object(curate_morning_brief.time, "sleep"):
            res = curate_morning_brief.curate_with_gemini(_sample_articles())

        self.assertEqual(res["theme"], "テストテーマ")
        self.assertEqual(len(fake_client.models.calls), 3)
        self.assertEqual(_tier_val(fake_client.models.calls[0]["config"]), "flex")
        self.assertEqual(_tier_val(fake_client.models.calls[1]["config"]), "flex")
        self.assertIsNone(_tier_val(fake_client.models.calls[2]["config"]))
        self.assertAlmostEqual(meter.totals()["usd"], 9.0, places=6)

    def test_weekly_column_flex_and_standard_fallback(self):
        fake_client_ok = _FakeClient([SimpleNamespace(text="コラム本文", usage_metadata=_fake_usage())])
        meter_flex = usage_meter.UsageMeter()
        meter_flex.enabled = True
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "dummy-key"}), \
             patch.object(generate_weekly_column.genai, "Client", return_value=fake_client_ok), \
             patch.object(generate_weekly_column, "meter", meter_flex):
            text = generate_weekly_column.generate_column(_sample_articles())
        self.assertEqual(text, "コラム本文")
        self.assertEqual(_tier_val(fake_client_ok.models.calls[0]["config"]), "flex")
        self.assertEqual(_thinking_val(fake_client_ok.models.calls[0]["config"]), "LOW")
        self.assertAlmostEqual(meter_flex.totals()["usd"], 4.5, places=6)

        fake_client_fb = _FakeClient([
            RuntimeError("503 Flex busy"),
            RuntimeError("503 Flex busy again"),
            RuntimeError("503 Standard blip"),
            SimpleNamespace(text="復旧コラム", usage_metadata=_fake_usage()),
        ])
        meter_fb = usage_meter.UsageMeter()
        meter_fb.enabled = True
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "dummy-key"}), \
             patch.object(generate_weekly_column.genai, "Client", return_value=fake_client_fb), \
             patch.object(generate_weekly_column, "meter", meter_fb), \
             patch.object(generate_weekly_column.time, "sleep"):
            text_fb = generate_weekly_column.generate_column(_sample_articles())
        self.assertEqual(text_fb, "復旧コラム")
        self.assertEqual(len(fake_client_fb.models.calls), 4)
        self.assertEqual(_tier_val(fake_client_fb.models.calls[0]["config"]), "flex")
        self.assertEqual(_tier_val(fake_client_fb.models.calls[1]["config"]), "flex")
        self.assertIsNone(_tier_val(fake_client_fb.models.calls[2]["config"]))
        self.assertIsNone(_tier_val(fake_client_fb.models.calls[3]["config"]))
        self.assertAlmostEqual(meter_fb.totals()["usd"], 9.0, places=6)

    def test_infographic_maker_uses_minimal_thinking_and_2k(self):
        img_part = SimpleNamespace(inline_data=SimpleNamespace(data=b"pngbytes"))
        resp = SimpleNamespace(candidates=[SimpleNamespace(content=SimpleNamespace(parts=[img_part]))])
        fake_client = _FakeClient([resp])
        with patch.dict(os.environ, {"GEMINI_IMAGE_API_KEY": "dummy-img-key"}), \
             patch("google.genai.Client", return_value=fake_client), \
             patch.object(infographic_maker, "meter", usage_meter.UsageMeter()):
            out = infographic_maker._generate_image("prompt")
        self.assertEqual(out, b"pngbytes")
        cfg = fake_client.models.calls[0]["config"]
        self.assertEqual(_thinking_val(cfg), "MINIMAL")
        self.assertEqual(cfg.image_config.image_size, "2K")


if __name__ == "__main__":
    unittest.main()
