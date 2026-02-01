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
import argparse
import json
from datetime import datetime
from config import JST, NEWS_BOT_OUTPUT_DIR
from rss_client import collect_from_rss_feeds
from filters import filter_by_time, filter_by_ai_keywords, remove_duplicates
from ai_client import process_with_gemini
from output_manager import output_markdown, save_output, save_json
from line_notifier import send_news_to_line

HISTORY_FILE = os.path.join(NEWS_BOT_OUTPUT_DIR, "check_history.json")

def load_history() -> set:
    """既知のURL履歴を読み込む"""
    if not os.path.exists(HISTORY_FILE):
        return set()
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data.get("urls", []))
    except Exception:
        return set()

def save_history(urls: set):
    """URL履歴を保存する"""
    os.makedirs(NEWS_BOT_OUTPUT_DIR, exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump({"urls": list(urls), "updated_at": datetime.now(JST).isoformat()}, f, indent=2)

def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="AI News Bot")
    parser.add_argument("--mode", choices=["daily", "sentinel"], default="daily", help="実行モード")
    parser.add_argument("--no-line", action="store_true", help="LINE通知をスキップする")
    args = parser.parse_args()
    
    print("=" * 50)
    print(f"🤖 AI News Bot - Mode: {args.mode.upper()}")
    print("=" * 50)
    print()
    
    # 1. RSSフィードから記事を収集
    articles = collect_from_rss_feeds()
    
    if not articles:
        print("❌ 記事が取得できませんでした")
        return
    
    # 2. フィルタリング (Common)
    # Sentinelモードなら「前回チェック以降」＝実質的には過去1時間〜数時間だが、
    # 厳密には「履歴にないもの」かつ「過去24時間以内」で良い。
    articles_time_filtered = filter_by_time(articles)
    
    # AI関連キーワードフィルタ
    articles_keyword_filtered = filter_by_ai_keywords(articles_time_filtered)
    
    # 重複除去 (URLベース)
    candidates = remove_duplicates(articles_keyword_filtered)
    
    # --- 履歴チェック (Deduplication) ---
    history = load_history()
    new_candidates = [a for a in candidates if a["url"] not in history]
    
    print(f"🔍 新着チェック: 候補 {len(candidates)}件 -> 未読 {len(new_candidates)}件")
    
    if not new_candidates:
        print("✅ 新しいAIニュースはありませんでした。")
        return

    # --- モード別処理 ---
    
    final_candidates = []
    
    if args.mode == "sentinel":
        # Sentinelモード: 新着があれば即処理対象
        # ただし、ゴミ記事を減らすため、キーワードにヒットしたものだけ（既にfilter_by_ai_keywords済み）
        final_candidates = new_candidates
        
        # 出力ファイル名 (分刻み)
        output_file = os.path.join(NEWS_BOT_OUTPUT_DIR, f"breaking_{datetime.now(JST).strftime('%Y%m%d_%H%M')}.md")
        
    else:
        # Dailyモード: 従来通り10件選定
        final_candidates = new_candidates
        
        # 10件未満なら補填 (Dailyのみ)
        if len(final_candidates) < 10:
            print(f"⚠️ 候補が少ないため ({len(final_candidates)}件)、履歴外の全記事から補填します")
            all_unique = remove_duplicates(articles_time_filtered)
            for article in all_unique:
                if article["url"] not in history and article["url"] not in [a["url"] for a in final_candidates]:
                    final_candidates.append(article)
                    if len(final_candidates) >= 10:
                        break
        
        # 出力ファイル名 (日次)
        output_file = os.path.join(NEWS_BOT_OUTPUT_DIR, f"ai_news_{datetime.now(JST).strftime('%Y%m%d_%H%M')}.md")

    if not final_candidates:
        print("⚠️ 処理対象となる記事がありませんでした")
        return

    # 3. Gemini APIで翻訳・要約・スコアリング
    # Sentinelモードなら最大5件くらいで十分（大量に来ても困る）
    limit = 5 if args.mode == "sentinel" else 10
    processed = process_with_gemini(final_candidates, max_articles=limit)
    
    if not processed:
        print("⚠️ AI処理の結果、有効な記事が残りませんでした")
        return

    # 4. 出力 & 保存
    md = output_markdown(processed)
    save_output(md, output_file)
    
    json_file = output_file.replace(".md", ".json")
    save_json(processed, json_file)
    
    print()
    print("=" * 50)
    print("📰 出力結果")
    print("=" * 50)
    print(md)
    
    # 5. LINE 送信
    # Sentinelモードなら「速報」として送るロジックが必要だが、
    # 現状の send_news_to_line はタイトルが固定されている。
    # 一旦そのまま送るが、受け手（自分）が速報とわかるようにしたい。
    # ※ line_notifier.py をいじらずに済ませるため、send_news_to_line はそのまま使う。
    #    (DailyもSentinelも同じフォーマットで届くが、Sentinelは件数が少ないので区別つく)
    
    # 5. LINE 送信
    if not args.no_line:
        send_news_to_line(processed)
    else:
        print("⏭️ --no-line が指定されたため、LINE送信をスキップします。")
    
    # --- DOMINATOR UPGRADE: Full Automation Sequence ---
    # 完全に自動化するために、PDF生成とX投稿もここで行う。
    
    try:
        print("🤖 Starting Dominator Sequence...")
        
        # A. PDF生成 (Latest Update Strategy)
        from generators.pdf_maker import create_pdf_report
        import shutil
        
        # Generate dated file
        pdf_filename = f"report_{datetime.now(JST).strftime('%Y%m%d')}.pdf"
        pdf_path = create_pdf_report(processed, os.path.join(NEWS_BOT_OUTPUT_DIR, pdf_filename))
        
        if pdf_path:
            # Overwrite "Latest" for fixed link
            public_dir = os.path.join(os.path.dirname(NEWS_BOT_OUTPUT_DIR), "public_reports")
            if not os.path.exists(public_dir):
                os.makedirs(public_dir)
            latest_path = os.path.join(public_dir, "Antigravity_Latest_Report.pdf")
            shutil.copy2(pdf_path, latest_path)
            print(f"✅ PDF Updated: {latest_path}")
            
            # B. X (Twitter) Auto-Post (Only in Sentinel Mode)
            # Daily mode might be manual check, but Sentinel is "Hands-free"
            if args.mode == "sentinel":
                print("🐦 Executing Auto-Post to X...")
                from drivers.x_poster import post_to_x, hijack_top_trend
                
                top_a = processed[0]
                promo_text = f"""
【無料配布】
今日のAIニュースまとめ ({datetime.now(JST).strftime('%m/%d')} 17:00更新)

TOPIC:
・{top_a['title_ja']}
...他。

正直、これさえ読めば今の流れは全部わかります。
リメイク版PDF、配布開始しました。

↓
配布は【LINE】で自動化しました。
リプ欄のリンクから「1秒」でDLできます。
(DM待たなくてOKです)

#AI #Gemini #無料配布
""".strip()
                promo_reply = f"【受取リンク】\nこちらのLINEで「レポート」と送ると、このPDFが自動で届きます！\n(友だち追加して待っててね)\n👇\nhttps://lin.ee/gTGnitS"
                
                # 1. Post to Self (Timeline)
                post_to_x(promo_text, reply_text=promo_reply)
                print("✅ Timeline Post Complete.")
                
                
                # 2. Newsjacking (Paparazzi Strategy)
                # Search for 'AI' or 'Gemini' and reply to top tweet with INFOGRAPHIC (High Value)
                print("🕵️ Initiating Newsjacking Protocol (Project Paparazzi)...")
                
                # Generate Infographic from top article
                from generators.infographic_maker import create_infographic
                infographic_path = os.path.join(NEWS_BOT_OUTPUT_DIR, f"infographic_{datetime.now(JST).strftime('%Y%m%d')}.png")
                
                # Create visual summary card
                create_infographic(
                    top_a['title_ja'], 
                    top_a['summary_ja'][:80] + "...", 
                    output_path=infographic_path
                )
                
                # Polite, value-add reply
                hijack_text = f"話題のニュースですね、要点を1枚の画像にまとめました。\n(詳細なレポートはプロフのリンクにあります) #AI"
                
                if os.path.exists(infographic_path):
                    hijack_top_trend("AI", hijack_text, image_path=infographic_path)
                    print("✅ Paparazzi Mission Complete (Image Reply Sent).")
                else:
                    print("⚠️ Infographic generation failed. Skipping hijack.")
                
    except Exception as e:
        print(f"❌ Dominator Sequence Failed: {e}")
        # Don't stop the script, just log error
        pass
    
    # 6. 履歴更新
    # Sentinelモードの趣旨（速報）に合わせ、今回「新着」として認識した記事はすべて「既読」とする。
    # これにより、選ばれなかった記事が次回の実行で再度候補になることを防ぐ。
    seen_urls = {a["url"] for a in new_candidates}
    save_history(history | seen_urls)
    print(f"📚 履歴を更新しました (+{len(seen_urls)}件 / 全{len(history | seen_urls)}件)")


if __name__ == "__main__":
    main()
