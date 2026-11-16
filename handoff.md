# handoff.md — AIニュースの引き継ぎ

最終確認: 2026-11-16。作業開始・終了時の更新ルールは [AGENTS.md](AGENTS.md)。2026-10-10の朝刊遅延と適用済み再発低減策（collection_runner など）は [automation/RECOVERY_HANDOFF.md](automation/RECOVERY_HANDOFF.md) を先に読む。現在の主起動は **OpenAI dot（どっちゃん）の定時タスク、07:07 JST**、実処理はGitHub Actions。変更担当者は [AGENTS.md](AGENTS.md) に従い毎回引き継ぎを更新する。構成は [README.md](README.md)、過去の変更は [HISTORY.md](HISTORY.md)。

## Flex 推論（50%割引・Standard 自動退避付き）と思考レベル MEDIUM の導入（2026-11-16）

- **変更点**:
  - `config.py`: `GEMINI_THINKING_LEVEL`（既定 `"MEDIUM"`）、`GEMINI_SERVICE_TIER`（既定 `"flex"`）、`GEMINI_FLEX_TIMEOUT_MS`（既定 `180000`）を追加。
  - `ai_client.py`, `curate_morning_brief.py`, `generate_weekly_column.py`: 共通ヘルパー（`should_use_flex_attempt`, `build_gemini_text_config`, `is_fatal_key_error`）により、初回試行は Flex 推論＋`thinking_level="MEDIUM"` で呼び出し、遅延・503 等で失敗した場合は即座に通常モード（Standard）へフォールバックする（API キーエラー時は従来通り即中止）。週刊コラムも Flex 失敗時の Standard リトライを1回追加。
  - `usage_meter.py`: `service_tier="flex"` 呼び出しを 50% 割引（`FLEX_DISCOUNT=0.5`）で計算するよう更新（`PRICES_CHECKED = "2026-11-16"`）。
  - `tests/test_flex_inference.py`, `CLAUDE.md`: オフラインテスト 5 件を追加し、仕様を反映。
- **検証結果**: `pytest tests/ -q`、`python -m unittest discover -s tests`、`ruff check . --select E9,F63,F7,F82`、`git diff --check` がすべて exit 0。
- **元に戻す方法**: 該当コミットを `git revert <commit>` して `origin/main` へ push（環境変数 `GEMINI_SERVICE_TIER=standard` でも無効化可）。

## 読めない RSS フィードの修正・整理（2026-11-15）

- **確認日時**: 2026-11-15 09:00 JST
- **変更点**:
  - `config.py` の `RSS_FEEDS` を 66 件から 58 件へ更新（読めないフィード 14 件の修正・整理）。
    - URL 更新（4件）:
      - `Anthropic News`: 公式 RSS 不在のためコミュニティ保守ミラー（`https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_news.xml`）を使用
      - `Stability AI Blog`: URL を `https://stability.ai/news-updates?format=rss` へ更新
      - `Decrypt AI`: URL を `https://decrypt.co/feed?category=ai` へ更新
      - `Import AI`: Substack が GitHub Actions IP を 403 拒否するため著者の公式 WordPress サイト（`https://jack-clark.net/feed/`）へ切替
    - 公式代替へ切替（2件）:
      - `Microsoft AI Blog` → `name`: `Microsoft Blog`, `url`: `https://blogs.microsoft.com/feed/`（旧 AI ブログが 410 終了、移転先 Source AI トピックフィードは 10/21 で更新停止のため公式メインブログへ切替）
      - `Meta AI Blog` → `name`: `Meta Engineering`, `url`: `https://engineering.fb.com/feed/`（`ai.meta.com` に公式 RSS 無しのため Meta 公式技術ブログへ切替）
    - 削除（8件）: 公式 RSS 廃止・非公開化・ボット遮断・非AI記事占有のため除外（`VentureBeat AI`, `Forbes AI`, `Ledge.ai`, `AI Shift Blog`, `Reuters Technology`, `The Next Web AI`〔AI カテゴリ別 RSS 廃止に加え、全体フィード切替は非 AI 記事による上位 30 件枠占有が確認されたため〕, `ERNIE Blog (Baidu)`, `Midjourney Updates`）
  - ドキュメント内のフィード件数（66 → 58）を更新: `CLAUDE.md`, `README.md`, `README_EN.md`, `docs/ARCHITECTURE.md`
  - テスト追加: `tests/test_feed_health.py` に `config.RSS_FEEDS` の整合性テスト（非空・URL形式・重複なし・件数整合）を追加
- **根拠ファイル**: `health/feeds-2026-11-11.json` 〜 `health/feeds-2026-11-15.json`、`config.py`
- **検証結果**:
  - 実機 RSS 取得検証: 変更・切替した 6 フィードすべて `status == "ok"` かつ `len(articles) > 0` を確認（Anthropic News: 288件, Microsoft Blog: 10件, Meta Engineering: 9件, Stability AI Blog: 20件, Decrypt AI: 40件, Import AI: 10件）。全 58 フィード中 56 件が `ok`、2 件が一時的なエントリなし（`empty`）でエラー/遮断なしを確認
  - 自動テスト: `pytest tests/`（129 passed）、`unittest discover -s tests`（7 passed）、`ruff check`、`git diff --check` がすべて exit 0
- **未完了・次の手順**: 2026-11-16 朝の GitHub Actions で `health/feeds-2026-11-16.json` の全 58 件、特に GitHub Actions 上の `Import AI` / `Anthropic News` を含む読み取り結果を確認すること
- **元に戻す方法**: 該当コミットを `git revert` して `origin/main` へ push

## 既定モデルを gemini-4-hydrogen へ変更（2026-11-13）

- **変更点**: 藤川さんの指示により、`config.py` の `GEMINI_MODEL` を `"gemini-3.8-flash"` から `"gemini-4-hydrogen"` へ変更。あわせて `ai_client.py`（実行ログ表示）、`collect_rss_gemini.py`（Markdown フッター）、`usage_meter.py`（`PRICES` に `"gemini-4-hydrogen": (1.50, 7.50)` を追加、`PRICES_CHECKED = "2026-11-13"`）、`CLAUDE.md`、`README.md`、`README_EN.md`、`docs/ARCHITECTURE.md`、`.github/ISSUE_TEMPLATE/bug_report.md` を更新。
- **検証結果**: `pytest tests/`（128 passed）、`unittest discover -s tests`（7 passed）、`ruff check`、`git diff --check` がすべて exit 0。
- **未完了・次の手順**: 明朝（2026-11-14）07:07 JST の GitHub Actions 本番実行で `gemini-4-hydrogen` によるキュレーション・配信結果と `usage/` 記録を確認する。
- **元に戻す方法**: 該当コミットを `git revert` して `origin/main` へ push する。

## フィードの読み取り結果の記録（2026-11-10）

- `rss_client.py` が各フィードを `ok`（読めた）・`empty`（読めたが 0 件）・`failed`（HTTP エラー・通信エラー・フィードでないページ）に分け、`health/feeds-YYYY-MM-DD.json`（JST、同じ日の後の実行で置き換え）に保存する。各フィードに連続失敗日数 `failed_streak` を付ける（前日のファイルから数え、記録の無い日があれば 1 から）。保存は GitHub Actions 上だけ（手元で動かしても `health/` を作らない）。ワークフロー最後の自動コミットで main に入る。集める記事は変えていない。理由：feedparser は 404 などで例外を出さず空の結果を返すため、壊れたフィードが「0 件」と区別できなかった。
- 11/10 に手元から 66 本を読んだ結果：failed 12（Anthropic News・Meta AI Blog・Microsoft AI Blog ほか 404/410/429/非フィード）、empty 3（ArXiv AI・ArXiv ML・Microsoft 365 Copilot Blog）。GitHub の実行環境からの結果は未確認（次の朝の `health/` で分かる）。
- 8:10 のクラウドの点検（`../news-clock/cloud-check-prompt.md`）がこのファイルを読み、`failed_streak` がちょうど 3 のフィード、月曜は 3 以上のもの全部、3 分の 1 以上が失敗した日、記録が 3 日続けて無い日だけ藤川さんにメールで知らせる。Fable 5.2 の独立検証（高 0・中 3・低多数）を反映済み。未対応：3 分の 1 以上の条件は続く限り毎日知らせる（Actions 側の実績を数日見て調整）。フィードの URL の修正・差し替えは点検では行わない（藤川さんの判断）。
- テスト：`tests/test_feed_health.py`。元に戻す方法：該当コミットを `git revert`。

## 再開時の注意と未確認

- 10/7のrequestと同じ `head_sha` のpush runが成功したことは確認済み（確認主体と根拠は運用README）。この文書更新ではLINE/Xの実着信を再確認していない。run成功・公開JSON・配信開始記録を各チャネルの成功証明として使わない。
- 当日docsがある日は非強制実行をskip。docsなしで `automation/delivery-state/YYYY-MM-DD.json` がある日はrun/attemptとSNSログを確認して判断を待つ。時間窓は07:00〜21:59 JST。`force_redeliver` は時間窓と記録のガードを迂回して全チャネルを再送し得るため自動で使わない。記録を削除して再送しない。
- SNS直前に開始記録をmainへpushする実装を維持する。`DELIVERY_GUARD=1`、checkoutの `ref: main`、concurrency、最後の `if: always()` 保存を外さない。ローカルの配信スクリプト直接実行は本番SNSへ送信し得る。
- Cloud Run移行は [移行準備handoff](../cloud-run-migration/handoff.md) の段階。本番移管・VPS解約は未実施。VPS起動cron2行の無効化は10/1の切替記録で、VPSの現在の状態は今回再確認していない。

## 今回の引き継ぎ整備（2026-10-07）

Claude/Geminiの入口と既存READMEをこのhandoff・運用READMEへつなぎ、CLAUDEの古いVPS起動/欠配案内と「永続層はdocsのみ」を更新した。プログラム・workflow・秘密・公開記事・配信状態は変更していない。リンクと差分を読み戻して確認。2026-10-12にこの文書更新をcommitし、10/10の上流変更（RECOVERY_HANDOFF.md・collection_runner.py ほか）とmergeしてorigin/mainへpushした（CLAUDE.mdの衝突は両方の記述を残して解消）。

確認日時は2026-10-07 09:42 JST。追加リンクの存在とプログラム/workflowのハッシュ不変を確認済み。変更前文書は `.backups/20261007-handoff-docs-0939/` に保存してあり、文書だけを戻す場合も後続編集との比較後に対象ファイルを個別に復元する。

次の担当者は自分の変更に合わせてこの節を更新する。Cloud RunやVPSの続きは上記の移行準備資料を読み、現在の本番処理を移管済みと扱わない。
