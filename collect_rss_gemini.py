import os
import re
import json
import time
import datetime
from rss_client import collect_from_rss_feeds
from ai_client import process_with_gemini
from article_extractor import enrich_with_full_text
from config import NEWS_BOT_OUTPUT_DIR, AI_KEYWORDS, JST
from dotenv import load_dotenv

load_dotenv()

# キーワードを正規表現パターンに事前コンパイル（大文字小文字無視）
_KEYWORD_PATTERN = re.compile(
    "|".join(re.escape(kw) for kw in AI_KEYWORDS),
    re.IGNORECASE,
)


def filter_by_time(articles, hours=24):
    """Filter articles published within the last N hours."""
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=hours)
    filtered = [a for a in articles if a.get('published') and a['published'] >= cutoff]
    return filtered


def score_articles(articles):
    """キーワードマッチングで関連度スコアを算出する（正規表現で高速化）"""
    scored = []
    for a in articles:
        text = (a.get('title', '') + " " + a.get('summary', ''))
        matches = _KEYWORD_PATTERN.findall(text)
        a['_relevance'] = len(matches)
        scored.append(a)

    # AI関連度 > 0 を優先、次に公開日時の降順
    scored.sort(
        key=lambda x: (
            x['_relevance'] > 0,
            x.get('published', datetime.datetime.min.replace(tzinfo=datetime.timezone.utc))
            or datetime.datetime.min.replace(tzinfo=datetime.timezone.utc),
        ),
        reverse=True,
    )
    return scored


# 配信は10件だが、同じ出来事の記事は日本語化した後の束ねで減るため、余裕を持って渡す
# （2026-09-20/21/25 に 10 件のうち 1〜2 件が束ねられ、配信が 9・8 件になった）。
JEV_POOL = 15


def select_with_jev(articles, n=JEV_POOL):
    """Jev の上位 n 件（配信済みを除く）。使えない場合は None。"""
    from curate_morning_brief import get_delivered_urls
    import jev_selector

    delivered = get_delivered_urls(days=3)
    fresh = [a for a in articles if a.get("url") and a["url"] not in delivered]
    try:
        return jev_selector.select_articles(fresh, n=n)
    except Exception as e:  # never let the new selector stop the morning delivery
        print(f"   ⚠️ Jev 選定で予期しないエラー（従来方式に戻します）: {type(e).__name__}: {e}")
        return None


def keep_all_jev_picks(processed, picks):
    """Gemini 1次が落とした Jev 選定記事を未翻訳のまま戻す（2次で日本語化される）。"""
    have = {a.get("url") for a in processed}
    missing = []
    for a in picks:
        if a.get("url") in have:
            continue
        ac = {k: v for k, v in a.items() if k != "full_text"}
        if isinstance(ac.get("published"), datetime.datetime):
            ac["published"] = ac["published"].isoformat()
        missing.append(ac)
    if missing:
        print(f"   📌 Gemini 1次が {len(missing)} 件を落としたため、Jev 選定の記事で補います")
    return sorted(processed + missing, key=lambda a: a.get("jev_rank", len(picks) + 1))


def main():
    start = time.time()
    print("=== Hybrid News Collection Start ===")

    print("1. Fetching RSS Feeds...")
    articles = collect_from_rss_feeds()

    # Simple Time Filter (24h)
    print("2. Filtering by Time (24h)...")
    articles = filter_by_time(articles)
    print(f"-> {len(articles)} articles remaining.")

    if not articles:
        print("No recent articles found.")
        return

    # 3. Jev が「日本の一般読者が興味深いと思うか」で全件を採点し、上位 JEV_POOL 件を決める。
    #    Jev が使えないとき（鍵なし・通信失敗）は従来のキーワード方式に戻す。
    print("3. Selecting articles with Jev (reader interest)...")
    input_articles = select_with_jev(articles)
    jev_mode = bool(input_articles)
    if jev_mode:
        print(f"-> Jev selected {len(input_articles)} articles; Gemini writes the Japanese text.")
    else:
        print("3. Prioritizing AI-related articles (keyword fallback)...")
        scored_articles = score_articles(articles)
        # Take top 30 relevant/newest for Gemini
        input_articles = scored_articles[:30]
        print(f"-> Selected {len(input_articles)} articles for Gemini analysis (Priority: AI Relevance).")

    # 3.5. 上位記事の本文を取得して判断材料を厚くする（失敗時は RSS 要約で代替）
    print("3.5. Fetching full article text for top items...")
    enrich_with_full_text(input_articles, top_n=15)

    print("4. Processing with Gemini (AI Trend Analyst Mode)...")
    if jev_mode:
        # Jev の日は選んだ全件を日本語化する（未翻訳のまま 2次へ渡すと束ねが効かない）
        processed = process_with_gemini(input_articles, max_articles=len(input_articles))
    else:
        processed = process_with_gemini(input_articles)
    if jev_mode:
        processed = keep_all_jev_picks(processed, input_articles)

    # Save as JSON
    timestamp = datetime.datetime.now(JST).strftime("%Y%m%d_%H%M")
    filename = f"candidates_{timestamp}.json"
    filepath = os.path.join(NEWS_BOT_OUTPUT_DIR, filename)

    os.makedirs(NEWS_BOT_OUTPUT_DIR, exist_ok=True)

    output_data = {"articles": processed}
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"✅ Saved Top 10 to: {filepath}")

    # Also save as Markdown for visibility
    md_filename = f"candidates_{timestamp}.md"
    md_filepath = os.path.join(NEWS_BOT_OUTPUT_DIR, md_filename)

    now_jst = datetime.datetime.now(JST)
    updated_str = now_jst.strftime("%Y年%m月%d日 %H:%M")

    with open(md_filepath, 'w', encoding='utf-8') as f:
        f.write("# AI News Top 10\n\n")
        f.write(f"**更新日時**: {updated_str} (JST)\n\n")
        f.write("Generated by Gemini 3.8 Flash (via RSS)\n\n")
        for i, item in enumerate(processed, 1):
            title = item.get('title_ja', item.get('title', 'No Title'))
            summary = item.get('summary_ja', item.get('summary', ''))
            category = item.get('category', '未分類')
            source = item.get('source', 'Unknown')
            url = item.get('url', '')
            f.write(f"## {i}. {title}\n\n")
            f.write(f"**カテゴリ**: {category}\n\n")
            f.write(f"{summary}\n\n")
            f.write(f"- **出典**: {source}\n")
            f.write(f"- **URL**: {url}\n\n")

    elapsed = time.time() - start
    print(f"✅ Saved Markdown to: {md_filepath}")
    print(f"⏱️  Stage 1 合計: {elapsed:.1f}秒")


if __name__ == "__main__":
    main()
