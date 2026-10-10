# 2026-10-10 朝刊遅延: 他のLLM・保守担当向け引継ぎ

最終更新: 2026-10-10 JST。これは承認済み修正の保守資料です。新しい配信・再実行・権限変更の許可ではありません。

## 最初に読むもの

- 本書: 適用状態、確認済み事実、未解決点、変更の安全境界
- [CLAUDE.md](../CLAUDE.md): リポジトリ全体の本番運用・バックアップ規則
- [automation/README.md](README.md): 専用JSON push入口、同日ガード、復旧契約
- [HISTORY.md](../HISTORY.md): 2026-10-10の変更理由と経緯

## 適用済み状態

- 修正PR: [#17](https://github.com/TadFuji/ai-news-bot/pull/17)
- レビュー済み修正commit: `1acc71cf8c01840c761388d5da2f773feeb1f5c3`
- mainへのmerge commit: `c165546b00b71bbb9821e7b8d2e5807fde2401f0`
- 元main: `996f07044f060c0d14b23f6f6fde2818e3db3635`
- ユーザー承認後に適用。修正確認のための本番生成、SNS配信、force、rerunは実施していない。
- 10/10の公開JSON・送信開始記録はmerge前後で同じblob SHAだった。
  - `docs/2026-10-10.json`: `ece0f08887e272ef7ac0429d5be1e8b8bd4f2876`
  - `automation/delivery-state/2026-10-10.json`: `ce73729f7d7047665577278c6ae4747140107c94`
- 今後の確認ではこの時点の状態を現在の状態とみなさず、最新main・当日JST・最新runを読み直す。

## 障害の事実と不明点

すべて以下の時刻はJST。

1. [主起動run 37997461984](https://github.com/TadFuji/ai-news-bot/actions/runs/37997461984): 07:07:28登録、Stage 2を07:07:52開始。07:08:01に `double free or corruption (out)`、exit 134。
2. [予備run 38014886536](https://github.com/TadFuji/ai-news-bot/actions/runs/38014886536): 07:37予定のcronが10:53:06に登録。登録後約3秒でjob開始、10:56に成功。
3. 失敗と成功は同じcommit、runner image、Python、pip導入バージョンだった。依存更新で回復したとは言えない。
4. 失敗したのは生成・配信を担当するPythonプロセス。stdoutが未flushでスタックも無く、実際に落ちた処理・nativeライブラリは未特定。RSS/本文抽出は候補であり、原因と断定しない。
5. GitHub予備cronの遅れはrun登録前に発生した。GitHub内部の個別原因までは不明。[公式仕様](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)はscheduleの遅延・欠落を認めている。
6. 成功runのLINE/X API成功ログと公開JSONは確認済み。受信端末での実着信確認とは区別する。

## 変更箇所と処理順

`curate_morning_brief.main()`
→ 既存同日docs/開始記録ガード
→ `automation.collection_runner.collect_in_subprocess()`
→ 候補読込・重複排除・2次キュレーション
→ 朝刊保存
→ `automation.delivery_guard.persist_before_send()` が開始記録をmainへpush
→ SNS送信
→ Pages生成
→ workflow末尾でalways保存

- [collection_runner.py](collection_runner.py): 収集だけ別Python。最大2試行、各600秒。試行前後のJST/配信記録チェック、SNS環境変数除外、dotenv無効化、timeout時process groupのkill/reap。
- [collect_rss_gemini.py](../collect_rss_gemini.py): 候補JSONを一時ファイル+fsync+atomic replace。収集子の使用量をfinallyで記録。
- [curate_morning_brief.py](../curate_morning_brief.py): 上記収集ラッパー呼出し。候補0件はexit 1。既存候補があれば選定を継続。
- [daily_rss_gemini.yml](../.github/workflows/daily_rss_gemini.yml): `python -u -X faulthandler`。秘密を含み得るcore dumpは無効化。
- 新しいログは試行番号・終了状態・経過時間のみ。環境変数全体、秘密、記事本文を新たにdumpしない。

## 必ず維持する安全契約

- 主起動はクラウド定時タスクによる専用JSON追加push。GitHub cronは予備。
- push対象は `automation/requests/*.json` または `automation/tests/*.json`。通常コード/docs変更を配信トリガーへ追加しない。
- daily requestはJST当日、新規1件だけ。任意別名、更新、複数変更を混ぜた起動は禁止。
- main checkout、既存concurrency、日付チェック、当日docs/開始記録ガード、末尾always保存を維持。
- 自動retry対象は収集子だけ。SNS・朝刊全体の無条件retry、forceを追加しない。
- docsあり: 再配信しない。開始記録だけあり: 送信成否不明として人の判断を待つ。
- 記録pushの失敗・応答不明時はSNSへ進まない。外部SNSとgitの原子的トランザクションではない。
- 本番スクリプトを動かしてテストしない。既存mock/秘密なし子processテストを使う。

## 検証証拠

- 独立レビューの指摘（dotenv復活、子孫cleanup、候補上書き、完了後guard）を修正。critical/major blockerなし。
- ローカルPython 3.12.14: 105 tests + 7 subtests、ruff、diff check成功。
- PR CI Python 3.11.17: [105 tests + 7 subtests成功](https://github.com/TadFuji/ai-news-bot/actions/runs/38036380715)、[Lint成功](https://github.com/TadFuji/ai-news-bot/actions/runs/38036380693)。
- merge後main: [Tests成功](https://github.com/TadFuji/ai-news-bot/actions/runs/38039330978)、[Lint成功](https://github.com/TadFuji/ai-news-bot/actions/runs/38039330974)。
- テスト: [test_collection_runner.py](../tests/test_collection_runner.py)、[test_daily_guard.py](../tests/test_daily_guard.py)、[test_delivery_start_record.py](../tests/test_delivery_start_record.py)、[test_push_entrypoint.py](../tests/test_push_entrypoint.py)。
- 再検証コマンド: `.venv/bin/python -m pytest tests/ -q`、`.venv/bin/python -m ruff check . --select E9,F63,F7,F82`。
- native abort試験はfake収集子だけで行い、外部通信・本番APIを呼ばない。

## 残る制約と次の調査

- 根因のnative破壊箇所は未解明。同じ障害が2回続けば回復しない。親の2次キュレーション/配信側native crashもこの隔離の対象外。
- 収集は合計約20分の予算。Gemini自身の600秒timeout/内部retryより先に子を停止する場合がある。再試行でAPI費用が増える可能性がある。
- native abort/killまでの未flush使用量は記録できない。子process分は親とは別のusage行になる。
- process group cleanupは悪意のある子を封じるsandboxではない。別sessionへ離れた子孫まで停止保証しない。現collectorは子孫を生成しない。
- GitHub scheduleの定時性は改善・保証していない。「二度と起きない」と表現しない。
- 再発時は最後の段階ログ・faulthandlerスタック・実行環境・pip導入版を比較。再送前にdocs/開始記録/run ID/送信ログを確認し、情報不足で自動再送しない。

## ロールバック

本書はロールバック実行の許可ではない。実施が承認されたら最新mainを確認し、後続変更との衝突をレビューする。

- mergeを取り消す場合は `git revert -m 1 c165546b00b71bbb9821e7b8d2e5807fde2401f0` を専用branchで準備し、テスト・レビュー後に通常PRで反映。
- hard reset/force pushは禁止。request、配信済みdocs、delivery-state、使用量履歴を過去へ巻き戻さない。
- 変更前ソースはmerge第1親 `996f07044f060c0d14b23f6f6fde2818e3db3635` に残る。
