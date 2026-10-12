# handoff.md — AIニュースの引き継ぎ

最終確認: 2026-10-12。作業開始・終了時の更新ルールは [AGENTS.md](AGENTS.md)。2026-10-10の朝刊遅延と適用済み再発低減策（collection_runner など）は [automation/RECOVERY_HANDOFF.md](automation/RECOVERY_HANDOFF.md) を先に読む。現在の主起動は **OpenAI dot（どっちゃん）の定時タスク、07:07 JST**、実処理はGitHub Actions。起動・監視・再送判断の正本と10/7の成功確認は [automation/README.md](automation/README.md)。構成は [README.md](README.md)、過去の変更は [HISTORY.md](HISTORY.md)。

## 再開時の注意と未確認

- 10/7のrequestと同じ `head_sha` のpush runが成功したことは確認済み（確認主体と根拠は運用README）。この文書更新ではLINE/Xの実着信を再確認していない。run成功・公開JSON・配信開始記録を各チャネルの成功証明として使わない。
- 当日docsがある日は非強制実行をskip。docsなしで `automation/delivery-state/YYYY-MM-DD.json` がある日はrun/attemptとSNSログを確認して判断を待つ。時間窓は07:00〜21:59 JST。`force_redeliver` は時間窓と記録のガードを迂回して全チャネルを再送し得るため自動で使わない。記録を削除して再送しない。
- SNS直前に開始記録をmainへpushする実装を維持する。`DELIVERY_GUARD=1`、checkoutの `ref: main`、concurrency、最後の `if: always()` 保存を外さない。ローカルの配信スクリプト直接実行は本番SNSへ送信し得る。
- Cloud Run移行は [移行準備handoff](../cloud-run-migration/handoff.md) の段階。本番移管・VPS解約は未実施。VPS起動cron2行の無効化は10/1の切替記録で、VPSの現在の状態は今回再確認していない。

## 今回の引き継ぎ整備（2026-10-07）

Claude/Geminiの入口と既存READMEをこのhandoff・運用READMEへつなぎ、CLAUDEの古いVPS起動/欠配案内と「永続層はdocsのみ」を更新した。プログラム・workflow・秘密・公開記事・配信状態は変更していない。リンクと差分を読み戻して確認。2026-10-12にこの文書更新をcommitし、10/10の上流変更（RECOVERY_HANDOFF.md・collection_runner.py ほか）とmergeしてorigin/mainへpushした（CLAUDE.mdの衝突は両方の記述を残して解消）。

確認日時は2026-10-07 09:42 JST。追加リンクの存在とプログラム/workflowのハッシュ不変を確認済み。変更前文書は `.backups/20261007-handoff-docs-0939/` に保存してあり、文書だけを戻す場合も後続編集との比較後に対象ファイルを個別に復元する。

次の担当者は自分の変更に合わせてこの節を更新する。Cloud RunやVPSの続きは上記の移行準備資料を読み、現在の本番処理を移管済みと扱わない。
