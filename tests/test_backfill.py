import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import backfill as b


def record(message="123", status="complete"):
    return {"sha256": "a" * 64, "status": status,
            "messages": [{"index": 0, "message_id": message}], "total": 1}


class LedgerTests(unittest.TestCase):
    def test_manifest_requires_exact_numeric_continuity(self):
        manifest = {"status": "held", "source_id": "artificial-engineering", "range": [1, 64],
                    "editions": [{"edition_number": n, "status": "pending"} for n in range(1, 65)]}
        b.validate_manifest(pathlib.Path('.'), manifest)
        manifest['editions'][0], manifest['editions'][1] = manifest['editions'][1], manifest['editions'][0]
        with self.assertRaises(ValueError):
            b.validate_manifest(pathlib.Path('.'), manifest)

    def test_historical_scope_excludes_existing_feeds(self):
        self.assertTrue(b.is_backfill_id("artificial-engineering:edition-1"))
        self.assertTrue(b.is_backfill_id("artificial-engineering:edition-64"))
        self.assertFalse(b.is_backfill_id("artificial-engineering:edition-65"))
        self.assertFalse(b.is_backfill_id("elevate:agentic-verification"))

    def test_preserves_unrelated_successes(self):
        self.assertEqual(b.merge_ledgers({"old": record()}, {"new": record()}),
                         {"old": record(), "new": record()})

    def test_conflicting_ids_and_uncertainty_fail_closed(self):
        for other in (record("456"), record(status="uncertain")):
            with self.assertRaises(RuntimeError):
                b.merge_ledgers({"a": record()}, {"a": other})

    def test_remote_complete_cannot_regress(self):
        partial = record(status="pending")
        partial["messages"] = []
        self.assertEqual(b.merge_ledgers({"a": record()}, {"a": partial})["a"], record())


class OrderingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        (self.root / "data").mkdir()
        (self.root / b.LEDGER).write_text("{}")
        self.items = [{"edition_number": n, "status": "ready", "markdown_path": f"{n}.md"} for n in range(1, 4)]
        self.events = []

    def checkpoint(self, root, old, new):
        self.events.append(("checkpoint", new.get("id")))

    def invoke(self, args, cwd):
        item_id = args[args.index("--id") + 1]
        self.events.append(("send", item_id))
        state = b.read_json(self.root / b.LEDGER)
        state[item_id] = {**record(), "sha256": b.sha(item_id)}
        (self.root / b.LEDGER).write_text(json.dumps(state))
        return SimpleNamespace(returncode=0)

    def run_delivery(self, checkpoint=None, invoke=None):
        with patch.object(b, "validate_manifest", return_value=self.items), patch.object(
            b, "validate_article", side_effect=lambda root, item: (str(item["edition_number"]), str(item["edition_number"]))
        ):
            b.deliver(self.root, {"status": "active"}, checkpoint or self.checkpoint, invoke or self.invoke)

    def test_checkpoint_before_post_and_after_each_edition(self):
        self.run_delivery()
        self.assertEqual(self.events, [(op, n) for n in ("1", "2", "3")
                                      for op, n in (("checkpoint", n), ("send", n), ("checkpoint", None))])

    def test_missing_edition_stops_later_send(self):
        self.items[1]["status"] = "pending"
        self.run_delivery()
        self.assertEqual([e for e in self.events if e[0] == "send"], [("send", "1")])

    def test_inflight_blocks_all_post_calls(self):
        (self.root / b.INFLIGHT).write_text('{"id":"1"}')
        with self.assertRaises(RuntimeError):
            self.run_delivery()
        self.assertFalse(self.events)

    def test_persist_failure_prevents_next_edition(self):
        def fail_after_send(root, old, new):
            self.checkpoint(root, old, new)
            if not new:
                raise RuntimeError("remote push rejected")
        with self.assertRaises(RuntimeError):
            self.run_delivery(checkpoint=fail_after_send)
        self.assertEqual([e for e in self.events if e[0] == "send"], [("send", "1")])

    def test_failed_send_preserves_marker_and_stops(self):
        with self.assertRaises(RuntimeError):
            self.run_delivery(invoke=lambda *a, **kw: SimpleNamespace(returncode=1))
        self.assertEqual(self.events, [("checkpoint", "1"), ("checkpoint", "1")])

    def test_complete_entry_is_skipped_without_resend(self):
        (self.root / b.LEDGER).write_text(json.dumps({"1": {**record(), "sha256": b.sha("1")}}))
        self.run_delivery()
        self.assertEqual([e for e in self.events if e[0] == "send"], [("send", "2"), ("send", "3")])

    def test_finished_backfill_releases_future_live_feed(self):
        items = [{"edition_number": 1, "status": "ready", "markdown_sha256": "a" * 64}]
        with patch.object(b, "validate_manifest", return_value=items):
            self.assertFalse(b.already_completed(self.root, {"status": "active"}))
            (self.root / b.LEDGER).write_text(json.dumps({"artificial-engineering:edition-1": record()}))
            self.assertTrue(b.already_completed(self.root, {"status": "active"}))
            (self.root / b.INFLIGHT).write_text('{"id":"unknown"}')
            self.assertFalse(b.already_completed(self.root, {"status": "active"}))


class GitCheckpointTests(unittest.TestCase):
    def test_remote_concurrent_file_and_ledger_are_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            remote, runner, other = (base / x for x in ("remote.git", "runner", "other"))
            def run(*args, cwd=base):
                return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout
            run("init", "--bare", "--initial-branch=main", str(remote))
            run("clone", str(remote), str(runner))
            for path in (runner,):
                run("config", "user.name", "Test", cwd=path)
                run("config", "user.email", "test@example.invalid", cwd=path)
            (runner / "data").mkdir()
            (runner / b.LEDGER).write_text(json.dumps({"old": record()}))
            run("add", ".", cwd=runner)
            run("commit", "-m", "initial", cwd=runner)
            run("push", "origin", "main", cwd=runner)
            run("clone", str(remote), str(other))
            run("config", "user.name", "Test", cwd=other)
            run("config", "user.email", "test@example.invalid", cwd=other)
            (other / "unrelated.txt").write_text("keep me")
            (other / b.LEDGER).write_text(json.dumps({"old": record(), "concurrent": record()}))
            run("add", ".", cwd=other)
            run("commit", "-m", "concurrent", cwd=other)
            run("push", "origin", "main", cwd=other)
            marker = {"id": "new"}
            b.persist(runner, {}, marker)
            state = b.read_json(runner / b.LEDGER)
            state["new"] = record()
            (runner / b.LEDGER).write_text(json.dumps(state))
            b.persist(runner, marker, {})
            self.assertEqual(run("show", "main:unrelated.txt", cwd=remote), "keep me")
            saved = json.loads(run("show", f"main:{b.LEDGER}", cwd=remote))
            self.assertEqual(set(saved), {"old", "concurrent", "new"})
            self.assertEqual(json.loads(run("show", f"main:{b.INFLIGHT}", cwd=remote)), {})


if __name__ == "__main__":
    unittest.main()
