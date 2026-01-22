#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LINE Messaging API を使った通知モジュール

AI ニュース TOP10 を LINE に自動送信する機能を提供します。
v3.6: シェアボタン（Flex Message）の追加
"""

import os
import urllib.parse
from datetime import datetime
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    PushMessageRequest,
    TextMessage,
    FlexMessage,
    FlexBubble,
    FlexBox,
    FlexText,
    FlexButton,
    URIAction
)

def create_share_message() -> FlexMessage:
    """
    「友達にシェア」するためのFlex Messageを作成する
    
    Returns:
        FlexMessage: シェアボタン付きのメッセージ
    """
    # シェアするテキストの作成
    share_text = (
        "🤖 今日のAIニュースTOP10\n"
        "最新のトレンドを3分でチェック！\n\n"
        "👇 ニュースを読む\n"
        "https://tadfuji.github.io/ai-news-bot/"
    )
    encoded_text = urllib.parse.quote(share_text)
    share_url = f"https://line.me/R/msg/text/?{encoded_text}"
    
    # Flex Message (Bubble) の構築
    bubble = FlexBubble(
        size="kilo",
        body=FlexBox(
            layout="vertical",
            padding_all="md",
            contents=[
                FlexText(
                    text="この記事を友達にシェア",
                    weight="bold",
                    size="sm",
                    color="#1DB446",  # LINE Green
                    align="center"
                ),
                FlexText(
                    text="毎朝のAIニュースを、チームや友人に教えよう！",
                    size="xs",
                    color="#aaaaaa",
                    wrap=True,
                    align="center",
                    margin="md"
                )
            ]
        ),
        footer=FlexBox(
            layout="vertical",
            contents=[
                FlexButton(
                    style="primary",
                    color="#1DB446",
                    action=URIAction(
                        label="📢 シェアする",
                        uri=share_url
                    )
                )
            ]
        )
    )
    
    return FlexMessage(
        alt_text="📢 このニュースをシェアする",
        contents=bubble
    )


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
        "─────────",
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


def send_to_line(message_text: str) -> bool:
    """
    LINE Messaging API でメッセージを送信する
    
    Args:
        message_text: 送信するニュース本文（テキスト）
    
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
            
            # メッセージリストの作成 (テキスト + シェアボタン)
            messages = [
                TextMessage(text=message_text),
                create_share_message()
            ]
            
            push_request = PushMessageRequest(
                to=user_id,
                messages=messages
            )
            
            messaging_api.push_message(push_request)
        
        print("✅ LINE 送信成功！（シェアボタン付き）")
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
