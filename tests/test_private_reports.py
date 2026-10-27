"""Offline private report deduplication and uncertain-delivery safeguards."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import deliver_private_reports as reports


class PrivateReportsTests(unittest.TestCase):
    def test_completed_receipt_needs_every_message_id(self):
        record = {"sha256": "abc", "status": "complete", "total": 2,
                  "messages": [{"index": 0, "message_id": "one"},
                               {"index": 1, "message_id": "two"}]}
        self.assertTrue(reports.valid_complete(record, "abc"))
        self.assertFalse(reports.valid_complete(record, "different"))
        self.assertFalse(reports.valid_complete({**record, "messages": record["messages"][:1]}, "abc"))
        self.assertFalse(reports.valid_complete({**record, "status": "uncertain"}, "abc"))

    def test_skip_identical_complete_report_and_refuse_changed_digest(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            path = root / "reports/general/my-task/2026-10-27.md"
            path.parent.mkdir(parents=True)
            path.write_text("# Report\n", encoding="utf-8")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            identifier = "scheduled-report:general/my-task/2026-10-27"
            ledger_path = root / reports.LEDGER
            ledger_path.parent.mkdir()
            ledger_path.write_text(json.dumps({
                identifier: {"sha256": digest, "status": "complete", "total": 1,
                             "messages": [{"index": 0, "message_id": "123"}]}
            }))
            self.assertEqual(reports.pending(root), [])
            path.write_text("# Changed!\n")
            with self.assertRaisesRegex(RuntimeError, "Unreconciled"):
                reports.pending(root)

    def test_existing_inflight_blocks_all_sends(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "data").mkdir()
            (root / reports.INFLIGHT).write_text('{"id":"unknown"}')
            with patch.object(reports, "checkpoint") as checkpoint, \
                 patch.object(reports.subprocess, "run") as send:
                with self.assertRaisesRegex(RuntimeError, "in-flight marker"):
                    reports.run(root)
                checkpoint.assert_not_called()
                send.assert_not_called()

    def test_dry_run_never_requires_webhook_or_sends(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            path = root / "reports/finance/weekly/2026-10-27.md"
            path.parent.mkdir(parents=True)
            path.write_text("# Finance report", encoding="utf-8")
            with patch.object(reports, "checkpoint") as checkpoint, \
                 patch.object(reports.subprocess, "run") as send:
                reports.run(root, dry_run=True)
                checkpoint.assert_not_called()
                send.assert_not_called()


if __name__ == "__main__":
    unittest.main()
