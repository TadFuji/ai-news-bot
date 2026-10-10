"""Contain collection crashes before the irreversible SNS delivery boundary."""
import datetime as dt
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")
COLLECTION_ATTEMPTS = 2
COLLECTION_TIMEOUT_SECONDS = 600


def _run_child(command, root, env):
    """Reap the collector and kill its process group on timeout (Actions/Linux)."""
    with subprocess.Popen(command, cwd=root, env=env, start_new_session=True) as child:
        try:
            return child.wait(timeout=COLLECTION_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            finally:
                child.wait()
            raise


def _check_collection_guard(root):
    """Fail closed before each attempt; these failures must not be swallowed."""
    if os.environ.get("DELIVERY_GUARD") != "1":
        return
    day = dt.datetime.now(JST).date().isoformat()
    if os.environ.get("REQUEST_DATE") != day:
        raise RuntimeError("JST date changed before collection; refuse retry")
    if os.environ.get("FORCE_REDELIVER") != "1":
        if ((root / "docs" / f"{day}.json").exists()
                or (root / "automation/delivery-state" / f"{day}.json").exists()):
            raise RuntimeError("Delivery record exists; refuse collection retry")


def collect_in_subprocess(root=None):
    """Retry only the collector, never the curator or any SNS delivery code.

    The child writes the same candidates as before. A native abort cannot kill
    this parent, and a timeout kills the child's process group and reaps it.
    Existing valid candidates remain available if both attempts fail.
    """
    root = Path(root) if root is not None else Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONFAULTHANDLER"] = "1"
    # Prevent load_dotenv() in collector dependencies from restoring SNS keys.
    env["PYTHON_DOTENV_DISABLED"] = "1"
    # Collection needs the existing Gemini credential, but no SNS credentials.
    for key in list(env):
        if key.startswith(("LINE_", "X_")) or key in ("XAI_API_KEY", "GEMINI_IMAGE_API_KEY"):
            env.pop(key)
    command = [sys.executable, "-u", "-X", "faulthandler", str(root / "collect_rss_gemini.py")]
    for attempt in range(1, COLLECTION_ATTEMPTS + 1):
        _check_collection_guard(root)
        print(f"Collection attempt {attempt}/{COLLECTION_ATTEMPTS} started", flush=True)
        started = time.monotonic()
        try:
            returncode = _run_child(command, root, env)
            _check_collection_guard(root)
            reason = f"exit={returncode}"
            if returncode == 0:
                print(f"Collection completed in {time.monotonic() - started:.1f}s", flush=True)
                return True
        except subprocess.TimeoutExpired:
            reason = "timeout"
        except OSError:
            # Do not print exception values that could include environment data.
            reason = "process-start-failed"
        _check_collection_guard(root)
        print(f"Collection attempt {attempt} failed ({reason}); "
              f"elapsed={time.monotonic() - started:.1f}s", flush=True)
        if attempt < COLLECTION_ATTEMPTS:
            time.sleep(2)
    print("Collection exhausted; use existing candidates if available", flush=True)
    return False
