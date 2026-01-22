#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI ニュース収集・翻訳ボット (Modularized)

24時間以内のAI関連ニュースをRSSフィードから収集し、
Gemini APIで日本語に翻訳・要約して出力します。

使用方法:
    export GOOGLE_API_KEY="your-api-key"
    python main.py
"""

import os
from datetime import datetime
from config import JST, OUTPUT_DIR
from rss_client import collect_from_rss_feeds
from filters import filter_by_time, filter_by_ai_keywords, remove_duplicates
from ai_client import process_with_gemini
from output_manager import output_markdown, save_output, save_json
from line_notifier import send_news_to_line

def main():
    """メイン処理"""
    print("=" * 50)
    print("🤖 AI ニュース収集・翻訳ボット (Modularized)")
    print("=" * 50)
    print()
    
    # OUTPUT_FILE の定義 (実行時間を名前に含めるためここで定義)
    output_file = os.path.join(OUTPUT_DIR, f"ai_news_{datetime.now(JST).strftime('%Y%m%d_%H%M')}.md")
    
    # 1. RSSフィードから記事を収集
    articles = collect_from_rss_feeds()
    
    if not articles:
        print("❌ 記事が取得できませんでした")
        return
    
    # 2. JST 実行時点から過去48時間の記事をフィルタ
    articles_time_filtered = filter_by_time(articles)
    
    # 3. AI関連キーワードでフィルタ（優先）
    articles_keyword_filtered = filter_by_ai_keywords(articles_time_filtered)
    
    # 4. 重複を除去
    unique_keyword_articles = remove_duplicates(articles_keyword_filtered)
    
    # もし10件未満なら、キーワードにヒットしなかった記事も追加（ソースがAI専門カテゴリなので許容）
    final_candidates = unique_keyword_articles
    if len(final_candidates) < 10:
        print(f"⚠️ キーワード記事が少ないため ({len(final_candidates)}件)、全記事から補填します")
        all_unique = remove_duplicates(articles_time_filtered)
        # 既にある記事を除外して追加
        existing_urls = {a["url"] for a in final_candidates}
        for article in all_unique:
            if article["url"] not in existing_urls:
                final_candidates.append(article)
                if len(final_candidates) >= 10:
                    break
    
    if not final_candidates:
        print("⚠️ 過去48時間以内の記事が見つかりませんでした")
        # 空の出力を生成
        md = output_markdown([])
        save_output(md, output_file)
        print(md)
        return
    
    # 5. Gemini APIで翻訳・要約・スコアリング
    processed = process_with_gemini(final_candidates, max_articles=10)
    
    # 6. Markdown出力
    md = output_markdown(processed)
    
    # 7. ファイルに保存
    save_output(md, output_file)
    
    # 7.5 JSONファイルも保存 (Marketing Engine用)
    json_file = output_file.replace(".md", ".json")
    save_json(processed, json_file)
    
    # 8. 標準出力にも表示（GitHub Actions のログ用）
    print()
    print("=" * 50)
    print("📰 出力結果")
    print("=" * 50)
    print()
    print(md)
    
    # 9. LINE に送信
    send_news_to_line(processed)


if __name__ == "__main__":
    main()
