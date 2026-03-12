# ai-news-bot — 変更履歴

## 2026-03-12 (Session: ae965d1f)

### 作業者: Antigravity AI

### 1. リポジトリのパブリック化
- `gh repo edit TadFuji/ai-news-bot --visibility public`
- セキュリティレビュー完了（.env非追跡、Git履歴クリーン、APIキーはSecrets管理）

### 2. GitHub Pages 404 修正
- Visibility変更時にPages設定が自動リセット → `gh api repos/.../pages -X POST` で再有効化

### 3. 英文ニュース混入問題の修正 (commit `de71ea6`)
- **根本原因**: `GOOGLE_API_KEY` が失効（約5日間発覚せず）
- **影響**: Gemini API 全失敗 → フォールバック発動 → RSS の英文記事がそのまま配信
- **修正**:
  - `curate_morning_brief.py`: リトライ機構（最大2回/指数バックオフ）、フォールバック時に `title_ja`/`summary_ja` を転写
  - `ai_client.py`: フォールバック時に翻訳済みフィールドを転写
- **APIキー更新**: `.env` + GitHub Secrets
- **復旧確認**: 手動ワークフロー実行 → 「2次キュレーション完了、10件保証達成」

### 4. 改善1: ヘルスチェック通知 (commit `d5ee0e4`)
- `curate_morning_brief.py`: フォールバック発動時にLINE障害通知を自動送信
- `sys.exit(1)` で GitHub Actions を赤ステータスにし、サイレント障害を防止
- 配信・サイト更新は続行した上で最後にexit(1)する設計

### 5. 改善2: `global.html` ハードコード修正 (commit `d5ee0e4`)
- `docs/global.html`: デフォルトJSONを `global_2026-03-02.json` → `global_latest.json` に変更
- `build_pages.py`: `global_latest.json` を自動生成するロジック追加

### 6. 改善3: DB重複コード統合 (commit `d5ee0e4`)
- **新規**: `db_utils.py` — 共通関数を抽出
  - `get_db_connection()`, `init_db()`, `save_articles()`, `save_collection_run()`
  - `normalize_category()`, `normalize_region()`, `parse_published_at()`
- `save_to_db.py`: 338行 → 107行
- `save_global_news.py`: 305行 → 108行

### 未実施の改善案（提案済み）
4. RSS ソースの言語タグ追加
5. Gemini 構造化出力 (`response_mime_type="application/json"`)
6. GitHub Pages UI 改善（`one_liner`/`why_important` 表示、`column.html`/`archive.html` 作成）
7. LINE Flex Message カルーセルで 10 件配信
8. `app.py` リファクタリング（`generators/` へ分離）
9. トレンド分析ダッシュボード（D3.js / Chart.js）
10. メール配信チャネル追加（Resend / SendGrid）
11. RSS 死活監視
12. ユニットテスト追加
