#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI ニュース収集・翻訳ボット

24時間以内のAI関連ニュースをRSSフィードから収集し、
Gemini APIで日本語に翻訳・要約して出力します。

使用方法:
    export GOOGLE_API_KEY="your-api-key"
    python ai_news_collector.py
"""

import os
import json
from datetime import datetime, timedelta, timezone
import feedparser
from dateutil import parser as date_parser
import google.generativeai as genai

# ===========================
# 設定
# ===========================

# RSSフィードのリスト（AI関連のテックメディア）
RSS_FEEDS = [
    {
        "name": "TechCrunch AI",
        "url": "https://techcrunch.com/category/artificial-intelligence/feed/",
        "region": "米国"
    },
    {
        "name": "The Verge AI",
        "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
        "region": "米国"
    },
    {
        "name": "Wired AI",
        "url": "https://www.wired.com/feed/tag/ai/latest/rss",
        "region": "米国"
    },
    {
        "name": "VentureBeat AI",
        "url": "https://venturebeat.com/category/ai/feed/",
        "region": "米国"
    },
    {
        "name": "NHK 科学・技術",
        "url": "https://www.nhk.or.jp/rss/news/cat6.xml",
        "region": "日本"
    },
    {
        "name": "MIT Technology Review",
        "url": "https://www.technologyreview.com/feed/",
        "region": "米国"
    },
    {
        "name": "Ars Technica AI",
        "url": "https://feeds.arstechnica.com/arstechnica/technology-lab",
        "region": "米国"
    },
]

# AI関連キーワード（フィルタリング用）
AI_KEYWORDS = [
    "AI", "artificial intelligence", "machine learning", "deep learning",
    "LLM", "GPT", "ChatGPT", "Gemini", "Claude", "OpenAI", "Anthropic",
    "neural network", "transformer", "generative AI", "生成AI",
    "人工知能", "機械学習", "大規模言語モデル", "ディープラーニング",
    "Copilot", "Midjourney", "Stable Diffusion", "DALL-E",
    "AGI", "superintelligence", "AI regulation", "AI ethics",
]

# 出力ファイルパス
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, f"ai_news_{datetime.now().strftime('%Y%m%d_%H%M')}.md")

# ===========================
# ニュース収集機能
# ===========================

def collect_from_rss_feeds() -> list[dict]:
    """
    複数のRSSフィードからニュース記事を収集する
    
    Returns:
        記事情報のリスト（タイトル、URL、公開日時、ソース名）
    """
    articles = []
    
    for feed_info in RSS_FEEDS:
        print(f"📡 {feed_info['name']} から記事を取得中...")
        try:
            feed = feedparser.parse(feed_info["url"])
            
            for entry in feed.entries:
                # 公開日時を取得（published または updated）
                pub_date = None
                if hasattr(entry, "published"):
                    pub_date = entry.published
                elif hasattr(entry, "updated"):
                    pub_date = entry.updated
                
                # 日時をパース
                parsed_date = None
                if pub_date:
                    try:
                        parsed_date = date_parser.parse(pub_date)
                        # タイムゾーンがない場合はUTCとして扱う
                        if parsed_date.tzinfo is None:
                            parsed_date = parsed_date.replace(tzinfo=timezone.utc)
                    except Exception:
                        pass
                
                # 概要を取得
                summary = ""
                if hasattr(entry, "summary"):
                    summary = entry.summary
                elif hasattr(entry, "description"):
                    summary = entry.description
                
                articles.append({
                    "title": entry.title if hasattr(entry, "title") else "No Title",
                    "url": entry.link if hasattr(entry, "link") else "",
                    "published": parsed_date,
                    "summary": summary[:500] if summary else "",  # 最大500文字
                    "source": feed_info["name"],
                    "region": feed_info["region"],
                })
                
        except Exception as e:
            print(f"  ⚠️ エラー: {e}")
            continue
    
    print(f"✅ 合計 {len(articles)} 件の記事を取得しました")
    return articles


def filter_by_time(articles: list[dict]) -> list[dict]:
    """
    前日7時〜当日7時（JST）に公開された記事のみを抽出する
    
    Args:
        articles: 記事リスト
    
    Returns:
        フィルタリングされた記事リスト
    """
    # JST (UTC+9) で 7:00 を基準にする
    jst = timezone(timedelta(hours=9))
    now_jst = datetime.now(jst)
    
    # 当日の7:00 JST
    today_7am_jst = now_jst.replace(hour=7, minute=0, second=0, microsecond=0)
    
    # もし現在時刻が7時より前なら、基準は昨日の7時〜今日の7時
    # もし現在時刻が7時以降なら、基準は今日の7時〜明日の7時
    if now_jst.hour < 7:
        end_time = today_7am_jst
        start_time = end_time - timedelta(days=1)
    else:
        start_time = today_7am_jst
        end_time = start_time + timedelta(days=1)
    
    # UTC に変換して比較
    start_time_utc = start_time.astimezone(timezone.utc)
    end_time_utc = end_time.astimezone(timezone.utc)
    
    filtered = []
    for article in articles:
        if article["published"]:
            pub_time = article["published"]
            if start_time_utc <= pub_time < end_time_utc:
                filtered.append(article)
    
    start_str = start_time.strftime('%m/%d %H:%M')
    end_str = end_time.strftime('%m/%d %H:%M')
    print(f"📅 {start_str} 〜 {end_str} (JST) の記事: {len(filtered)} 件")
    return filtered


def filter_by_ai_keywords(articles: list[dict]) -> list[dict]:
    """
    AI関連のキーワードを含む記事のみを抽出する
    
    Args:
        articles: 記事リスト
    
    Returns:
        AI関連の記事リスト
    """
    filtered = []
    for article in articles:
        text = f"{article['title']} {article['summary']}".lower()
        for keyword in AI_KEYWORDS:
            if keyword.lower() in text:
                filtered.append(article)
                break
    
    print(f"🤖 AI関連の記事: {len(filtered)} 件")
    return filtered


def remove_duplicates(articles: list[dict]) -> list[dict]:
    """
    重複する記事を削除する（タイトルの類似度でチェック）
    
    Args:
        articles: 記事リスト
    
    Returns:
        重複を除去した記事リスト
    """
    seen_titles = set()
    unique = []
    
    for article in articles:
        # タイトルを正規化（小文字化、空白除去）
        normalized = article["title"].lower().strip()
        
        # 既に同じタイトルがあればスキップ
        if normalized not in seen_titles:
            seen_titles.add(normalized)
            unique.append(article)
    
    print(f"📋 重複除去後: {len(unique)} 件")
    return unique


# ===========================
# Gemini API による処理
# ===========================

def process_with_gemini(articles: list[dict], max_articles: int = 10) -> list[dict]:
    """
    Gemini APIを使用して記事を翻訳・要約し、重要度スコアを付与する
    
    Args:
        articles: 記事リスト
        max_articles: 処理する最大記事数
    
    Returns:
        処理済み記事リスト（日本語タイトル、日本語要約、スコア付き）
    """
    # APIキーを取得
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("❌ GOOGLE_API_KEY 環境変数が設定されていません")
        return articles[:max_articles]
    
    # Geminiを設定
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")
    
    # 記事情報をまとめてプロンプトに含める
    articles_text = ""
    for i, article in enumerate(articles[:30]):  # 最大30件を処理対象
        articles_text += f"""
---
記事{i+1}:
タイトル: {article['title']}
ソース: {article['source']} ({article['region']})
概要: {article['summary'][:300]}
URL: {article['url']}
"""
    
    prompt = f"""あなたはAI・テクノロジー分野の専門家です。
以下のニュース記事リストから、最も重要で影響力のある10件を選び、日本語で出力してください。

選定基準:
- グローバルな影響度（政策、ビジネス、技術革新）
- AI分野における重要性
- 日本のビジネスパーソンへの関連性
- 重複する内容は1つだけ選ぶ

出力形式（JSON配列）:
[
  {{
    "index": 元の記事番号,
    "title_ja": "日本語タイトル",
    "summary_ja": "2〜3文の日本語要約。ビジネス専門家向けに分かりやすく",
    "importance_score": 1-10の重要度スコア,
    "reason": "選定理由（1文）"
  }},
  ...
]

---
記事リスト:
{articles_text}
---

重要: 必ず10件選び、JSON配列のみを出力してください。マークダウンのコードブロックは不要です。
"""
    
    print("🧠 Gemini API で処理中...")
    
    try:
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # JSONをパース（コードブロックがある場合は除去）
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1])
        
        results = json.loads(response_text)
        
        # 結果を元の記事情報とマージ
        processed = []
        for result in results:
            idx = result.get("index", 1) - 1
            if 0 <= idx < len(articles):
                article = articles[idx].copy()
                article["title_ja"] = result.get("title_ja", article["title"])
                article["summary_ja"] = result.get("summary_ja", "要約なし")
                article["importance_score"] = result.get("importance_score", 5)
                article["reason"] = result.get("reason", "")
                processed.append(article)
        
        # スコアで降順ソート
        processed.sort(key=lambda x: x.get("importance_score", 0), reverse=True)
        
        print(f"✅ Gemini 処理完了: {len(processed)} 件")
        return processed[:max_articles]
        
    except Exception as e:
        print(f"❌ Gemini API エラー: {e}")
        # フォールバック: 元の記事をそのまま返す
        return articles[:max_articles]


# ===========================
# 出力機能
# ===========================

def output_markdown(articles: list[dict]) -> str:
    """
    記事リストをMarkdown形式で出力する
    
    Args:
        articles: 処理済み記事リスト
    
    Returns:
        Markdown形式の文字列
    """
    now = datetime.now(timezone(timedelta(hours=9)))  # JST
    
    md = f"""# AI関連ニュース TOP10

**更新日時**: {now.strftime('%Y年%m月%d日 %H:%M')} (JST)

過去24時間以内に公開された、最も重要なAI関連ニュースを厳選してお届けします。

---

"""
    
    for i, article in enumerate(articles, 1):
        title = article.get("title_ja", article["title"])
        summary = article.get("summary_ja", article.get("summary", "要約なし"))
        url = article["url"]
        source = article["source"]
        
        md += f"""## {i}. {title}

{summary}

- **出典**: {source}
- **URL**: {url}

---

"""
    
    if not articles:
        md += "該当するAI関連ニュースは過去24時間以内に見つかりませんでした。\n"
    
    return md


def save_output(content: str, filepath: str) -> None:
    """
    コンテンツをファイルに保存する
    
    Args:
        content: 保存する内容
        filepath: 保存先ファイルパス
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    
    print(f"💾 保存完了: {filepath}")


# ===========================
# メイン処理
# ===========================

def main():
    """メイン処理"""
    print("=" * 50)
    print("🤖 AI ニュース収集・翻訳ボット")
    print("=" * 50)
    print()
    
    # 1. RSSフィードから記事を収集
    articles = collect_from_rss_feeds()
    
    if not articles:
        print("❌ 記事が取得できませんでした")
        return
    
    # 2. JST 7時基準で24時間以内の記事をフィルタ
    articles = filter_by_time(articles)
    
    # 3. AI関連キーワードでフィルタ
    articles = filter_by_ai_keywords(articles)
    
    # 4. 重複を除去
    articles = remove_duplicates(articles)
    
    if not articles:
        print("⚠️ 過去24時間以内のAI関連ニュースが見つかりませんでした")
        # 空の出力を生成
        md = output_markdown([])
        save_output(md, OUTPUT_FILE)
        print(md)
        return
    
    # 5. Gemini APIで翻訳・要約・スコアリング
    processed = process_with_gemini(articles, max_articles=10)
    
    # 6. Markdown出力
    md = output_markdown(processed)
    
    # 7. ファイルに保存
    save_output(md, OUTPUT_FILE)
    
    # 8. 標準出力にも表示（GitHub Actions のログ用）
    print()
    print("=" * 50)
    print("📰 出力結果")
    print("=" * 50)
    print()
    print(md)


if __name__ == "__main__":
    main()
