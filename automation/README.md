# 日次push入口・監視・復旧（現行運用: 2026-10-07）

対象repo: `TadFuji/ai-news-bot` / branch: `main` / workflow: `daily_rss_gemini.yml`。
**主起動と同runの監視は OpenAI dot（どっちゃん）の定時タスクが担当する。AIニュースは毎日07:07 JST。** これはユーザー確認済みの運用であり、収集・生成・LINE/X配信・Pages保存はGitHub Actionsが担当する。GitHub予備scheduleは07:37 JSTを維持。VPSのHN/AI起動cron2行を2026-10-01にコメント化した切替記録は下記に保全するが、現在のVPS稼働は今回再確認していない。

dotは同日request・公開JSON・配信開始記録・実行中runを照会してから一意pathを追加し、そのcommitと同じrunを監視する。応答不明なら同じpath・commit・runを読む。曖昧な再送やforceは禁止。送信境界前の失敗が確実な場合だけ、下記の復旧条件を満たす同じrunの失敗jobを1回再実行し、結果を報告する。開始記録がある日は先にrun/attemptとSNSログを調べる。

## 10/7の確認と記録の読み方

ユーザー相談の親スレッドが接続済みGitHubの読取で、以下の一致とsuccessを確認した。この文書編集担当が本番を再実行したものではない。

- request commit: [98dee82272106e4d4eb0543b77cf95cbef48ab0f](https://github.com/TadFuji/ai-news-bot/commit/98dee82272106e4d4eb0543b77cf95cbef48ab0f)
- 実行: [37538737603](https://github.com/TadFuji/ai-news-bot/actions/runs/37538737603)、event=`push`、`head_sha` が上記commitと一致、conclusion=`success`。
- commit title: `Daily request 2026-10-07 by dot`。GitHub actorは `TadFuji`。OpenAI dotへの帰属はユーザー確認済みの運用情報によるもので、actor名だけからは推定しない。

request作成・run成功・当日公開JSON・LINE/X実着信は別々の確認。開始記録も送信成功の証明ではない。今回の文書整備では実着信を再確認していない。Cloud Runは [移行準備](../../cloud-run-migration/handoff.md) の段階で、本番移管済みではない。

作業者は [AGENTS.md](../AGENTS.md) に従い毎回 [handoff.md](../handoff.md) を更新する。起動の正本はこの文書、入口判定は [daily_gate.py](daily_gate.py)、送信前記録は [delivery_guard.py](delivery_guard.py)、呼出し順は [curate_morning_brief.py](../curate_morning_brief.py)、配線は [daily_rss_gemini.yml](../.github/workflows/daily_rss_gemini.yml)。

## 起動契約

Contents API の create_file で **新規ファイル1件だけ** mainへ追加する。更新・削除・コード変更と混ぜたpushは拒否。commit messageに `[skip ci]` / `[skip actions]` を含めない。

- 日次path: `automation/requests/YYYY-MM-DD.json`
- 日次content: `{"version":1,"date":"YYYY-MM-DD","mode":"daily"}`
- 日次commit title: `Daily request YYYY-MM-DD by dot`（運用上の表記。実装の受理判定はpath・JSON・push差分による）。
- no-op path: `automation/tests/YYYY-MM-DD-<test_id>.json`
- no-op content: `{"version":1,"date":"YYYY-MM-DD","mode":"noop","test_id":"<test_id>"}`
- 日付は **Asia/Tokyo の当日**。古い日付の遅延起動は拒否。`test_id` は英小文字/数字で始まり、英小文字/数字/ハイフンのみ、1〜40文字。
- JSONは上記キーのみ、最大1024 bytes。重複キー、未知のmode、任意force入力、日付/path不一致を拒否。
- 信号の内容はpush eventのcommit SHAから読み、当日成果物は最新mainで確認。競合したpush/schedule/dispatchは既存concurrencyで直列化。

no-opはcheckoutと入口検証だけ。依存導入・API生成・SNS配信・結果commit/pushを全て省く。no-op用ファイルの新規commit自体は残る。

日次信号は一日1つ。create_fileの応答が不明なら同じpathのfile/commit/runを読む。別名のdaily信号や更新、無条件rerunで再送しない。既存fileがあることは成功の証明ではない。

## 完了確認

1. create_fileが返したcommit SHAと同じ `head_sha`、event=`push`、workflow=`daily_rss_gemini.yml` のrunを探す。見つからない場合は未確認。これだけでは生成/配信成功とはしない。
2. runのstatus/conclusionとjobのstepsを見る。入口だけ成功で後続がskippedならno-op/既に生成済み。run全体の緑だけで新規成果物の完成とは判定しない。
3. mainに当日の `docs/YYYY-MM-DD.json` があるか確認する。HNはGenerate digestとCommit results、AIはStage2と最終保存ステップの結果も見る。
4. AIの公開JSONはSNS実着信の証明ではない。LINE/Xの送信結果はStage2ログで確認。片方失敗・fallbackでもrunは赤になり得る。SNS送信を含むrunの全件rerunは自動で行わない。

## 同日ガードと失敗時の判断

HN専用の成果物・時間窓・再生成判断は [HN側の運用README](../../Hacker-News/automation/README.md#同日ガードと失敗時の判断) を正本とする。

AI: 当日docsの存在を従来どおり保護。非強制実行は7時前・22時以降に開始しない。SNS直前に `automation/delivery-state/YYYY-MM-DD.json`（date/state/run_id/run_attemptのみ）を **mainへpushしてから** SNSを呼ぶ。git操作の失敗・応答不明なら送信に進まない。開始記録だけ残る日は自動入口を赤で止める。

- docsがある: 自動再配信しない。SNS欠配が疑われるときも、全体を再送せず該当チャネルのログを確認。
- docsなし・開始記録あり: 記録のrun_idとrun_attemptを調べる。送信成功/開始後の中断/成否不明は人の判断を待つ。
- docsなし・開始記録なし: Stage2が送信境界へ到達していないことをsteps/logsでも確認してから、非強制のdispatchで当日を回復できる。dispatchも同じガードを通る。
- 開始記録のpush失敗: 送信前停止をログで確認。最終always保存によりローカルの開始記録が後からpushされる場合もあるので、main上の状態を改めて確認する。
- AIの手動 `force_redeliver=true` は従来どおり明示操作として残す。当日docs・開始記録・時間窓のガードを迂回し、既存の開始記録を上書きして配信済みチャネルまで再配信し得る。チャネル限定再送ではない。送信境界後のrunを自動force/rerunせず、request・docs・開始記録を削除して回復しない。新しい秘密や権限は不要。

開始記録は再送を安全側へ止めるための記録で、LINE/X APIとの原子的なトランザクションではない。チャネル別の成否不明を完全解消する仕組みではない。

## バックアップと復旧

以下は2026-10-01の切替時に記録した復旧案。現在のVPS/他cron/定時タスクの状態を確認せず実行しない。本日の文書整備でSSH・cron変更・復旧は行っていない。

実装前main: `2e7c1a08c7fe124b2c7533b22959708b30053e57`。変更前workflow/編集対象はHNの `test-output/trigger-cutover-backup-20261001/`、AIの `.backups/20261001-push-trigger/` に退避済み（非コミット）。10/1の切替作業では既存のHN `handoff.md` を変更しなかった。

VPS既存crontabは `/root/trigger-cutover-backups/20261001/crontab.before`。SHA256: `82c142a6bdd0d5a51f65d0726431fc6e80184e1c3be809edf0e00554e23e6ac9`。`.env` や認証値をコピーしていない。起動スクリプトは変更しないためハッシュだけ記録: HN `a0ebd9a0c8a708ad7d48b8237bd88ba4cd0e9ca38668303448419b1005ecdf17`、AI `4186cf03f631c91ad9d4d86450b7add36bfdec2a25a3d229c1f1a259a28ec58d`。

切替後の復旧は、クラウド定時2タスクを一時停止し、**他cronに後日の変更がないことを確認した場合だけ** `ssh openclaw 'crontab /root/trigger-cutover-backups/20261001/crontab.before'`。他cronに変更があれば該当2行だけ戻す。復旧行は `0 6 * * * /root/hn-trigger/run.sh` と `7 7 * * * /root/ai-news-trigger/run.sh`。2026-10-01にこの2行だけ無効化した。他の11行はbyte単位で維持。

コード復旧は当該実装commitを `git revert <implementation-commit>` してpush（force/resetはしない）。後日作られたrequest・docs・開始記録・記事を巻き戻さない。VPS停止中に入口をrevertすると定時起動が失われるため、先にVPSの該当行を復旧する。


## 切替実証

- 直前backup: `/root/trigger-cutover-backups/20261001/crontab.before-cutover`（0600）。SHA256 `82c142a6bdd0d5a51f65d0726431fc6e80184e1c3be809edf0e00554e23e6ac9`。
- 切替後crontab SHA256 `3c11e5292aa77902adf7f802c92bcdfb141e00f4c664909a48e08795868dbe33`。
- 変更は次の2行の先頭prefixのみ。

```cron
# cloud-daily-trigger disabled 2026-10-01 | 7 7 * * * /root/ai-news-trigger/run.sh
# cloud-daily-trigger disabled 2026-10-01 | 0 6 * * * /root/hn-trigger/run.sh
```

他者が後日変更したcronを守る復旧は、クラウド2タスクを停止した上で、次の2行だけ元へ戻す（秘密値は表示しない）。

```sh
ssh openclaw 'python3 -' <<'PYRESTORE'
import subprocess
prefix = b'# cloud-daily-trigger disabled 2026-10-01 | '
targets = {b'0 6 * * * /root/hn-trigger/run.sh', b'7 7 * * * /root/ai-news-trigger/run.sh'}
before = subprocess.check_output(['crontab', '-l'])
lines = before.splitlines(keepends=True)
assert all(sum(line.rstrip(b'\r\n') == prefix + target for line in lines) == 1 for target in targets)
assert not any(line.rstrip(b'\r\n') in targets for line in lines)
after = b''.join(line[len(prefix):] if line.rstrip(b'\r\n') in {prefix + target for target in targets} else line for line in lines)
assert subprocess.check_output(['crontab', '-l']) == before
subprocess.run(['crontab', '-'], input=after, check=True)
assert subprocess.check_output(['crontab', '-l']) == after
print('Restored only the two daily trigger lines.')
PYRESTORE
```

子CLI/親connectorのno-opは両repo成功、生成/SNS/結果commitステップ全skipped。AIは既存設定でTests/LintとPages再デプロイがpushに反応するため、CI/デプロイ消費はある。記事/SNSの新規配信はなく、実装前との差分でHN output/usage/healthとAI docs/usageが不変。次の本番日次における実生成/実SNSはこの検証では実行していない。
