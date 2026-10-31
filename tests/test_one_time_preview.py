"""No-network checks for the user's exactly-two-post one-time approval."""
import json
import os
import pathlib
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
FIXTURE_ROOT = pathlib.Path(os.environ.get("DROPS_TEST_DATA_ROOT", str(ROOT)))
sys.path.insert(0, str(ROOT / "scripts"))
import backfill
import one_time_preview as preview


class OneTimePreviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        (self.root / "data").mkdir()
        shutil.copyfile(FIXTURE_ROOT / preview.MANIFEST, self.root / preview.MANIFEST)
        self.manifest = preview.read_manifest(self.root)
        for item in self.manifest["items"]:
            destination = self.root / item["markdown_path"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(FIXTURE_ROOT / item["markdown_path"], destination)
        (self.root / backfill.LEDGER).write_text("{}")
        (self.root / backfill.INFLIGHT).write_text("{}")

    def test_manifest_approves_only_two_exact_historical_posts(self):
        items = preview.validate(self.root, self.manifest)
        self.assertEqual([i["id"] for i in items], [r[0] for r in preview.APPROVED])
        self.assertEqual(len(items), 2)

    def test_scope_cannot_expand_or_change(self):
        for mutate in (
            lambda x: x["items"].append(dict(x["items"][0])),
            lambda x: x["items"][0].update(published_at="2026-10-23"),
            lambda x: x["items"][1].update(canonical_url="https://example.org/"),
            lambda x: x["items"][1].update(id="hamel-husain:other"),
            lambda x: x.update(authorized_at="2026-10-24"),
        ):
            other = json.loads(json.dumps(self.manifest))
            mutate(other)
            with self.subTest(other=other):
                with self.assertRaises(ValueError):
                    preview.validate(self.root, other)

    def test_markdown_cannot_be_changed_after_review(self):
        item = self.manifest["items"][0]
        path = self.root / item["markdown_path"]
        path.write_text(path.read_text() + "An unapproved revision\n")
        with self.assertRaisesRegex(ValueError, "changed since review"):
            preview.validate(self.root, self.manifest)

    def test_all_preflight_validation_before_first_send(self):
        (self.root / self.manifest["items"][1]["markdown_path"]).unlink()
        with patch.object(backfill, "deliver_one") as send:
            with self.assertRaises(FileNotFoundError):
                preview.deliver(self.root, self.manifest)
        send.assert_not_called()

    def test_only_the_two_approved_ids_are_passed_to_durable_sender(self):
        with patch.object(backfill, "deliver_one") as send:
            preview.deliver(self.root, self.manifest)
        self.assertEqual([c.args[1] for c in send.call_args_list],
                         [row[0] for row in preview.APPROVED])
        self.assertTrue(all(c.kwargs["plan"] == preview.MANIFEST for c in send.call_args_list))

    def test_held_status_never_sends(self):
        self.manifest["status"] = "held"
        with patch.object(backfill, "deliver_one") as send:
            preview.deliver(self.root, self.manifest)
        send.assert_not_called()

    def test_inflight_marker_blocks_replay(self):
        (self.root / backfill.INFLIGHT).write_text('{"id":"unknown", "sha256":"some-hash"}')
        with patch.object(backfill, "deliver_one") as send:
            with self.assertRaisesRegex(RuntimeError, "Unreconciled"):
                preview.deliver(self.root, self.manifest)
        send.assert_not_called()

    def test_completed_ledger_skips_second_delivery(self):
        ledger = {i["id"]: {"sha256":i["markdown_sha256"],"status":"complete"}
                  for i in self.manifest["items"]}
        (self.root / backfill.LEDGER).write_text(json.dumps(ledger))
        self.assertTrue(preview.already_completed(self.root, self.manifest))

    def test_digest_conflict_stops_both_sends(self):
        item = self.manifest["items"][1]
        (self.root / backfill.LEDGER).write_text(json.dumps({
            item["id"]: {"sha256": "0"*64, "status": "complete"}}))
        with patch.object(backfill, "deliver_one") as send:
            with self.assertRaisesRegex(RuntimeError, "reconciliation"):
                preview.deliver(self.root, self.manifest)
        send.assert_not_called()


if __name__ == "__main__":
    unittest.main()
