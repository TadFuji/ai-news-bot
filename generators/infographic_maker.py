"""X 投稿用のインフォグラフィック画像を OpenAI gpt-image-2 で生成する。

トップ10記事の中身をそのまま画像生成モデルへ渡し、1枚で全体像がつかめる
日本語のインフォグラフィックを描かせる（x-morning-brief のバナー生成と同じ手法）。
生成に失敗しても None を返すだけで、配信そのものは止めない。
"""

import base64
import io
import os
import time
from datetime import datetime

import requests

from config import JST

MODEL = "gpt-image-2"
QUALITY = "high"
# distribute_daily.py が書き出し、build_pages.py が OGP 画像として流用するファイル名
CARD_FILENAME = "x_card.png"
GEN_SIZE = "2560x1440"   # 16:9。gpt-image-2 は各辺が16の倍数である必要がある
POST_SIZE = (1600, 900)  # X 推奨サイズ（16:9 はタイムラインで切られず最大表示）
MAX_ATTEMPTS = 3
RETRY_BASE_WAIT = 3  # 秒。試行回数を掛けて待つ


def _field(article, *names):
    """記事 dict から最初に見つかった非空フィールドを返す（title_ja / title 揺れ吸収）。"""
    for n in names:
        v = article.get(n)
        if v:
            return v
    return ""


def build_prompt(articles, theme="", date_str=""):
    """トップ10記事から画像生成プロンプトを組み立てる。"""
    items = []
    for i, a in enumerate(articles, 1):
        head = _field(a, "one_liner", "title_ja", "title")
        detail = _field(a, "summary_ja", "summary")
        category = a.get("category", "")
        items.append(f"【{i}位】{head}（{category}）\n{detail}")

    return (
        f"以下は{date_str}のAIニュース トップ{len(items)}です。"
        f"この{len(items)}件が1枚で見渡せる、日本語のインフォグラフィックを作成してください。\n\n"
        f"=== 本日のテーマ ===\n{theme}\n\n"
        f"=== トップ{len(items)} ===\n" + "\n\n".join(items) + "\n=== ここまで ===\n\n"
        "デザイン要件:\n"
        "- 16:9 の横長。雑誌の特集扉のような、洗練された情報グラフィック。\n"
        "- 1位・2位・3位は大きなブロックで扱い、それぞれ見出しと、内容を象徴する具体的な絵を添える。\n"
        "- 4位以降は小さめのカードやリストとして整理して並べ、順位番号と短い見出しを添える。\n"
        "- 画像内の文字はすべて日本語・横書き。各項目の見出しは上記の文をそのまま正確に書き写す。\n"
        "- 誤字や意味をなさない文字列は絶対に入れない。読めない文字を書くくらいなら文字を減らす。\n"
        "- 英語のボタン風の装飾（Read more 等）、架空のロゴやブランド名は入れない。\n"
        "- 暗色を基調に鮮やかなアクセント色。文字の読みやすさを最優先。\n"
        "- 全体を眺めるだけで、今日のAIの動きがつかめること。"
    )


def _generate_image(prompt):
    """gpt-image-2 を呼んで PNG バイト列を返す（失敗時 None）。"""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("⚠️ OPENAI_API_KEY 未設定のため画像生成をスキップ")
        return None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            resp = requests.post(
                "https://api.openai.com/v1/images/generations",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": MODEL,
                    "prompt": prompt,
                    "size": GEN_SIZE,
                    "quality": QUALITY,
                },
                timeout=600,
            )
            resp.raise_for_status()
            b64 = (resp.json().get("data") or [{}])[0].get("b64_json")
            if b64:
                return base64.b64decode(b64)
            reason = "レスポンスに画像データが含まれていない"
        except Exception as e:
            detail = getattr(getattr(e, "response", None), "text", "") or str(e)
            reason = f"{type(e).__name__}: {detail[:300]}"

        if attempt < MAX_ATTEMPTS:
            wait = RETRY_BASE_WAIT * attempt
            print(f"⚠️ 画像生成 {attempt}/{MAX_ATTEMPTS} 失敗（{reason}）— {wait}秒後に再試行")
            time.sleep(wait)
        else:
            print(f"⚠️ 画像生成を {MAX_ATTEMPTS} 回試して失敗（{reason}）")
    return None


def _save_for_x(png_bytes, output_path):
    """X 推奨サイズへ縮小して保存する。

    1600x900 の PNG は最悪ケース（乱数ノイズ）でも約 4.1MB で、X の
    アップロード上限 5MB に収まるため、JPEG への退避は用意しない。
    """
    from PIL import Image

    img = Image.open(io.BytesIO(png_bytes)).convert("RGB").resize(POST_SIZE, Image.LANCZOS)
    img.save(output_path, format="PNG", optimize=True)
    return output_path


def create_infographic(articles, theme="", date_str=None, output_path="x_card.png"):
    """トップ10記事から X 投稿用画像を生成し、保存先パスを返す（失敗時 None）。"""
    if not articles:
        return None
    if not date_str:
        date_str = datetime.now(JST).strftime("%Y年%m月%d日")

    prompt = build_prompt(articles[:10], theme, date_str)
    png_bytes = _generate_image(prompt)
    if not png_bytes:
        return None

    path = _save_for_x(png_bytes, output_path)
    print(f"🖼️ インフォグラフィックを保存: {path}")
    return path


if __name__ == "__main__":
    # ローカル確認用: docs/ の最新レポートから1枚生成する。
    import glob
    import json

    latest = max(glob.glob("docs/2*.json"))
    data = json.load(open(latest, encoding="utf-8"))
    print(f"📄 {latest} を使用")
    create_infographic(
        data.get("articles", []),
        theme=data.get("theme", ""),
        output_path="output/x_card_test.png",
    )
