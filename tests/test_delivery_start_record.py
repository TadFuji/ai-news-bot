"""SNS must never begin unless its conservative start record is durable."""
import datetime as dt
import json
from pathlib import Path
import subprocess
from unittest.mock import Mock

import pytest
import curate_morning_brief as cm
from automation import delivery_guard as dg


def _enable(monkeypatch):
    monkeypatch.setenv("DELIVERY_GUARD", "1")
    monkeypatch.setenv("REQUEST_DATE", dt.datetime.now(dg.JST).date().isoformat())
    monkeypatch.setenv("GITHUB_RUN_ID", "12345")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")
    monkeypatch.setenv("FORCE_REDELIVER", "0")


def test_every_git_failure_aborts_before_send(monkeypatch, tmp_path):
    _enable(monkeypatch)
    for fail_at in range(6):
        calls = []
        def git(args, **kwargs):
            calls.append(args)
            if len(calls) == fail_at + 1:
                raise subprocess.CalledProcessError(1, args)
        monkeypatch.setattr(dg.subprocess, "run", git)
        # A separate temp root prevents the previous failed attempt's local record
        # from becoming the reason a subsequent case stopped.
        root = tmp_path / str(fail_at)
        root.mkdir()
        sent = Mock()
        with pytest.raises(subprocess.CalledProcessError):
            dg.persist_before_send(root)
            sent()
        sent.assert_not_called()


def test_push_is_last_prerequisite_and_only_record_is_staged(monkeypatch, tmp_path):
    _enable(monkeypatch)
    calls = []
    monkeypatch.setattr(dg.subprocess, "run", lambda args, **kw: calls.append(args))
    dg.persist_before_send(tmp_path)
    day = dt.datetime.now(dg.JST).date().isoformat()
    assert calls[-1] == ["git", "push", "origin", "HEAD:main"]
    assert ["git", "add", f"automation/delivery-state/{day}.json"] in calls
    assert json.loads((tmp_path / f"automation/delivery-state/{day}.json").read_text())["run_id"] == "12345"
    with pytest.raises(RuntimeError, match="previous delivery"):
        dg.persist_before_send(tmp_path)
    monkeypatch.setenv("FORCE_REDELIVER", "1")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "2")
    dg.persist_before_send(tmp_path)


def test_date_rollover_aborts_without_git(monkeypatch, tmp_path):
    _enable(monkeypatch)
    monkeypatch.setenv("REQUEST_DATE", "2020-01-01")
    git = Mock()
    monkeypatch.setattr(dg.subprocess, "run", git)
    with pytest.raises(RuntimeError, match="date changed"):
        dg.persist_before_send(tmp_path)
    git.assert_not_called()


def test_pipeline_stops_when_start_record_cannot_be_persisted(monkeypatch, tmp_path):
    _enable(monkeypatch)
    monkeypatch.setattr(cm, "DOCS_DIR", str(tmp_path))
    monkeypatch.setattr(dg, "started_today", lambda: False)
    monkeypatch.setattr(cm, "load_candidates", lambda: [{"url": "https://example.com/a"}])
    import distribute_daily
    import build_pages
    monkeypatch.setattr(cm, "collect_in_subprocess", Mock(return_value=True))
    monkeypatch.setattr(cm, "get_delivered_urls", lambda **kw: set())
    monkeypatch.setattr(cm, "dedup_articles", lambda x: x)
    monkeypatch.setattr(cm, "curate_with_gemini", lambda x: {"articles": x})
    monkeypatch.setattr(cm, "save_morning_brief", Mock())
    def fail():
        raise subprocess.CalledProcessError(1, ["git", "push"])
    monkeypatch.setattr(dg, "persist_before_send", fail)
    send, build = Mock(), Mock()
    monkeypatch.setattr(distribute_daily, "main", send)
    monkeypatch.setattr(build_pages, "build_pages", build)
    with pytest.raises(subprocess.CalledProcessError):
        cm.main()
    send.assert_not_called()
    build.assert_not_called()


def test_pipeline_ambiguous_previous_attempt_stops_before_collection(monkeypatch, tmp_path):
    _enable(monkeypatch)
    monkeypatch.setattr(cm, "DOCS_DIR", str(tmp_path))
    monkeypatch.setattr(dg, "started_today", lambda: True)
    collect = Mock()
    monkeypatch.setattr(cm, "load_candidates", collect)
    with pytest.raises(RuntimeError, match="Previous delivery"):
        cm.main()
    collect.assert_not_called()


def test_workflow_noop_gates_all_mutating_and_secret_steps():
    text = Path('.github/workflows/daily_rss_gemini.yml').read_text()
    assert text.count("if: steps.guard.outputs.run == 'true'") == 3
    assert sum(line.strip() == "if: always() && steps.guard.outputs.run == 'true'" for line in text.splitlines()) == 2
    assert "ref: main" in text
    assert "group: morning-brief-${{ github.ref }}" in text
    assert "github.event_name == 'workflow_dispatch' && inputs.force_redeliver" in text


def test_start_record_reaches_local_bare_remote(monkeypatch, tmp_path):
    _enable(monkeypatch)
    remote, work = tmp_path / "remote.git", tmp_path / "work"
    subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
    subprocess.run(["git", "init", "-b", "main", str(work)], check=True, capture_output=True)
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=work, text=True).strip()
    git("config", "user.name", "offline-test")
    git("config", "user.email", "offline@example.invalid")
    (work / "README.md").write_text("offline fixture\n")
    git("add", "README.md")
    git("commit", "-m", "fixture")
    git("remote", "add", "origin", str(remote))
    git("push", "-u", "origin", "main")
    dg.persist_before_send(work)
    day = dt.datetime.now(dg.JST).date().isoformat()
    content = subprocess.check_output(["git", "--git-dir", str(remote), "show",
                                       f"main:automation/delivery-state/{day}.json"], text=True)
    assert json.loads(content)["state"] == "delivery-started"
    monkeypatch.setenv("FORCE_REDELIVER", "1")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "2")
    dg.persist_before_send(work)
    assert git("status", "--porcelain") == ""

