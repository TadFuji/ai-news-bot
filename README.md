# 🤖 AI ニュース収集・翻訳ボット

24時間以内のAI関連ニュースを自動収集し、日本語で要約・配信するボットです。

## 機能

- 📡 **ニュース収集**: TechCrunch、Wired、NHK 等の RSS フィードから AI 関連記事を取得
- 🌐 **日本語翻訳**: Gemini API で英語記事を自然な日本語に翻訳
- ⭐ **重要度評価**: AI が記事の重要性を判断し、TOP10 を選定
- ⏰ **自動実行**: GitHub Actions で毎日 JST 7:00 に自動実行

## セットアップ

### 1. リポジトリをフォーク/クローン

```bash
git clone https://github.com/YOUR_USERNAME/ai-news-bot.git
cd ai-news-bot
```

### 2. Gemini API キーを取得

1. [Google AI Studio](https://aistudio.google.com/) にアクセス
2. API キーを作成

### 3. GitHub Secrets を設定

リポジトリの Settings > Secrets and variables > Actions で以下を追加:

| Secret 名        | 値              |
| ---------------- | --------------- |
| `GOOGLE_API_KEY` | Gemini API キー |

### 4. Actions を有効化

リポジトリの Actions タブから、ワークフローを有効化してください。

## ローカル実行

```bash
# 依存関係をインストール
pip install -r requirements.txt

# 環境変数を設定
export GOOGLE_API_KEY="your-api-key"

# 実行
python ai_news_collector.py
```

## 出力例

```markdown
# AI関連ニュース TOP10

**更新日時**: 2026年01月16日 07:00 (JST)

## 1. OpenAI、次世代モデル「GPT-5」の開発計画を発表

OpenAI は次世代大規模言語モデル「GPT-5」の開発を進めていることを明らかにした。
従来モデルと比較して推論能力が大幅に向上し、マルチモーダル処理も強化される見込み。

- **出典**: TechCrunch AI
- **URL**: https://techcrunch.com/...
```

## スケジュール

- **自動実行**: 毎日 JST 7:00（UTC 22:00）
- **手動実行**: Actions タブから `Run workflow` をクリック

## ファイル構成

```
ai-news-bot/
├── .github/
│   └── workflows/
│       └── ai_news.yml      # GitHub Actions ワークフロー
├── output/                   # 出力ファイル保存先
├── ai_news_collector.py      # メインスクリプト
├── requirements.txt          # Python 依存関係
└── README.md                 # このファイル
```

## ライセンス

MIT License
