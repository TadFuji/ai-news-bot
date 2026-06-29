#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LINE Messaging API を使った通知モジュール

AI ニュース TOP10 を LINE に自動送信する機能を提供します。
v3.6: シェアボタン（Flex Message）の追加
"""

import os
import urllib.parse
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    PushMessageRequest,
    TextMessage,
    FlexMessage,
    FlexCarousel,
    FlexBubble,
    FlexBox,
    FlexText,
    FlexButton,
    URIAction
)

def create_share_message(top_article: dict | None = None) -> FlexMessage:
    """
    「友達にシェア」するためのFlex Messageを作成する

    top_article が渡された場合は、その記事内容をシェアテキストに含める
    （友達追加URL固定からの脱却）。

    Returns:
        FlexMessage: シェアボタン付きのメッセージ
    """
    line_add_friend_url = "https://lin.ee/gTGnitS"

    if top_article:
        one_liner = top_article.get("one_liner") or top_article.get("title_ja", "")
        title = top_article.get("title_ja", top_article.get("title", ""))
        url = top_article.get("url", "")
        share_text = (
            f"🤖【AIニュース】{one_liner}\n\n"
            f"{title}\n"
            f"詳細→{url}\n\n"
            "毎朝のAIニュースはこちら👇（無料）\n"
            f"{line_add_friend_url}"
        )
    else:
        share_text = (
            "🤖 毎朝、世界のAIニュースがLINEに届く！\n\n"
            "自分も愛用している無料のニュースボットです。\n"
            "忙しい朝でも3分でトレンド把握できます。\n\n"
            "👇 こっから友達追加できるよ（無料）\n"
            f"{line_add_friend_url}"
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


def create_news_carousel(articles: list[dict], max_cards: int = 3) -> FlexMessage:
    """ニュース上位を横スクロールの Flex Carousel カードにする。

    各カードに one_liner / タイトル / 要約 / action_item と「元記事を読む」ボタンを配置。
    LINE のバブルは既定が白背景のため、文字色は濃色で可読性を確保する。
    """
    bubbles = []
    for i, a in enumerate(articles[:max_cards], 1):
        title = a.get("title_ja", a.get("title", "タイトルなし"))
        summary = a.get("summary_ja", a.get("summary", ""))
        one_liner = a.get("one_liner", "")
        action_item = a.get("action_item", "")
        category = a.get("category", "")
        url = a.get("url", "").strip()
        if not url.lower().startswith(("http://", "https://")):
            url = "https://tadfuji.github.io/ai-news-bot/"

        body_contents = [
            FlexText(text=f"{i}. {category}".strip(" ."), size="xs",
                     color="#06c755", weight="bold"),
        ]
        if one_liner:
            body_contents.append(FlexText(
                text=f"💡 {one_liner}", weight="bold", size="md",
                color="#111111", wrap=True, margin="sm"))
        body_contents.append(FlexText(
            text=title, size="sm", color="#333333", wrap=True, margin="sm"))
        if summary:
            body_contents.append(FlexText(
                text=summary[:120], size="xs", color="#888888", wrap=True, margin="sm"))
        if action_item:
            body_contents.append(FlexText(
                text=f"👉 {action_item}", size="xs", color="#06c755", wrap=True, margin="md"))

        bubbles.append(FlexBubble(
            size="kilo",
            body=FlexBox(layout="vertical", padding_all="md", contents=body_contents),
            footer=FlexBox(layout="vertical", contents=[
                FlexButton(
                    style="primary", color="#1DB446", height="sm",
                    action=URIAction(label="元記事を読む", uri=url),
                )
            ]),
        ))

    lead = ""
    if articles:
        lead = articles[0].get("one_liner") or articles[0].get("title_ja", "")
    return FlexMessage(
        alt_text=f"本日のAI TOP{len(bubbles)}: {lead}"[:380],
        contents=FlexCarousel(contents=bubbles),
    )


def format_news_for_line(articles: list[dict], max_articles: int = 3) -> str:
    """
    ニュース記事を LINE 用テキストに整形する
    
    Args:
        articles: 処理済み記事リスト
        max_articles: LINE に送信する記事数（デフォルト: 3件）
    
    Returns:
        LINE 送信用のテキスト
    """
    if not articles:
        return "📰 本日のAIニュースはありませんでした。"
    
    # ヘッダー
    lines = [
        "🤖 AI ニュース TOP 3",
        "─────────",
        ""
    ]
    
    # 各記事（LINE では文字数制限を考慮し上位3件のみ）
    for i, article in enumerate(articles[:max_articles], 1):
        title = article.get("title_ja", article.get("title", "タイトルなし"))
        summary = article.get("summary_ja", article.get("summary", ""))
        one_liner = article.get("one_liner", "")
        why_important = article.get("why_important", "")
        url = article.get("url", "")
        
        if one_liner:
            lines.append(f"【{i}】💡 {one_liner}")
            lines.append(f"{title}")
        else:
            lines.append(f"【{i}】{title}")
        lines.append(f"{summary}")
        if why_important:
            lines.append(f"📌 {why_important}")
        lines.append(f"🔗 {url}")
        lines.append("")
    
    # フッター
    if len(articles) > max_articles:
        lines.append(f"💡 残り {len(articles) - max_articles} 件の重要ニュースはウェブで！")
        lines.append("👇 最新アーカイブはこちら")
        lines.append("https://tadfuji.github.io/ai-news-bot/")
    
    return "\n".join(lines)


def _push_messages(messages) -> bool:
    """LINE へメッセージ群を送信する単一の送出口。

    将来の一般公開（push → broadcast / multicast）はこの関数の変更だけで
    済むよう、宛先の決定をここに集約する（broadcast-ready）。
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
            push_request = PushMessageRequest(to=user_id, messages=messages)
            messaging_api.push_message(push_request)
        print("✅ LINE 送信成功！")
        return True
    except Exception as e:
        print(f"❌ LINE 送信エラー: {e}")
        return False


def send_to_line(message_text: str) -> bool:
    """テキスト通知（障害アラート等）を1通送信する。"""
    return _push_messages([TextMessage(text=message_text)])


def send_news_to_line(articles: list[dict]) -> bool:
    """
    AI ニュースを LINE に送信するメイン関数（テキスト形式）

    Args:
        articles: 処理済み記事リスト

    Returns:
        送信成功なら True
    """
    print()
    print("📱 LINE への送信を開始...")

    if not articles:
        return send_to_line("📰 本日のAIニュースはありませんでした。")

    message_text = format_news_for_line(articles)
    return send_to_line(message_text)
