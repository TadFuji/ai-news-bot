"""Persist a conservative pre-send record before any daily SNS delivery."""
import datetime as dt
import json
import os
from pathlib import Path
import re
import subprocess
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")


def started_today(root=None, now=None):
    root = Path(root) if root is not None else Path(__file__).resolve().parents[1]
    day = (now or dt.datetime.now(JST)).astimezone(JST).date().isoformat()
    return (root / "automation/delivery-state" / f"{day}.json").exists()


def persist_before_send(root=None):
    """A failed/ambiguous git push raises BEFORE the caller can send anything.

    Enabled explicitly by the daily workflow. No token values are handled here;
    checkout's existing contents credential performs the git operations.
    """
    if os.environ.get("DELIVERY_GUARD") != "1":
        return
    root = Path(root) if root is not None else Path(__file__).resolve().parents[1]
    day = dt.datetime.now(JST).date().isoformat()
    if os.environ.get("REQUEST_DATE") != day:
        raise RuntimeError("JST date changed since daily gate; refuse delivery")
    run_id, attempt = os.environ.get("GITHUB_RUN_ID", ""), os.environ.get("GITHUB_RUN_ATTEMPT", "")
    if not re.fullmatch(r"[0-9]+", run_id) or not re.fullmatch(r"[0-9]+", attempt):
        raise RuntimeError("invalid Actions run identity")
    path = root / "automation/delivery-state" / f"{day}.json"
    if path.exists() and os.environ.get("FORCE_REDELIVER") != "1":
        raise RuntimeError("previous delivery may have sent; human review required")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"date": day, "state": "delivery-started", "run_id": run_id,
                               "run_attempt": attempt}, indent=2) + "\n", encoding="utf-8")
    def git(*args):
        subprocess.run(["git", *args], cwd=root, check=True, timeout=120)
    git("config", "user.name", "github-actions[bot]")
    git("config", "user.email", "github-actions[bot]@users.noreply.github.com")
    git("add", str(path.relative_to(root)))
    git("commit", "-m", f"chore: record delivery start {day} [skip ci]")
    git("pull", "--rebase", "--autostash", "origin", "main")
    git("push", "origin", "HEAD:main")
    print(f"Delivery-start record persisted for {day}; SNS sending can begin.")
