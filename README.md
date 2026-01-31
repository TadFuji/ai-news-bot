# 🤖 AI News Bot (RSS & Gemini Pipeline)

主要なテックメディアや企業の公式ブログ（RSS）からAI関連ニュースを24時間ごとに自動収集し、**Gemini 2.0 Flash** で翻訳・要約して配信する完全自動化ボットです。

🔗 **公開アーカイブ**: [AI News Archive](https://tadfuji.github.io/ai-news-bot/)

## 🌟 プロジェクトの概要

このボットは、情報の洪水であるAIニュースを一箇所に集約し、**「日本語で」「短時間に」「重要なものだけ」** 把握できるように設計されています。
GitHub Actions を活用し、サーバーレスで永続的に稼働します。

### 主な機能
- 📡 **広範囲なRSS収集**: TechCrunch, Wired, OpenAI Blog, Google AI Blog など、信頼できる18以上のソースを常時監視。
- ⚖️ **厳格なAI特化選別**: 「AIトレンドアナリスト」の視点で、AIに直接関連しない一般経済・ITニュースを強力にフィルタリング。
- 🧠 **40代ペルソナへの最適化**: 日本の40代ビジネスパーソンが直面する「生存戦略」「リスク管理」「身近な利便性」に直結する情報を優先的に選定。
- 🚀 **完全自動運転**: 毎朝 7:00 (JST) に GitHub Actions が起動し、ニュースの収集からサイト更新までを無人で完了します。
- 📱 **マルチプラットフォーム配信**: 生成されたレポートは Webサイト (GitHub Pages) および LINE (Messaging API) に配信可能です。

## 🛠️ 技術スタック

- **Language**: Python 3.10+
- **AI Model**: Google Gemini 2.0 Flash
- **Infrastructure**: GitHub Actions (Cron Schedule)
- **Hosting**: GitHub Pages
- **Notification**: LINE Messaging API

## 🚀 セットアップ手順

### 1. クローン
```bash
git clone https://github.com/tadfuji/ai-news-bot.git
cd ai-news-bot
```

### 2. インストール
```bash
pip install -r requirements.txt
```

### 3. 環境設定 (.env)
ルートディレクトリに `.env` を作成してください。

```bash
GOOGLE_API_KEY="your_gemini_api_key"
LINE_CHANNEL_ACCESS_TOKEN="your_line_token" # LINE配信する場合のみ
LINE_USER_ID="your_line_user_id"            # LINE配信する場合のみ
```

## 💻 実行方法

### 手動でのニュース収集
```bash
# RSSを収集し、Geminiで翻訳・要約を実行
python main.py
```

### サイトのビルド
```bash
# 生成されたJSONデータを元にHTMLを更新
python build_pages.py
```

## 📂 ディレクトリ構造

```
ai-news-bot/
├── config.py                 # RSSフィードリストやプロンプト設定
├── main.py                   # 実行エントリーポイント
├── ai_client.py              # Gemini API クライアント
├── rss_client.py             # RSS取得ロジック
├── build_pages.py            # HTML生成 (Jinja2 Template)
├── output/                   # 生成されたMarkdown/JSON
└── docs/                     # 公開用ウェブサイト (GitHub Pages)
```

## 🛡️ ライセンス
MIT License
