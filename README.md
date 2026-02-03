# 🤖 AI News Bot: Global Intelligence to Local Action

[![Daily RSS + Gemini Summary](https://github.com/TadFuji/ai-news-bot/actions/workflows/daily_rss_gemini.yml/badge.svg)](https://github.com/TadFuji/ai-news-bot/actions/workflows/daily_rss_gemini.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Gemini 3 Flash Preview](https://img.shields.io/badge/AI-Gemini%203%20Flash%20Preview-orange.svg)](https://deepmind.google/technologies/gemini/)

世界中の膨大なAIニュースから、**日本の40代ビジネスリーダー**にとって真に価値のある情報のみを抽出し、日本語で要約・配信する完全自動化パイプラインです。

🔗 **公開ポータル**: [AI News Bot Web Archive](https://tadfuji.github.io/ai-news-bot/)

---

## 🎯 プロジェクトの使命（Editorial Policy）

「情報の海で溺れない、賢明な判断を下すための羅針盤」

多くのAIニュースは、専門的すぎる学術論文や、一般人には無関係な海外の資金調達ニュース、あるいは単なるノイズに溢れています。本プロジェクトは、**「AIトレンドアナリスト」**という明確なペルソナ（AIを活用して意思決定を行うビジネスパーソンの分身）をAIに定義し、以下の3つの基準で情報を厳選します：

1.  **生存戦略（Survival Strategy）**: 「この技術は、私たちの働き方をどう変えるか？」
2.  **リスク管理（Risk Management）**: 「教育、著作権、セキュリティの観点で何に注意すべきか？」
3.  **身近な利便性（Practical Utilities）**: 「LINEやExcelなど、日常的なツールがどう進化したか？」

---

## 🏗️ システムアーキテクチャ (System Architecture)

GitHub Actions を中核とした、モダンなサーバーレス・アーキテクチャを採用しています。

```mermaid
graph TD
    subgraph "External Sources"
        A[RSS Feeds (Global Tech/AI Corp Blogs)]
    end

    subgraph "GitHub Actions (CI/CD Pipeline)"
        B[Discovery: RSS Client]
        C[Pre-Filtering: Keyword Scoring]
        D[Editorial Analysis: Gemini 3 Flash Preview]
        E[Generation: Markdown/JSON/HTML]
    end

    subgraph "Delivery"
        F[Web: GitHub Pages]
        G[SNS: X/Twitter Thread]
        H[Nofication: LINE Messaging API]
    end

    A --> B
    B --> C
    C -- "Selected Top 30" --> D
    D -- "Curated Top 10" --> E
    E --> F
    E --> G
    E --> H
```

---

## 🚀 技術的な特徴 (Technical Excellence)

プロのエンジニアが信頼を置ける、堅牢で拡張性の高い設計を目指しています。

-   **Modular Design**: 収集(RSS)、解析(AI)、通知(LINE/X)、ビルド(HTML)が完全に疎結合化されています。
-   **Multi-Stage Filtering**: 入口でのキーワードベースの感度調整と、Geminiによる文脈理解に基づいた最終選別の二段構え。
-   **State of the Art AI**: 高レベルな論理推論と爆速の処理速度を両立した `Gemini 3 Flash Preview` を採用。
-   **Zero-Overhead Deployment**: 完全にGitHub Actions内で完結し、データベースやサーバーの維持費をかけずに永続的に稼働。
-   **Terminology Bridging**: 専門用語を避けず、日本のビジネスパーソンに伝わる言葉で平易に解説するロジック。

---

## 📂 ディレクトリ構造 (Project Structure)

```text
ai-news-bot/
├── .github/workflows/    # CI/CD自動化定義
├── config.py             # 全体の設定・RSSソース・キーワード定義
├── main.py               # 統合実行エントリーポイント
├── collect_rss_gemini.py # ニュース収集/解析のコアロジック
├── ai_client.py          # Gemini API との高度なプロンプト連携
├── rss_client.py         # 複数のRSSソースを並列(?)取得
├── build_pages.py        # Jinja2形式のテンプレートを用いた静的サイト生成
├── line_notifier.py      # LINE Messaging API連携（Flex Message等）
├── distribute_daily.py   # SNS/メッセージ配信の司令塔
├── docs/                 # GitHub Pages 公開用ディレクトリ
└── output/               # 中間生成物（JSON/Markdown履歴）
```

---

## 🛠️ セットアップと開発 (Development)

### ローカル実行
```bash
# 依存関係のインストール
pip install -r requirements.txt

# 環境変数の設定 (cp .env.example .env)
# GOOGLE_API_KEY, LINE_CREDENTIALS 等を設定
```

### システムの心臓部（Prompts）
`ai_client.py` 内のプロンプトは、AIを単なる翻訳機ではなく「専門のキュレーター」として機能させるための高度なコンテキスト（Role, Task, Constraints, Personas）を内包しています。

---

## 🤝 コントリビューション
バグ報告、新しいRSSソースの推薦、プロンプトの改善提案をお待ちしております！詳細は `CONTRIBUTING.md` をご覧ください。

## 🛡️ License
MIT License -詳細は `LICENSE` を参照。

---
Produced by Antigravity AI Project.
