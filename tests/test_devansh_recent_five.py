"""Offline regressions for exactly five Devansh historical posts (four public, one paid)."""
import copy
import json
import pathlib
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import backfill
import devansh_recent_five as devansh
import deliver_articles


class DevanshRecentFiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        (self.root / "scripts").mkdir()
        (self.root / "data").mkdir()
        shutil.copyfile(ROOT / devansh.MANIFEST, self.root / devansh.MANIFEST)
        self.manifest = devansh.read_manifest(self.root)
        for item in self.manifest["items"]:
            if item["status"] != "ready":
                continue
            target = self.root / item["markdown_path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / item["markdown_path"], target)
        (self.root / backfill.LEDGER).write_text("{}\n")
        (self.root / backfill.INFLIGHT).write_text("{}\n")

    def test_exact_five_archive_items_and_paid_hold(self):
        items = devansh.validate(self.root, self.manifest)
        self.assertEqual([i["id"] for i in items],
                         [devansh.expected_row(*row)["id"] for row in devansh.APPROVED])
        self.assertEqual([i["status"] for i in items],
                         ["ready", "ready", "held", "ready", "ready"])
        self.assertEqual(len(items), 5)
        self.assertEqual(items[2]["reason"], "paywalled_full_text_unavailable")
        self.assertFalse((self.root / items[2]["markdown_path"]).exists())

    def test_reviewed_article_contracts_and_word_count(self):
        for item in devansh.validate(self.root, self.manifest):
            if item["status"] != "ready":
                continue
            text = (self.root / item["markdown_path"]).read_text()
            fields, body = backfill.frontmatter(text)
            paragraphs = [p.strip() for p in body.strip().split("\n\n") if p.strip()]
            self.assertEqual(fields["editorial_version"], "ko-300words-v1")
            self.assertEqual(len(paragraphs), 6)
            self.assertGreaterEqual(len(" ".join(paragraphs[2:]).split()), 250)
            self.assertLessEqual(len(" ".join(paragraphs[2:]).split()), 350)

    def test_never_widen_historical_authorization(self):
        edits = [
            lambda p: p["items"].append(copy.deepcopy(p["items"][0])),
            lambda p: p["items"][0].update(published_at="2026-10-01"),
            lambda p: p["items"][0].update(canonical_url="https://example.com/"),
            lambda p: p["items"][4].update(id="devansh-ai-made-simple:other"),
            lambda p: p.update(authorized_at="2026-10-25T00:00:00Z"),
            lambda p: p["items"].reverse(),
        ]
        for edit in edits:
            other = copy.deepcopy(self.manifest)
            edit(other)
            with self.subTest(edit=edit):
                with self.assertRaises(ValueError):
                    devansh.validate(self.root, other)

    def test_paid_post_cannot_be_changed_to_ready_without_complete_review(self):
        item = copy.deepcopy(self.manifest)
        item["items"][2]["status"] = "ready"
        with self.assertRaises(ValueError):
            devansh.validate(self.root, item)
        item = copy.deepcopy(self.manifest)
        item["items"][2]["markdown_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            devansh.validate(self.root, item)

    def test_changed_markdown_blocks_entire_approval_before_any_send(self):
        last = next(i for i in self.manifest["items"] if i["status"] == "ready")
        article = self.root / last["markdown_path"]
        article.write_text(article.read_text() + "\nUnreviewed edit")
        with patch.object(backfill, "deliver_one") as sender:
            with self.assertRaisesRegex(ValueError, "changed since review"):
                devansh.deliver(self.root, self.manifest)
            sender.assert_not_called()

    def test_four_reviewed_items_only_are_sent_in_chronological_order(self):
        with patch.object(backfill, "deliver_one") as sender:
            devansh.deliver(self.root, self.manifest)
        intended = [x["id"] for x in self.manifest["items"] if x["status"] == "ready"]
        self.assertEqual([call.args[1] for call in sender.call_args_list], intended)
        self.assertTrue(all(call.kwargs["plan"] == devansh.MANIFEST
                            for call in sender.call_args_list))

    def test_global_held_status_sends_nothing(self):
        self.manifest["status"] = "held"
        with patch.object(backfill, "deliver_one") as sender:
            devansh.deliver(self.root, self.manifest)
        sender.assert_not_called()

    def test_unreconciled_marker_blocks_all_replays(self):
        (self.root / backfill.INFLIGHT).write_text('{"id":"some_previous_post"}')
        with patch.object(backfill, "deliver_one") as sender:
            with self.assertRaisesRegex(RuntimeError, "Unreconciled"):
                devansh.deliver(self.root, self.manifest)
            sender.assert_not_called()

    def test_partial_and_complete_ledger_idempotency(self):
        items = [i for i in self.manifest["items"] if i["status"] == "ready"]
        ledger = {item["id"]: {"sha256": item["markdown_sha256"], "status": "complete"}
                  for item in items[:2]}
        (self.root / backfill.LEDGER).write_text(json.dumps(ledger))
        with patch.object(backfill, "deliver_one") as sender:
            devansh.deliver(self.root, self.manifest)
        self.assertEqual([c.args[1] for c in sender.call_args_list],
                         [i["id"] for i in items[2:]])
        self.assertFalse(devansh.already_completed(self.root, self.manifest))
        ledger.update({item["id"]: {"sha256": item["markdown_sha256"], "status": "complete"}
                       for item in items[2:]})
        (self.root / backfill.LEDGER).write_text(json.dumps(ledger))
        self.assertTrue(devansh.already_completed(self.root, self.manifest))
        with patch.object(backfill, "deliver_one") as sender:
            devansh.deliver(self.root, self.manifest)
        sender.assert_not_called()

    def test_digest_conflict_is_detected_pre_send(self):
        item = next(i for i in self.manifest["items"] if i["status"] == "ready")
        (self.root / backfill.LEDGER).write_text(
            json.dumps({item["id"]: {"sha256": "0" * 64, "status": "complete"}}))
        with patch.object(backfill, "deliver_one") as sender:
            with self.assertRaisesRegex(RuntimeError, "reconciliation"):
                devansh.deliver(self.root, self.manifest)
        sender.assert_not_called()

    def test_dispatch_integration_sends_reviewed_backfill_before_live(self):
        with patch.object(deliver_articles, "__file__",
                          str(self.root / "scripts/deliver_articles.py")), \
             patch.object(backfill, "deliver_one") as sender:
            deliver_articles.main()
        self.assertEqual([c.args[1] for c in sender.call_args_list],
                         [i["id"] for i in self.manifest["items"] if i["status"] == "ready"])


if __name__ == "__main__":
    unittest.main()
