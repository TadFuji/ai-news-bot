#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Weekly AI Column Generator
"""

import os
import json
import glob
from datetime import datetime, timedelta, timezone
from google import genai
from dotenv import load_dotenv
from config import JST, NEWS_BOT_OUTPUT_DIR
from line_notifier import send_to_line

load_dotenv()

def get_weekly_highlights():
    # 7 days ago (Sunday to Sunday, roughly)
    end_date = datetime.now(JST)
    start_date = end_date - timedelta(days=7)
    
    # Pattern: ai_news_YYYYMMDD_HHMM.json
    files = glob.glob(os.path.join(NEWS_BOT_OUTPUT_DIR, "ai_news_*.json"))
    weekly_items = []
    
    print(f"DEBUG: Search range {start_date} to {end_date}")
    
    for f in files:
        try:
            fname = os.path.basename(f)
            # Extract timestamp part
            ts_str = fname.replace("ai_news_", "").replace(".json", "")
            # Verify format
            dt = datetime.strptime(ts_str, "%Y%m%d_%H%M").replace(tzinfo=JST)
            
            if start_date <= dt <= end_date:
                with open(f, 'r', encoding='utf-8') as json_f:
                    data = json.load(json_f)
                    weekly_items.extend(data)
        except Exception as e:
            # Skip files that don't match pattern or are corrupt
            continue
            
    return weekly_items

def generate_column(items):
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("❌ GOOGLE_API_KEY not found.")
        return None

    client = genai.Client(api_key=api_key)
    
    # Deduplicate by URL
    unique_items = {i.get('url', str(idx)): i for idx, i in enumerate(items)}.values()
    
    # Sort by importance_score descending
    sorted_items = sorted(unique_items, key=lambda x: x.get('importance_score', 0), reverse=True)
    
    # Take top 30 for context
    top_items = sorted_items[:30]
    
    item_text = ""
    for i, item in enumerate(top_items, 1):
        title = item.get('title_ja', item.get('title', 'No Title'))
        summary = item.get('summary_ja', item.get('summary', 'No Summary'))
        item_text += f"{i}. {title}: {summary}\n"

    print(f"DEBUG: Generating column from {len(top_items)} items...")

    prompt = f"""
    あなたは、日本のビジネスパーソンに大人気のAIテック系コラムニスト「アント」編集長です。
    この1週間のAIニュースTop30をベースに、日曜日の朝9時に配信する「AIウィークリーコラム」を執筆してください。

    **ターゲット読者:**
    - AIの進化に興味はあるが、日々のニュースを追う時間がない40代〜50代のビジネスリーダー
    - 「結局、何が重要で、これからどうなるの？」を知りたい層

    **コラムの構成（必須）:**
    
    1. **【今週の総括】** (3行以内でズバリ)
       - 今週のAI界隈を一言で表すと？
       
    2. **【編集長が選ぶトップ3】** (最もインパクトのあった3つ)
       - 記事タイトル
       - 💡 **「ここがヤバい」ポイント** (なぜ重要なのか、未来どうなるかの独自の読み)
       
    3. **【未来予報】** (コラムのメイン)
       - 今週の動きから予測できる「来週以降の展開」や「半年後の世界」
       - 読者へのアクション提案（「今のうちに〇〇しておきましょう」など）
       - 少し辛口だったり、ユーモアを交えた「人間味」のある文章で

    **執筆トーン:**
    - "です・ます"調だが、堅苦しくないエッセイ風
    - 専門用語は噛み砕くか、例え話を使う
    - 読者が読んで「なるほど！」「やる気が出た」と思えるポジティブさと洞察
    
    **入力データ（今週のトップニュース）:**
    {item_text}
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash", # Use standard stable model if preview is risky, sticking to what user likely has access to or widely avail
            contents=prompt
        )
        return response.text
    except Exception as e:
        # Fallback to older model if new one fails or SDK diffs
        print(f"Generation Error: {e}")
        try:
            response = client.models.generate_content(
                model="gemini-1.5-flash", 
                contents=prompt
            )
            return response.text
        except:
            return None

def main():
    print("=== Weekly Column Generator Start ===")
    
    items = get_weekly_highlights()
    if not items:
        print("⚠️ No news items found for the past week.")
        return

    column_text = generate_column(items)
    if not column_text:
        print("❌ Failed to generate column.")
        return
    
    # Formatting for LINE
    header = "☕ 日曜版：AIウィークリーコラム\n\n"
    full_msg = header + column_text
    
    # Save to file for record
    output_filename = f"weekly_column_{datetime.now(JST).strftime('%Y%m%d')}.txt"
    output_path = os.path.join(NEWS_BOT_OUTPUT_DIR, "columns", output_filename)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_msg)
    print(f"💾 Saved to {output_path}")

    # Send to LINE
    print("📨 Sending to LINE...")
    success = send_to_line(full_msg)
    
    if success:
        print("✅ Daily Column sent successfully.")
    else:
        print("❌ Failed to send LINE message.")

if __name__ == "__main__":
    main()
