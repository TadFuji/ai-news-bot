"""Minimal client for TypeSafe Jev via the OpenRouter Decisions API (alpha).

Standard library only. The API key is read from OPENROUTER_API_KEY and is
never printed or written anywhere; error messages never include the upstream body.
"""

import json
import os
import time
import urllib.error
import urllib.request

ENDPOINT = "https://openrouter.ai/api/alpha/decisions"
MODEL = "typesafe/jev-1.13"
INPUT_PRICE_USD = 0.042 / 1_000_000  # openrouter.ai/typesafe/jev-1.13, checked 2026-09-19
TIMEOUT_SEC = 30


class JevError(Exception):
    """Raised with a message that never contains the key or the upstream body."""


def load_key() -> str:
    return os.environ.get("OPENROUTER_API_KEY", "").strip()


def decide(state: dict, questions: dict, key: str) -> dict:
    """Send one decisions request and return {answers, usage, elapsed_ms}."""
    body = json.dumps({"model": MODEL, "state": state, "questions": questions}).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "X-Title": "ai-news-bot",
        },
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as res:
            data = json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        # Do not reflect the upstream body: it may echo request content.
        raise JevError(f"HTTP {e.code}") from None
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise JevError(f"connection failed ({type(e).__name__})") from None
    except ValueError:
        raise JevError("response was not JSON") from None
    answers = data.get("answers")
    if not isinstance(answers, dict):
        raise JevError("response has no answers")
    return {
        "answers": answers,
        "usage": data.get("usage") or {},
        "elapsed_ms": round((time.perf_counter() - started) * 1000),
    }


def cost_of(usage: dict) -> float:
    cost = usage.get("cost")
    if isinstance(cost, (int, float)):
        return float(cost)
    tokens = usage.get("input_tokens")
    return tokens * INPUT_PRICE_USD if isinstance(tokens, int) else 0.0
