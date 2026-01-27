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
    
    # 1週間分のニュースすべてをコンテキストとして使用
    all_items = list(sorted_items)
    
    item_text = ""
    for i, item in enumerate(all_items, 1):
        title = item.get('title', item.get('title_ja', 'No Title'))
        summary = item.get('summary', item.get('summary_ja', 'No Summary'))
        item_text += f"{i}. {title}: {summary}\n"

    print(f"📊 {len(all_items)}件のニュースをコラム生成に使用します。")

    prompt = f"""
あなたは、日本のビジネスパーソンに大人気のAIテック系コラムニスト「アント」編集長です。
日曜日の朝に配信する「AIウィークリーコラム」を執筆してください。

## あなたのキャラクター
- 50代のベテランテック編集長。業界30年の経験から独自の視点を持つ
- 辛口だが愛情深い。読者を「あなた」と呼び、友人に話すように書く
- 時々ダジャレや軽いジョークを入れる。堅苦しさゼロ
- 「私はこう思うんですよ」「正直に言うとね」など個人的意見を惜しまない

## 執筆スタイル（超重要）
**これは「ニュースまとめ」ではなく「エッセイ・読み物」です。**

以下のような流れで、1週間を振り返る「物語」として書いてください：

1. **冒頭の挨拶**（2〜3行）
   - 「今週もお疲れ様でした」的な親しみのある入り
   - 今週の印象を一言で（例：「いやー、今週は激動でしたね」）

2. **週の流れに沿った読み物**（メインパート）
   - 「週の前半、まず目を引いたのは〇〇のニュースでした」
   - 「これを見て私が思ったのは...」と個人的コメント
   - 「で、水曜あたりに飛び込んできたのがコレ」と次のニュースへ自然につなぐ
   - 「正直、最初は『またか』と思ったんですが、よく見ると...」のような本音
   - 記事を**引用**しながら、あなたの**解釈や予測**を織り交ぜる
   - 「週の後半には、さらに驚きのニュースが」と盛り上げる

3. **締めくくり**（3〜4行）
   - 今週の学びを一言でまとめる
   - 読者への軽いアドバイス（「来週はこれに注目ですよ」など）
   - 「また来週！」的なフレンドリーな締め

## 絶対にやってはいけないこと
- ❌ 箇条書きだけの羅列
- ❌ 「第1位」「第2位」のようなランキング形式
- ❌ 無機質な要約
- ❌ ですます調でも堅苦しい文体

## お手本フレーズ
- 「月曜日、最初に目についたのは〇〇のニュースでした。これ、正直びっくりしましたよね？」
- 「で、これだけでも十分なのに、水曜日にはさらに〇〇が発表されまして...」
- 「私ね、この手のニュースを見るたびに思うんですけど、」
- 「いやいや、ちょっと待ってくださいよ。これ、つまり〇〇ってことですよね？」
- 「来週以降、この流れがどうなるか。私の予想を言わせてもらうと...」

## 入力データ（今週のニュース {len(all_items)}件）
{item_text}

上記のニュースから5〜7件程度を選び、週の流れに沿って「読み物」として書いてください。
文字数は800〜1200文字程度。読んで楽しい、友人からの手紙のようなコラムをお願いします。
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
*このコラムは、1週間分のAIニュース（毎日のTop10）をベースに、Gemini編集長が執筆しました。*
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
