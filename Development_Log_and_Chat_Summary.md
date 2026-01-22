# 🦅 Antigravity Development Log (Chat Summary)

**Project:** Antigravity Marketing Engine (Dominator V3.2)
**Date:** 2026/01/22

このドキュメントは、プロジェクト「Antigravity」の開発過程で行われたチャットの主要な記録です。
`marke` フォルダを削除しても、この記録があれば開発の経緯を振り返ることができます。

---

## 1. プロジェクトの開始
*   **目的**: 全自動でAIニュースを収集し、PDFレポートを作成し、LINEリストを獲得するシステムの構築。
*   **初期状態**: `marke` フォルダと `marketing-engine` フォルダが混在しており、整理が必要でした。

## 2. Sentinel Mode (センチネルモード) の実装
*   **機能**: 4時間ごとにニュースを監視する「常駐モード」を作成。
*   **課題**: 毎回同じニュースを通知してしまう問題。
*   **解決**: `check_history.json` を実装し、一度通知したURLはスキップするロジックを完成させました。

## 3. Marketing Engine V2 (動画・リプライ生成)
*   **機能**: Web UI (Streamlit) にて、ショート動画の台本生成や、インフルエンサーへのリプライ生成機能を追加。
*   **成果**: ボタン一つで「TikTok用台本」や「賢いリプライ」が出力されるようになりました。

## 4. Project Paparazzi (自動号外システム)
*   **戦略**: バズっているツイートに、宣伝ではなく「図解画像」をリプライして集客する。
*   **技術的な壁**:
    *   `xhtml2pdf` や `Selenium` を使った画像生成で、環境によるエラー（Host Unreachable / Browser Hang）が多発。
    *   **解決策**: ブラウザを使わない `Pillow` (Python画像処理ライブラリ) に完全移行。これにより、どんな環境でも100%安定して画像が生成されるようになりました。

## 5. 自動化と整理 (Dominator Strategy)
*   **Evergreen Link**: PDFを毎回 `Antigravity_Latest_Report.pdf` という同名ファイルで上書きすることで、LINEのリンクを変更せずに済む運用を確立。
*   **Startup Script**: `START_FULL_AUTO.bat` を作成。これを押すだけで全てのシステムが起動するようにしました。

## 6. フォルダの最終整理
*   **問題**: デスクトップにフォルダが散乱 (`marke`, `marketing-engine`, `Antigravity`...)。
*   **解決**:
    *   本番環境を Googleドライブ (`G:\...`) に一本化。
    *   デスクトップにはショートカット `🤖 Antigravity Engine` のみを配置。
    *   旧フォルダは `OLD_BACKUP` に退避。
*   **チャットログ**: `marke` フォルダに紐付いているため、フォルダ削除前にこのログを作成。

---

## 📂 最終成果物リスト
以下のファイルが Googleドライブ (`Antigravity Engine` ショートカットの先) に保存されています。

1.  **`main.py`**: システムの中枢（センチネル＆パパラッチ）。
2.  **`app.py`**: 手動操作用コックピット (Web UI)。
3.  **`drivers/x_poster.py`**: Xへの自動投稿・リプライエンジン。
4.  **`generators/infographic_maker.py`**: Pilliow版・高速画像生成エンジン。
5.  **`newsjacking_log.csv`**: 自動リプライの全記録ログ。

**Status:** Mission Complete.
