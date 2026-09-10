"""Gemini API のトークン使用量と概算費用を、実行 1 回ごとに記録する。

なぜこれがあるか
----------------
ai-news-bot / Hacker-News / reddit / x-morning-brief の 4 系統は毎日自動で動き、
そのたびに Gemini の従量課金が発生する。2026-09-10 のプロンプト監査の時点では
どれもトークン数を記録しておらず、「今月いくら使ったか」「どの工程が重いか」を
後から調べる手段が無かった。このモジュールはその 1 点だけを担う。

使い方
------
    from usage_meter import meter

    resp = client.models.generate_content(model=MODEL, contents=prompt)
    meter.record(MODEL, resp, label="summary")      # 応答を受け取るたびに

    meter.record_image(IMAGE_MODEL, label="cover")  # 画像は枚数で数える

    # 実行の終わりに 1 回
    print(meter.summary_line())
    meter.flush(log_dir="usage", run={"articles": 30})

`flush()` は `<log_dir>/usage-YYYY-MM.jsonl` へ 1 行追記する（月ごとに 1 ファイル）。
1 行 = 1 実行。読むときは `python3 usage_meter.py usage/` で月次集計が出る。

止め方・変え方（環境変数）
--------------------------
    USAGE_METER=0          記録も書き出しもしない
    USAGE_LOG_DIR=<path>   書き出し先を上書きする
    USAGE_JPY_PER_USD=157  円換算のレート（既定 157）

このモジュールは**外に例外を出さない**。計測の不具合で本番の配信を落とさない
ため、内部の失敗はすべて捕捉して `meter.errors` に理由を積むだけにする。
呼び出し側に try/except を書く必要はない。

費用はあくまで概算
------------------
下の単価表は 2026-09-10 に https://ai.google.dev/gemini-api/docs/pricing の
有料ティア表を見て書き写したもの。**正式な請求額は Google Cloud の請求画面が正典**で、
この数字は「桁が合っているか」「どの工程が重いか」を見るためのもの。
単価表に無いモデルはトークン数だけ記録し、費用は unknown として集計から外す
（推測で金額を出さない）。単価が変わったら PRICES と PRICES_CHECKED を直す。
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import threading
from pathlib import Path

PRICES_CHECKED = "2026-09-10"
PRICES_SOURCE = "https://ai.google.dev/gemini-api/docs/pricing"

# 1M トークンあたりの USD。(input, output)
# 3.8 / 3.7 / 3.6 Flash は 2026-12-31 までの割引価格。翌日から倍になる。
_FLASH_3X_DISCOUNT_UNTIL = _dt.date(2026, 12, 31)
_FLASH_3X_DISCOUNTED = (0.75, 3.75)
_FLASH_3X_STANDARD = (1.50, 7.50)

PRICES: dict[str, tuple[float, float]] = {
    "gemini-3.5-flash": (1.50, 9.00),
    "gemini-3.5-flash-lite": (0.30, 2.50),
    "gemini-3.1-flash-lite": (0.25, 1.50),
    "gemini-3.1-pro-preview": (2.00, 12.00),  # 入力 200k 超は $4.00 / 出力 $18.00
    "gemini-2.5-pro": (1.25, 10.00),          # 入力 200k 超は $2.50 / 出力 $15.00
    "gemini-2.5-flash": (0.30, 2.50),
    "gemini-2.5-flash-lite": (0.10, 0.40),
}

# 1 枚あたりの USD。解像度で変わるものは 1K/2K の値を既定にする。
IMAGE_PRICES: dict[str, float] = {
    "gemini-3-pro-image": 0.134,          # 1K/2K。4K は 0.24
    "gemini-3.1-flash-image": 0.067,      # 1K。0.5K=0.045 / 2K=0.101 / 4K=0.151
    "gemini-3.1-flash-lite-image": 0.0336,
    "gemini-2.5-flash-image": 0.039,
}


def _text_price(model: str, on: _dt.date) -> tuple[float, float] | None:
    """モデル ID から (入力単価, 出力単価) を引く。不明なら None。"""
    if model in PRICES:
        return PRICES[model]
    if model in ("gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash"):
        return _FLASH_3X_DISCOUNTED if on <= _FLASH_3X_DISCOUNT_UNTIL else _FLASH_3X_STANDARD
    return None


def _int(value) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


class UsageMeter:
    """1 プロセス内の Gemini 呼び出しを足し上げる。スレッドセーフ。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.calls: list[dict] = []
        self.errors: list[str] = []
        self.started_at = _dt.datetime.now(_dt.timezone.utc)
        self.enabled = os.environ.get("USAGE_METER", "1") != "0"

    # ---- 記録 -------------------------------------------------------------

    def record(self, model: str, response, label: str = "") -> None:
        """generate_content の応答からトークン数を拾う。失敗しても黙って続ける。"""
        if not self.enabled:
            return
        try:
            u = getattr(response, "usage_metadata", None)
            if u is None:
                self._note(f"usage_metadata なし: {model} ({label})")
                return
            prompt = _int(getattr(u, "prompt_token_count", 0))
            cached = _int(getattr(u, "cached_content_token_count", 0))
            candidates = _int(getattr(u, "candidates_token_count", 0))
            thoughts = _int(getattr(u, "thoughts_token_count", 0))
            tool_use = _int(getattr(u, "tool_use_prompt_token_count", 0))
            total = _int(getattr(u, "total_token_count", 0))
            entry = {
                "kind": "text",
                "model": model,
                "label": label,
                "prompt_tokens": prompt,
                "cached_tokens": cached,
                # 思考トークンは出力として課金されるので出力側に足す
                "output_tokens": candidates + thoughts,
                "thoughts_tokens": thoughts,
                "tool_use_tokens": tool_use,
                "total_tokens": total,
            }
            with self._lock:
                self.calls.append(entry)
        except Exception as exc:  # 計測の失敗で本番を止めない
            self._note(f"record 失敗: {type(exc).__name__}: {exc}")

    def record_image(self, model: str, count: int = 1, label: str = "", usd_each: float | None = None) -> None:
        """画像生成を枚数で数える。単価を明示したいときは usd_each を渡す。"""
        if not self.enabled:
            return
        try:
            with self._lock:
                self.calls.append({
                    "kind": "image",
                    "model": model,
                    "label": label,
                    "images": int(count),
                    "usd_each": usd_each,
                })
        except Exception as exc:
            self._note(f"record_image 失敗: {type(exc).__name__}: {exc}")

    def _note(self, msg: str) -> None:
        with self._lock:
            if len(self.errors) < 20:
                self.errors.append(msg)

    # ---- 集計 -------------------------------------------------------------

    def totals(self, on: _dt.date | None = None) -> dict:
        """呼び出しをモデル別に足し上げ、概算費用を付ける。"""
        on = on or _dt.date.today()
        by_model: dict[str, dict] = {}
        usd = 0.0
        unpriced: set[str] = set()
        try:
            with self._lock:
                calls = list(self.calls)
            for c in calls:
                m = c["model"]
                slot = by_model.setdefault(m, {
                    "calls": 0, "images": 0, "prompt_tokens": 0,
                    "output_tokens": 0, "cached_tokens": 0, "usd": 0.0,
                })
                slot["calls"] += 1
                if c["kind"] == "image":
                    each = c.get("usd_each")
                    if each is None:
                        each = IMAGE_PRICES.get(m)
                    slot["images"] += c["images"]
                    if each is None:
                        unpriced.add(m)
                    else:
                        cost = each * c["images"]
                        slot["usd"] += cost
                        usd += cost
                    continue
                slot["prompt_tokens"] += c["prompt_tokens"]
                slot["output_tokens"] += c["output_tokens"]
                slot["cached_tokens"] += c["cached_tokens"]
                price = _text_price(m, on)
                if price is None:
                    unpriced.add(m)
                    continue
                cost = (c["prompt_tokens"] / 1e6) * price[0] + (c["output_tokens"] / 1e6) * price[1]
                slot["usd"] += cost
                usd += cost
        except Exception as exc:
            self._note(f"totals 失敗: {type(exc).__name__}: {exc}")
        for slot in by_model.values():
            slot["usd"] = round(slot["usd"], 6)
        return {
            "calls": sum(s["calls"] for s in by_model.values()),
            "prompt_tokens": sum(s["prompt_tokens"] for s in by_model.values()),
            "output_tokens": sum(s["output_tokens"] for s in by_model.values()),
            "images": sum(s["images"] for s in by_model.values()),
            "usd": round(usd, 6),
            "jpy": round(usd * _jpy_rate()),
            "unpriced_models": sorted(unpriced),
            "by_model": by_model,
        }

    def summary_line(self) -> str:
        """cron.log や Actions のログに 1 行で残す用。"""
        try:
            t = self.totals()
            if not t["calls"]:
                return "USAGE: Gemini 呼び出しなし"
            parts = [
                f"USAGE: {t['calls']}回",
                f"入力{t['prompt_tokens']:,}tok",
                f"出力{t['output_tokens']:,}tok",
            ]
            if t["images"]:
                parts.append(f"画像{t['images']}枚")
            parts.append(f"約 ${t['usd']:.4f}（{t['jpy']}円）")
            if t["unpriced_models"]:
                parts.append(f"単価未登録: {','.join(t['unpriced_models'])}")
            if self.errors:
                parts.append(f"計測エラー{len(self.errors)}件")
            return " / ".join(parts)
        except Exception as exc:
            return f"USAGE: 集計に失敗（{type(exc).__name__}: {exc}）"

    # ---- 書き出し ---------------------------------------------------------

    def flush(self, log_dir: str | os.PathLike = "usage", run: dict | None = None) -> Path | None:
        """1 実行を JSONL へ 1 行追記する。書けなくても例外は出さない。

        Gemini を 1 回も呼ばなかった実行（収集専用モード、ガードで早期終了した朝など）は
        書かない。行が増えるだけで費用の話が読みにくくなるため。
        """
        if not self.enabled or not self.calls:
            return None
        try:
            d = Path(os.environ.get("USAGE_LOG_DIR") or log_dir)
            d.mkdir(parents=True, exist_ok=True)
            now = _dt.datetime.now(_dt.timezone.utc)
            path = d / f"usage-{now:%Y-%m}.jsonl"
            row = {
                "at": now.isoformat(timespec="seconds"),
                "started_at": self.started_at.isoformat(timespec="seconds"),
                "prices_checked": PRICES_CHECKED,
                "jpy_per_usd": _jpy_rate(),
                **self.totals(),
            }
            if run:
                row["run"] = run
            if self.errors:
                row["meter_errors"] = self.errors
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            return path
        except Exception as exc:
            self._note(f"flush 失敗: {type(exc).__name__}: {exc}")
            return None


def _jpy_rate() -> float:
    try:
        return float(os.environ.get("USAGE_JPY_PER_USD", "157"))
    except ValueError:
        return 157.0


meter = UsageMeter()


# ---- 月次の読み出し（python3 usage_meter.py usage/） ------------------------

def _report(log_dir: str) -> int:
    d = Path(log_dir)
    files = sorted(d.glob("usage-*.jsonl")) if d.is_dir() else []
    if not files:
        print(f"記録が見つかりません: {d}")
        return 1
    for path in files:
        runs = 0
        usd = 0.0
        by_model: dict[str, float] = {}
        tok_in = tok_out = images = 0
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            runs += 1
            usd += row.get("usd", 0.0)
            tok_in += row.get("prompt_tokens", 0)
            tok_out += row.get("output_tokens", 0)
            images += row.get("images", 0)
            for m, s in (row.get("by_model") or {}).items():
                by_model[m] = by_model.get(m, 0.0) + s.get("usd", 0.0)
        rate = _jpy_rate()
        print(f"\n{path.name}  実行 {runs} 回")
        print(f"  入力 {tok_in:,} tok / 出力 {tok_out:,} tok / 画像 {images} 枚")
        print(f"  概算 ${usd:.2f}（約 {round(usd * rate):,} 円 @ {rate}円/$）")
        for m, v in sorted(by_model.items(), key=lambda kv: -kv[1]):
            print(f"    {m:<28} ${v:.2f}")
    print(f"\n単価は {PRICES_CHECKED} 時点の {PRICES_SOURCE} による概算です。")
    print("正式な請求額は Google Cloud の請求画面を見てください。")
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(_report(sys.argv[1] if len(sys.argv) > 1 else "usage"))
