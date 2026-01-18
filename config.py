import os
from datetime import timedelta, timezone

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
# JSTタイムゾーン定義
JST = timezone(timedelta(hours=9))
