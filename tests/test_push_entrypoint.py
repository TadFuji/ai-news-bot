"""Offline safety tests for immutable daily push requests and shared guards."""
import datetime as dt
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from automation import daily_gate as gate

NOW = dt.datetime(2026, 10, 1, 8, tzinfo=gate.JST)
DAY = "2026-10-01"


class RequestTests(unittest.TestCase):
    def test_daily_and_noop_contract(self):
        for mode in ("daily", "noop"):
            payload = {"version": 1, "date": DAY, "mode": mode}
            path = f"automation/requests/{DAY}.json"
            if mode == "noop":
                payload["test_id"] = "child-noop-01"
                path = f"automation/tests/{DAY}-child-noop-01.json"
            self.assertEqual(gate.validate_request(path, json.dumps(payload), DAY), payload)

    def test_invalid_inputs_fail_closed(self):
        base = {"version": 1, "date": DAY, "mode": "daily"}
        for value in ({**base, "version": True}, {**base, "mode": "force"},
                      {**base, "force_redeliver": True}, {**base, "date": "2026-02-30"},
                      {**base, "date": "$(touch /tmp/pwned)"}, [],
                      {**base, "date": "2026-09-30"}):
            with self.subTest(value=value), self.assertRaises((ValueError, TypeError)):
                gate.validate_request(f"automation/requests/{DAY}.json", json.dumps(value), DAY)
        for content in ('{"version":1,"version":1,"date":"2026-10-01","mode":"daily"}', "x" * 1025):
            with self.assertRaises(ValueError):
                gate.validate_request(f"automation/requests/{DAY}.json", content, DAY)
        for test_id in ("../../x", "a\nrun=true", "$(id)", "A", "a" * 41):
            with self.assertRaises(ValueError):
                gate.validate_request(f"automation/tests/{DAY}-{test_id}.json", json.dumps(
                    {"version": 1, "date": DAY, "mode": "noop", "test_id": test_id}), DAY)

    def test_push_reads_event_commit_not_branch_tip(self):
        event = {"ref": "refs/heads/main", "before": "a" * 40, "after": "b" * 40}
        calls = []
        def git(*args):
            calls.append(args)
            if args[0] == "diff":
                return f"A\tautomation/requests/{DAY}.json"
            if args[0] == "show":
                return json.dumps({"version": 1, "date": DAY, "mode": "daily"})
            return ""
        with patch.object(gate, "git", git):
            self.assertEqual(gate.request_from_push(event, DAY)["mode"], "daily")
        self.assertIn(("show", "b" * 40 + f":automation/requests/{DAY}.json"), calls)

    def test_push_refuses_updates_deletes_and_mixed_code_changes(self):
        event = {"ref": "refs/heads/main", "before": "a" * 40, "after": "b" * 40}
        for diff in (f"M\tautomation/requests/{DAY}.json", f"D\tautomation/requests/{DAY}.json",
                     f"A\tautomation/requests/{DAY}.json\nM\tmain.py", ""):
            with patch.object(gate, "git", lambda *a: diff if a[0] == "diff" else ""):
                with self.assertRaises(ValueError):
                    gate.request_from_push(event, DAY)

    def test_guards_all_automatic_and_dispatch_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "output").mkdir()
            (root / "docs").mkdir()
            (root / f"output/{DAY}-HackerNews-Top30.md").touch()
            (root / f"docs/{DAY}.json").touch()
            for project, reason in (("hn", "already-generated"), ("ai", "already-delivered")):
                for event_name in ("schedule", "workflow_dispatch", "push"):
                    with patch.object(gate, "request_from_push", return_value={"mode": "daily"}):
                        self.assertEqual(gate.decide(project, event_name, {}, root, NOW), (False, DAY, reason))
            self.assertTrue(gate.decide("ai", "workflow_dispatch", {"inputs": {"force_redeliver": "true"}}, root, NOW)[0])
            with patch.object(gate, "request_from_push", return_value={"mode": "daily", "force_redeliver": True}):
                self.assertFalse(gate.decide("ai", "push", {}, root, NOW)[0])

    def test_ambiguity_is_red_and_noop_remains_harmless(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "automation/delivery-state"
            state.mkdir(parents=True)
            (state / f"{DAY}.json").touch()
            with self.assertRaises(ValueError):
                gate.decide("ai", "schedule", {}, root, NOW)
            with patch.object(gate, "request_from_push", return_value={"mode": "noop", "test_id": "child-noop-01"}):
                self.assertEqual(gate.decide("ai", "push", {}, root, NOW), (False, DAY, "noop: child-noop-01"))

    def test_delayed_schedule_outside_window_is_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            for project in ("hn", "ai"):
                for hour in (0, 5, 22, 23):
                    self.assertFalse(gate.decide(project, "schedule", {}, Path(tmp), NOW.replace(hour=hour))[0])


if __name__ == "__main__":
    unittest.main()
