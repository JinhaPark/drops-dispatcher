"""Offline regression tests for live Discord remote checkpoints. No webhook calls."""
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
import deliver_articles as dispatcher


def complete(text, *ids):
    return {"sha256": b.sha(text), "status": "complete", "total": len(ids),
            "messages": [{"index": index, "message_id": item}
                         for index, item in enumerate(ids)]}


def run_git(root, *args):
    return subprocess.run(["git", *args], cwd=root, check=True, text=True,
                          capture_output=True).stdout.strip()


class RemoteCheckpointTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = pathlib.Path(self.temp.name)
        self.remote = self.base / "remote.git"
        self.runner = self.base / "runner"
        run_git(self.base, "init", "--bare", "--initial-branch=main", str(self.remote))
        run_git(self.base, "clone", str(self.remote), str(self.runner))
        self.configure(self.runner)
        (self.runner / "data").mkdir()
        self.write_json(self.runner, b.LEDGER, {"historical": complete("old", "H0")})
        self.write_json(self.runner, b.INFLIGHT, {})
        for n in (1, 2):
            (self.runner / f"article-{n}.md").write_text(f"article-{n}", encoding="utf-8")
        run_git(self.runner, "add", ".")
        run_git(self.runner, "commit", "-m", "baseline")
        run_git(self.runner, "push", "origin", "main")

    def configure(self, root):
        run_git(root, "config", "user.name", "Checkpoint Test")
        run_git(root, "config", "user.email", "test@example.invalid")

    def clone(self, label):
        target = self.base / label
        run_git(self.base, "clone", str(self.remote), str(target))
        self.configure(target)
        return target

    def write_json(self, root, filename, value):
        path = root / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")

    def remote_json(self, filename):
        return json.loads(run_git(self.remote, "show", f"main:{filename}"))

    def invoke_success(self, *ids):
        def invoke(argv, cwd):
            item_id = argv[argv.index("--id") + 1]
            text = pathlib.Path(argv[argv.index("--file") + 1]).read_text()
            ledger = b.read_json(cwd / b.LEDGER)
            ledger[item_id] = complete(text, *ids)
            self.write_json(cwd, b.LEDGER, ledger)
            return SimpleNamespace(returncode=0)
        return invoke

    def deliver(self, root, n, invoke=None, checkpoint=b.persist):
        return b.deliver_one(root, f"live:{n}", root / f"article-{n}.md",
                             b.sha(f"article-{n}"), checkpoint=checkpoint,
                             invoke=invoke or self.invoke_success(f"M{n}"),
                             plan="live")

    def test_every_article_commits_remote_before_next_post(self):
        events = []

        def invoke(argv, cwd):
            item_id = argv[argv.index("--id") + 1]
            self.assertEqual(self.remote_json(b.INFLIGHT)["id"], item_id)
            events.append(item_id)
            return self.invoke_success(f"msg-{len(events)}")(argv, cwd)

        self.deliver(self.runner, 1, invoke)
        self.assertEqual(self.remote_json(b.INFLIGHT), {})
        self.assertIn("live:1", self.remote_json(b.LEDGER))
        self.deliver(self.runner, 2, invoke)
        self.assertEqual(events, ["live:1", "live:2"])
        self.assertEqual(set(self.remote_json(b.LEDGER)),
                         {"historical", "live:1", "live:2"})
        self.assertEqual(self.remote_json(b.INFLIGHT), {})

    def test_runner_lost_after_posts_before_final_push_blocks_replay(self):
        self.deliver(self.runner, 1)
        marker = {"id": "live:2", "sha256": b.sha("article-2"),
                  "run_id": "local", "plan": "live"}
        b.persist(self.runner, {}, marker)
        self.invoke_success("M2")(["--file", str(self.runner / "article-2.md"),
                                   "--id", "live:2"], self.runner)
        # Simulate process/runner disappearing without its final remote save.
        restarted = self.clone("new-runner")
        calls = []
        with self.assertRaisesRegex(RuntimeError, "in-flight"):
            self.deliver(restarted, 2, invoke=lambda *a, **kw: calls.append(1))
        self.assertEqual(calls, [])
        self.assertEqual(self.remote_json(b.INFLIGHT), marker)
        self.assertIn("live:1", self.remote_json(b.LEDGER))
        self.assertNotIn("live:2", self.remote_json(b.LEDGER))

    def test_post_send_push_failure_retains_remote_fence_and_local_ids(self):
        native_run = subprocess.run
        deny_push = False

        def fake_run(args, *pos, **kw):
            if deny_push and args[:2] == ["git", "push"]:
                return SimpleNamespace(returncode=1, stdout="", stderr="simulated rejection")
            return native_run(args, *pos, **kw)

        def invoke(argv, cwd):
            nonlocal deny_push
            result = self.invoke_success("M1a", "M1b")(argv, cwd)
            deny_push = True
            return result

        with patch.object(b.subprocess, "run", side_effect=fake_run):
            with self.assertRaisesRegex(RuntimeError, "Could not persist ledger"):
                self.deliver(self.runner, 1, invoke)
        self.assertEqual(self.remote_json(b.INFLIGHT)["id"], "live:1")
        self.assertNotIn("live:1", self.remote_json(b.LEDGER))
        self.assertEqual([x["message_id"] for x in
                          b.read_json(self.runner / b.LEDGER)["live:1"]["messages"]],
                         ["M1a", "M1b"])
        restarted = self.clone("after-push-error")
        with self.assertRaisesRegex(RuntimeError, "in-flight"):
            self.deliver(restarted, 1, lambda *a, **kw: self.fail("POST repeated"))

    def test_partial_send_keeps_each_successful_chunk_and_stops(self):
        def partial(argv, cwd):
            ledger = b.read_json(cwd / b.LEDGER)
            ledger["live:1"] = {"sha256": b.sha("article-1"), "status": "uncertain",
                                "total": 2,
                                "messages": [{"index": 0, "message_id": "chunk-0"}]}
            self.write_json(cwd, b.LEDGER, ledger)
            return SimpleNamespace(returncode=1)

        with self.assertRaisesRegex(RuntimeError, "incomplete or uncertain"):
            self.deliver(self.runner, 1, partial)
        record = self.remote_json(b.LEDGER)["live:1"]
        self.assertEqual(record["status"], "uncertain")
        self.assertEqual(record["messages"], [{"index": 0, "message_id": "chunk-0"}])
        self.assertEqual(self.remote_json(b.INFLIGHT)["id"], "live:1")
        restarted = self.clone("after-partial")
        with self.assertRaisesRegex(RuntimeError, "in-flight"):
            self.deliver(restarted, 2, lambda *a, **kw: self.fail("next post attempted"))

    def test_concurrent_main_change_is_preserved_through_checkpoint(self):
        other = self.clone("other-writer")

        def invoke(argv, cwd):
            run_git(other, "pull", "--ff-only", "origin", "main")
            (other / "unrelated.txt").write_text("concurrent changes", encoding="utf-8")
            ledger = b.read_json(other / b.LEDGER)
            ledger["another-job"] = complete("other", "X0")
            self.write_json(other, b.LEDGER, ledger)
            run_git(other, "add", ".")
            run_git(other, "commit", "-m", "unrelated concurrent changes")
            run_git(other, "push", "origin", "main")
            return self.invoke_success("M1")(argv, cwd)

        self.deliver(self.runner, 1, invoke)
        self.assertEqual(run_git(self.remote, "show", "main:unrelated.txt"),
                         "concurrent changes")
        self.assertEqual(set(self.remote_json(b.LEDGER)),
                         {"historical", "another-job", "live:1"})
        self.assertEqual(self.remote_json(b.INFLIGHT), {})

    def test_pre_send_push_failure_blocks_post(self):
        native_run = subprocess.run
        def fake_run(args, *pos, **kw):
            if args[:2] == ["git", "push"]:
                return SimpleNamespace(returncode=1, stdout="", stderr="simulated rejection")
            return native_run(args, *pos, **kw)
        with patch.object(b.subprocess, "run", side_effect=fake_run):
            with self.assertRaisesRegex(RuntimeError, "Could not persist ledger"):
                self.deliver(self.runner, 1, lambda *a, **kw: self.fail("POST happened"))
        self.assertEqual(self.remote_json(b.INFLIGHT), {})
        self.assertNotIn("live:1", self.remote_json(b.LEDGER))

    def test_incomplete_success_record_cannot_clear_marker(self):
        def fake_success(argv, cwd):
            ledger = b.read_json(cwd / b.LEDGER)
            ledger["live:1"] = {"sha256": b.sha("article-1"), "status": "complete",
                                "total": 2, "messages": [{"index": 0, "message_id": "first"}]}
            self.write_json(cwd, b.LEDGER, ledger)
            return SimpleNamespace(returncode=0)
        with self.assertRaisesRegex(RuntimeError, "incomplete or uncertain"):
            self.deliver(self.runner, 1, fake_success)
        self.assertEqual(self.remote_json(b.INFLIGHT)["id"], "live:1")

    def test_remote_success_is_skipped_and_changed_digest_is_rejected(self):
        self.deliver(self.runner, 1)
        restarted = self.clone("no-repost")
        self.assertFalse(self.deliver(restarted, 1,
                                      lambda *a, **kw: self.fail("duplicate post")))
        with self.assertRaisesRegex(RuntimeError, "reconciliation"):
            b.deliver_one(restarted, "live:1", restarted / "article-1.md", b.sha("different"),
                          invoke=lambda *a, **kw: self.fail("revised post"))


class LiveDispatcherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        (self.root / "scripts").mkdir()
        (self.root / "articles" / "live").mkdir(parents=True)
        (self.root / "data").mkdir()
        (self.root / b.LEDGER).write_text("{}", encoding="utf-8")

    def article(self, n):
        path = self.root / "articles" / "live" / f"2026-10-23-{n}.md"
        text = (f"---\\nid: live:{n}\\nsource_id: live\\n"
                f"canonical_url: https://example.test/{n}\\nauthor: Tester\\n"
                f"published_at: 2026-10-23\\nstatus: ready\\n---\\nTitle {n}\\n")
        path.write_text(text, encoding="utf-8")
        return path

    def run_dispatch(self):
        with patch.object(dispatcher, "__file__", str(self.root / "scripts" / "deliver_articles.py")):
            dispatcher.main()

    def test_live_path_uses_shared_checkpoint_per_article(self):
        self.article(1)
        self.article(2)
        calls = []
        with patch.object(b, "deliver_one", side_effect=lambda *a, **kw: calls.append(a[2])):
            self.run_dispatch()
        self.assertEqual(len(calls), 2)
        self.assertEqual([p.name for p in calls],
                         ["2026-10-23-1.md", "2026-10-23-2.md"])

    def test_invalid_second_article_prevents_first_post(self):
        self.article(1)
        self.article(2).write_text("---\\nid: live:2\\nstatus: ready\\n---\\nBad")
        with patch.object(b, "deliver_one", side_effect=lambda *a, **kw: self.fail("POST")):
            with self.assertRaisesRegex(RuntimeError, "provenance"):
                self.run_dispatch()

    def test_uncertain_prior_article_blocks_all_new_posts(self):
        self.article(1)
        self.article(2)
        self.root.joinpath(b.LEDGER).write_text(json.dumps({
            "live:2": {"status": "uncertain", "sha256": "0" * 64}
        }))
        with patch.object(b, "deliver_one", side_effect=lambda *a, **kw: self.fail("POST")):
            with self.assertRaisesRegex(RuntimeError, "reconciliation"):
                self.run_dispatch()


if __name__ == "__main__":
    unittest.main()
