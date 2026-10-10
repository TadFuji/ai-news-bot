"""No network, API keys, generation, or delivery in crash-recovery tests."""
import datetime as dt
from pathlib import Path
import subprocess
from unittest.mock import Mock

import pytest

from automation import collection_runner as cr


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    monkeypatch.delenv("DELIVERY_GUARD", raising=False)
    monkeypatch.delenv("FORCE_REDELIVER", raising=False)
    monkeypatch.setattr(cr.time, "sleep", lambda _: None)


def test_success_runs_only_collector_and_drops_sns_credentials(monkeypatch, tmp_path):
    monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "fake-line")
    monkeypatch.setenv("X_ACCESS_TOKEN", "fake-x")
    monkeypatch.setenv("GOOGLE_API_KEY", "fake-gemini")
    run = Mock(return_value=0)
    monkeypatch.setattr(cr, "_run_child", run)
    assert cr.collect_in_subprocess(tmp_path)
    assert run.call_count == 1
    args, kw = run.call_args
    env = args[2]
    assert args[0][-1] == str(tmp_path / "collect_rss_gemini.py")
    assert args[0][1:4] == ["-u", "-X", "faulthandler"]
    assert "LINE_CHANNEL_ACCESS_TOKEN" not in env
    assert "X_ACCESS_TOKEN" not in env
    assert env["GOOGLE_API_KEY"] == "fake-gemini"
    assert env["PYTHON_DOTENV_DISABLED"] == "1"


@pytest.mark.parametrize("first", [-6, 1, "timeout", "oserror"])
def test_failure_retries_only_once(monkeypatch, tmp_path, first):
    error = {"timeout": subprocess.TimeoutExpired("collector", 600),
             "oserror": OSError("not logged")}.get(first)
    outcome = error if error else first
    run = Mock(side_effect=[outcome, 0])
    monkeypatch.setattr(cr, "_run_child", run)
    assert cr.collect_in_subprocess(tmp_path)
    assert run.call_count == 2


def test_both_fail_returns_false_and_logs_no_exception_content(monkeypatch, tmp_path, capsys):
    run = Mock(side_effect=OSError("private exception content"))
    monkeypatch.setattr(cr, "_run_child", run)
    assert not cr.collect_in_subprocess(tmp_path)
    assert run.call_count == 2
    assert "private exception content" not in capsys.readouterr().out


@pytest.mark.parametrize("record", ["docs", "automation/delivery-state"])
def test_delivery_record_blocks_even_the_first_attempt(monkeypatch, tmp_path, record):
    day = dt.datetime.now(cr.JST).date().isoformat()
    monkeypatch.setenv("DELIVERY_GUARD", "1")
    monkeypatch.setenv("REQUEST_DATE", day)
    path = tmp_path / record / f"{day}.json"
    path.parent.mkdir(parents=True)
    path.write_text("{}")
    run = Mock()
    monkeypatch.setattr(cr, "_run_child", run)
    with pytest.raises(RuntimeError, match="Delivery record"):
        cr.collect_in_subprocess(tmp_path)
    run.assert_not_called()


def test_guard_rechecked_before_second_attempt(monkeypatch, tmp_path):
    day = dt.datetime.now(cr.JST).date().isoformat()
    monkeypatch.setenv("DELIVERY_GUARD", "1")
    monkeypatch.setenv("REQUEST_DATE", day)
    def fail_and_cross_date(*args, **kwargs):
        monkeypatch.setenv("REQUEST_DATE", "2000-01-01")
        return -6
    run = Mock(side_effect=fail_and_cross_date)
    monkeypatch.setattr(cr, "_run_child", run)
    with pytest.raises(RuntimeError, match="JST date changed"):
        cr.collect_in_subprocess(tmp_path)
    assert run.call_count == 1


def test_real_native_abort_child_does_not_abort_parent(monkeypatch, tmp_path):
    # Deliberate child-only signal. No production collector is ever executed.
    script = tmp_path / "collect_rss_gemini.py"
    script.write_text(
        "import os, resource\nfrom pathlib import Path\n"
        "resource.setrlimit(resource.RLIMIT_CORE, (0, 0))\n"
        "p = Path('attempted')\n"
        "if not p.exists():\n    p.write_text('1')\n    os.abort()\n"
    )
    assert cr.collect_in_subprocess(tmp_path)
    assert (tmp_path / "attempted").read_text() == "1"


def test_real_timeout_is_bounded_and_child_is_reaped(monkeypatch, tmp_path):
    (tmp_path / "collect_rss_gemini.py").write_text("import time\ntime.sleep(30)\n")
    monkeypatch.setattr(cr, "COLLECTION_TIMEOUT_SECONDS", 0.05)
    assert not cr.collect_in_subprocess(tmp_path)


def test_timeout_kills_grandchildren(monkeypatch, tmp_path):
    (tmp_path / "collect_rss_gemini.py").write_text(
        "import subprocess, sys, time\nfrom pathlib import Path\n"
        "p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])\n"
        "with open('pids', 'a') as f: f.write(str(p.pid) + '\\n')\n"
        "time.sleep(30)\n"
    )
    monkeypatch.setattr(cr, "COLLECTION_TIMEOUT_SECONDS", 0.5)
    assert not cr.collect_in_subprocess(tmp_path)
    pids = (tmp_path / "pids").read_text().splitlines()
    assert len(pids) == 2
    for pid in pids:
        stat = Path(f"/proc/{pid}/stat")
        # A killed orphan can await init reaping; it must no longer be running.
        assert not stat.exists() or stat.read_text().split()[2] == "Z"


def test_dotenv_cannot_restore_sns_keys(tmp_path):
    (tmp_path / ".env").write_text("LINE_CHANNEL_ACCESS_TOKEN=fake\nX_ACCESS_TOKEN=fake\n")
    (tmp_path / "collect_rss_gemini.py").write_text(
        "import os\nfrom dotenv import load_dotenv\nload_dotenv()\n"
        "assert 'LINE_CHANNEL_ACCESS_TOKEN' not in os.environ\n"
        "assert 'X_ACCESS_TOKEN' not in os.environ\n"
    )
    assert cr.collect_in_subprocess(tmp_path)


@pytest.mark.parametrize("returncode", [0, -6])
def test_record_appearing_during_child_stops_pipeline(monkeypatch, tmp_path, returncode):
    day = dt.datetime.now(cr.JST).date().isoformat()
    monkeypatch.setenv("DELIVERY_GUARD", "1")
    monkeypatch.setenv("REQUEST_DATE", day)
    def finish_and_mark(*args):
        path = tmp_path / "automation/delivery-state" / f"{day}.json"
        path.parent.mkdir(parents=True)
        path.write_text("{}")
        return returncode
    run = Mock(side_effect=finish_and_mark)
    monkeypatch.setattr(cr, "_run_child", run)
    with pytest.raises(RuntimeError, match="Delivery record"):
        cr.collect_in_subprocess(tmp_path)
    assert run.call_count == 1


def test_success_after_date_rollover_stops_pipeline(monkeypatch, tmp_path):
    day = dt.datetime.now(cr.JST).date().isoformat()
    monkeypatch.setenv("DELIVERY_GUARD", "1")
    monkeypatch.setenv("REQUEST_DATE", day)
    def finish_late(*args):
        monkeypatch.setenv("REQUEST_DATE", "2000-01-01")
        return 0
    monkeypatch.setattr(cr, "_run_child", finish_late)
    with pytest.raises(RuntimeError, match="JST date changed"):
        cr.collect_in_subprocess(tmp_path)


def test_atomic_candidate_write_preserves_old_file_on_failure(monkeypatch, tmp_path):
    import collect_rss_gemini as collector
    target = tmp_path / "candidates_20261010_0707.json"
    original = b'{"articles":[{"url":"https://example.com/old"}]}'
    target.write_bytes(original)
    def partial_dump(data, file, **kwargs):
        file.write('{"articles":')
        raise ValueError("injected write failure")
    monkeypatch.setattr(collector.json, "dump", partial_dump)
    with pytest.raises(ValueError):
        collector.save_candidates_atomic(str(target), {"articles": []})
    assert target.read_bytes() == original
    assert list(tmp_path.glob(".candidates-*.tmp")) == []


def test_both_failed_attempts_preserve_existing_candidates(monkeypatch, tmp_path):
    target = tmp_path / "output/candidates_20261010_0707.json"
    target.parent.mkdir()
    original = b'{"articles":[{"url":"https://example.com/old"}]}'
    target.write_bytes(original)
    monkeypatch.setattr(cr, "_run_child", Mock(return_value=-6))
    assert not cr.collect_in_subprocess(tmp_path)
    assert target.read_bytes() == original


def test_no_candidates_fails_without_sending(monkeypatch, tmp_path):
    import curate_morning_brief as cm
    import distribute_daily
    monkeypatch.setattr(cm, "DOCS_DIR", str(tmp_path))
    monkeypatch.setattr(cm, "load_candidates", lambda: [])
    collect = Mock(return_value=False)
    monkeypatch.setattr(cm, "collect_in_subprocess", collect)
    send = Mock()
    monkeypatch.setattr(distribute_daily, "main", send)
    with pytest.raises(SystemExit) as err:
        cm.main()
    assert err.value.code == 1
    collect.assert_called_once()
    send.assert_not_called()


def test_workflow_keeps_crash_diagnostics_without_core_dumps():
    workflow = Path(".github/workflows/daily_rss_gemini.yml").read_text()
    assert "ulimit -c 0" in workflow
    assert "python -u -X faulthandler curate_morning_brief.py" in workflow
