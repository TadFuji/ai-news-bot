"""Validate immutable push requests and guard all daily entry points (stdlib only)."""
import datetime as dt
import json
import os
from pathlib import Path
import re
import subprocess
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")
TEST_ID = r"[a-z0-9][a-z0-9-]{0,39}"


def git(*args):
    return subprocess.check_output(["git", *args], text=True).strip()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def validate_request(path, content, today):
    if len(content.encode("utf-8")) > 1024:
        raise ValueError("request exceeds 1024 bytes")
    payload = json.loads(content, object_pairs_hook=unique_object)
    if not isinstance(payload, dict):
        raise ValueError("request must be a JSON object")
    day = payload.get("date")
    if not isinstance(day, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
        raise ValueError("date must be YYYY-MM-DD")
    dt.date.fromisoformat(day)
    if type(payload.get("version")) is not int or payload["version"] != 1:
        raise ValueError("unsupported version")
    if day != today:
        raise ValueError("request date must equal today's JST date; stale requests are refused")
    if payload.get("mode") == "daily":
        if set(payload) != {"version", "date", "mode"} or path != f"automation/requests/{day}.json":
            raise ValueError("daily request path or fields are invalid")
    elif payload.get("mode") == "noop":
        test_id = payload.get("test_id")
        if not isinstance(test_id, str) or not re.fullmatch(TEST_ID, test_id):
            raise ValueError("invalid test_id")
        if set(payload) != {"version", "date", "mode", "test_id"} or path != f"automation/tests/{day}-{test_id}.json":
            raise ValueError("no-op request path or fields are invalid")
    else:
        raise ValueError("mode must be daily or noop")
    return payload


def request_from_push(event, today):
    if event.get("ref") != "refs/heads/main" or event.get("deleted"):
        raise ValueError("requests must be pushed to main")
    before, after = event.get("before", ""), event.get("after", "")
    for sha in (before, after):
        if not re.fullmatch(r"[0-9a-f]{40}", sha) or sha == "0" * 40:
            raise ValueError("invalid push commit")
        # Checkout main may be newer than this event, so read the immutable
        # event commit, never the file at the latest branch tip.
        try:
            git("cat-file", "-e", f"{sha}^{{commit}}")
        except subprocess.CalledProcessError:
            git("fetch", "--no-tags", "--depth=2", "origin", sha)
    changes = git("diff", "--name-status", before, after).splitlines()
    if len(changes) != 1 or not changes[0].startswith("A\t"):
        raise ValueError("a signal push must add exactly one new request file and change nothing else")
    path = changes[0][2:]
    if not re.fullmatch(r"automation/(requests/\d{4}-\d{2}-\d{2}|tests/\d{4}-\d{2}-\d{2}-" + TEST_ID + r")\.json", path):
        raise ValueError("invalid request filename")
    return validate_request(path, git("show", f"{after}:{path}"), today)


def decide(project, event_name, event, root=Path("."), now=None):
    now = now or dt.datetime.now(JST)
    day = now.astimezone(JST).date().isoformat()
    force = False
    if event_name == "push":
        payload = request_from_push(event, day)
        if payload["mode"] == "noop":
            return False, day, "noop: " + payload["test_id"]
    elif event_name == "workflow_dispatch":
        force = project == "ai" and event.get("inputs", {}).get("force_redeliver") in (True, "true")
    elif event_name != "schedule":
        raise ValueError("unsupported event")
    if not force:
        if project == "hn":
            count = os.environ.get("COUNT", "30")
            if not re.fullmatch(r"[1-9][0-9]?", count):
                raise ValueError("invalid COUNT")
            if list((root / "output").glob(f"{day}-HackerNews-Top{count}.md")) or list((root / "output").glob(f"{day}-[0-9][0-9][0-9][0-9]-HackerNews-Top{count}.md")):
                return False, day, "already-generated"
        elif project == "ai":
            if (root / "docs" / f"{day}.json").is_file():
                return False, day, "already-delivered"
            if (root / "automation/delivery-state" / f"{day}.json").exists():
                raise ValueError("delivery-started record exists without published JSON; human review required, do not rerun")
        else:
            raise ValueError("unknown project")
        hour = now.astimezone(JST).hour
        if hour < (6 if project == "hn" else 7) or hour >= 22:
            return False, day, "outside-daytime-window"
    return True, day, "ready" + ("-explicit-force" if force else "")


def main():
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    run, day, reason = decide(os.environ["DAILY_PROJECT"], os.environ["GITHUB_EVENT_NAME"], event)
    with open(os.environ["GITHUB_OUTPUT"], "a") as out:
        out.write(f"run={'true' if run else 'false'}\ndate={day}\nreason={reason}\n")
    summary = f"Daily gate: {reason}; JST date: {day}. Request acceptance is not proof of delivery.\n"
    print(summary.strip())
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as out:
        out.write(summary)


if __name__ == "__main__":
    main()
