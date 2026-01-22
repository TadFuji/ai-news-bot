#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LINE Messaging API を使った通知モジュール

AI ニュース TOP10 を LINE に自動送信する機能を提供します。
"""

import os
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    PushMessageRequest,
    TextMessage,
)
from linebot.v3.exceptions import InvalidSignatureError


def format_news_for_line(articles: list[dict], max_articles: int = 5) -> str:
    """
    ニュース記事を LINE 用テキストに整形する
    
    Args:
        articles: 処理済み記事リスト
        max_articles: LINE に送信する記事数（デフォルト: 5件）
    
    Returns:
        LINE 送信用のテキスト
    """
    if not articles:
        return "📰 本日のAIニュースはありませんでした。"
    
    # ヘッダー
    lines = [
        "🤖 AI ニュース TOP10",
        "━━━━━━━━━━━━━━━━",
        ""
    ]
    
    # 各記事（LINE では読みやすさ優先で上位5件のみ）
    for i, article in enumerate(articles[:max_articles], 1):
        title = article.get("title_ja", article.get("title", "タイトルなし"))
        summary = article.get("summary_ja", article.get("summary", ""))
        url = article.get("url", "")
        
        # 要約を短く（LINE では100文字程度が読みやすい）
        if len(summary) > 100:
            summary = summary[:97] + "..."
        
        lines.append(f"【{i}】{title}")
        lines.append(f"{summary}")
        lines.append(f"🔗 {url}")
        lines.append("")
    
    # フッター
    if len(articles) > max_articles:
        lines.append(f"📌 他 {len(articles) - max_articles} 件の記事は Web で確認")
        lines.append("https://tadfuji.github.io/ai-news-bot/")
    
    return "\n".join(lines)


def send_to_line(message: str) -> bool:
    """
    LINE Messaging API でメッセージを送信する
    
    Args:
        message: 送信するテキストメッセージ
    
    Returns:
        送信成功なら True
    """
    channel_access_token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
    user_id = os.environ.get("LINE_USER_ID")
    
    if not channel_access_token or not user_id:
        print("⚠️ LINE 認証情報が設定されていません (LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID)")
        print("   → LINE 送信をスキップします")
        return False
    
    try:
        configuration = Configuration(access_token=channel_access_token)
        
        with ApiClient(configuration) as api_client:
            messaging_api = MessagingApi(api_client)
            
            push_request = PushMessageRequest(
                to=user_id,
                messages=[TextMessage(text=message)]
            )
            
            messaging_api.push_message(push_request)
        
        print("✅ LINE 送信成功！")
        return True
        
    except Exception as e:
        print(f"❌ LINE 送信エラー: {e}")
        return False


def send_news_to_line(articles: list[dict]) -> bool:
    """
    AI ニュースを LINE に送信するメイン関数
    
    Args:
        articles: 処理済み記事リスト
    
    Returns:
        送信成功なら True
    """
    print()
    print("📱 LINE への送信を開始...")
    
    message = format_news_for_line(articles)
    return send_to_line(message)
