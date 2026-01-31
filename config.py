import os
from datetime import timedelta, timezone

# ===========================
# 設定
# ===========================

# RSSフィードのリスト（AI関連のテックメディア）
RSS_FEEDS = [
    # --- 米国 主要メディア ---
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
        "name": "MIT Technology Review",
        "url": "https://www.technologyreview.com/feed/",
        "region": "米国"
    },
    {
        "name": "Ars Technica AI",
        "url": "https://feeds.arstechnica.com/arstechnica/technology-lab",
        "region": "米国"
    },
    {
        "name": "ZDNet AI",
        "url": "https://www.zdnet.com/topic/artificial-intelligence/rss.xml",
        "region": "米国"
    },
    {
        "name": "The Information",
        "url": "https://www.theinformation.com/feed",
        "region": "米国"
    },
    # --- AI企業公式ブログ ---
    {
        "name": "OpenAI Blog",
        "url": "https://openai.com/blog/rss.xml",
        "region": "米国"
    },
    {
        "name": "Anthropic News",
        "url": "https://www.anthropic.com/news/rss.xml",
        "region": "米国"
    },
    {
        "name": "Google AI Blog",
        "url": "https://blog.google/technology/ai/rss/",
        "region": "米国"
    },
    {
        "name": "DeepMind Blog",
        "url": "https://deepmind.google/blog/rss.xml",
        "region": "英国"
    },
    {
        "name": "Microsoft AI Blog",
        "url": "https://blogs.microsoft.com/ai/feed/",
        "region": "米国"
    },
    # --- 日本 ---
    {
        "name": "NHK 科学・技術",
        "url": "https://www.nhk.or.jp/rss/news/cat6.xml",
        "region": "日本"
    },
    {
        "name": "ITmedia AI+",
        "url": "https://rss.itmedia.co.jp/rss/2.0/aiplus.xml",
        "region": "日本"
    },
    # --- ヨーロッパ ---
    {
        "name": "BBC Technology",
        "url": "https://feeds.bbci.co.uk/news/technology/rss.xml",
        "region": "英国"
    },
    {
        "name": "Reuters Technology",
        "url": "https://www.reutersagency.com/feed/?taxonomy=best-topics&post_type=best&best-topics=tech",
        "region": "英国"
    },
]

# AI関連キーワード（フィルタリング用）- 拡充版
AI_KEYWORDS = [
    # --- 一般用語 ---
    "AI", "artificial intelligence", "machine learning", "deep learning",
    "neural network", "transformer", "generative AI", "生成AI",
    "人工知能", "機械学習", "大規模言語モデル", "ディープラーニング",
    # --- 主要モデル・サービス ---
    "LLM", "GPT", "GPT-4", "GPT-5", "ChatGPT", "Gemini", "Claude",
    "Copilot", "Midjourney", "Stable Diffusion", "DALL-E", "Sora",
    "Llama", "Mistral", "Grok", "Perplexity", "Suno", "Udio", "Runway", "Pika",
    # --- 主要企業・プラットフォーム ---
    "OpenAI", "Anthropic", "DeepMind", "xAI", "Cohere", "Hugging Face",
    "NVIDIA", "Microsoft", "Google", "Meta", "Apple AI", "Apple Intelligence",
    "Nano Banana", "Antigravity", "Google AI Studio",
    # --- 技術用語 ---
    "AGI", "superintelligence", "AI regulation", "AI ethics", "AI safety",
    "multimodal", "vision model", "language model", "foundation model",
    "fine-tuning", "RAG", "retrieval", "embedding", "prompt engineering",
    "AI agent", "autonomous agent", "reasoning", "chain of thought",
    # --- 英語追加（厳選版） ---
    "breakthrough", "inference", "funding", "deployment", "adoption",
    "regulation update", "open source",
    # --- 日本語追加 ---
    "チャットボット", "自動生成", "AI規制", "AI法",
    "推論", "学習手法", "マルチモーダル", "資金調達", "API",
    "規制", "ガイドライン", "著作権", "雇用",
]

# ルートディレクトリ
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# 出力ファイルパス
NEWS_BOT_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")

# JSTタイムゾーン定義
JST = timezone(timedelta(hours=9))
