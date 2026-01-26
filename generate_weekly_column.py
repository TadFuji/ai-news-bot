#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Weekly AI Column Generator

毎週日曜日に、過去1週間のAIニュースを集約し、
コラム形式でLINEに配信するスクリプト。
"""

import os
import json
import glob
from datetime import datetime, timedelta, timezone
from google import genai
from dotenv import load_dotenv
from line_notifier import send_to_line

load_dotenv()

# JSTタイムゾーン定義
JST = timezone(timedelta(hours=9))

# docsディレクトリ（GitHub Pages用、Git管理対象）
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(PROJECT_ROOT, "docs")


def get_weekly_highlights():
    """
    過去7日間のニュースをdocs/YYYY-MM-DD.jsonから収集する。
    
    Returns:
        list: 過去1週間の全ニュース記事リスト
    """
    end_date = datetime.now(JST)
    start_date = end_date - timedelta(days=7)
    
    weekly_items = []
    
    # docs/YYYY-MM-DD.json パターンでファイルを検索
    files = glob.glob(os.path.join(DOCS_DIR, "20??-??-??.json"))
    
    for f in files:
        try:
            fname = os.path.basename(f)
            # ファイル名から日付を抽出（例: 2026-01-27.json）
            date_str = fname.replace(".json", "")
            dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=JST)
            
            if start_date <= dt <= end_date:
                with open(f, 'r', encoding='utf-8') as json_f:
                    data = json.load(json_f)
                    # docs/latest.json形式: {"updated": "...", "articles": [...]}
                    if isinstance(data, dict) and "articles" in data:
                        weekly_items.extend(data["articles"])
                    elif isinstance(data, list):
                        weekly_items.extend(data)
        except Exception as e:
            # パターンに合わないファイルはスキップ
            continue
            
    return weekly_items


def generate_column(items):
    """
    Geminiを使用してウィークリーコラムを生成する。
    
    Args:
        items: ニュース記事のリスト
        
    Returns:
        str: 生成されたコラムテキスト、または失敗時はNone
    """
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("❌ GOOGLE_API_KEY not found.")
        return None

    client = genai.Client(api_key=api_key)
    
    # URLで重複を排除
    unique_items = {}
    for item in items:
        url = item.get('url', '')
        if url and url not in unique_items:
            unique_items[url] = item
    
    # 重要度スコアでソート（存在する場合）
    sorted_items = sorted(
        unique_items.values(), 
        key=lambda x: x.get('importance_score', 0), 
        reverse=True
    )
    
    # 上位30件をコンテキストとして使用
    top_items = sorted_items[:30]
    
    item_text = ""
    for i, item in enumerate(top_items, 1):
        title = item.get('title', item.get('title_ja', 'No Title'))
        summary = item.get('summary', item.get('summary_ja', 'No Summary'))
        item_text += f"{i}. {title}: {summary}\n"

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
            model="gemini-3-flash-preview",
            contents=prompt
        )
        return response.text
    except Exception as e:
        print(f"Gemini 3 Flash エラー: {e}")
        # フォールバック
        try:
            response = client.models.generate_content(
                model="gemini-1.5-flash", 
                contents=prompt
            )
            return response.text
        except Exception as fallback_e:
            print(f"フォールバックも失敗: {fallback_e}")
            return None


def main():
    print("=== Weekly Column Generator Start ===")
    
    items = get_weekly_highlights()
    if not items:
        print("⚠️ 過去1週間のニュースが見つかりませんでした。")
        return

    print(f"📰 {len(items)}件のニュースを収集しました。")
    
    column_text = generate_column(items)
    if not column_text:
        print("❌ コラムの生成に失敗しました。")
        return
    
    # LINE用フォーマット
    header = "☕ 日曜版：AIウィークリーコラム\n\n"
    full_msg = header + column_text
    
    # ファイル保存（docs/columns/ に保存 - Git管理対象）
    timestamp = datetime.now(JST).strftime('%Y%m%d')
    columns_dir = os.path.join(DOCS_DIR, "columns")
    os.makedirs(columns_dir, exist_ok=True)
    
    # テキストファイル保存
    output_filename = f"weekly_column_{timestamp}.txt"
    output_path = os.path.join(columns_dir, output_filename)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_msg)
    print(f"💾 テキスト保存: {output_path}")

    # Markdown保存（Webサイト用）
    md_filename = f"weekly_column_{timestamp}.md"
    md_path = os.path.join(columns_dir, md_filename)
    
    md_content = f"""# AIウィークリーコラム ({datetime.now(JST).strftime('%Y/%m/%d')})

{column_text}

---
*このコラムは、過去1週間のAIニュースTop30をベースに、Gemini編集長が執筆しました。*
"""
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"💾 Markdown保存: {md_path}")

    # LINE送信
    print("📨 LINEへ送信中...")
    success = send_to_line(full_msg)
    
    if success:
        print("✅ ウィークリーコラムを送信しました。")
    else:
        print("❌ LINE送信に失敗しました。")


if __name__ == "__main__":
    main()
