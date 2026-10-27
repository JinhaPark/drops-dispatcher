"""Narrow static and offline checks for one-shot Discord 3-route proof."""
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import verify_discord_routes as verifier
import backfill
import deliver_private_reports as reports


class RouteProbeTests(unittest.TestCase):
    def test_three_fixed_ids_and_independent_webhooks(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            test_file, ids = verifier.build_fixture(root)
            self.assertEqual(test_file.read_text(), verifier.TEXT["ai"])
            self.assertEqual(len(ids), 3)
            self.assertIn(verifier.ARTICLE_ID, ids)
            self.assertIn("scheduled-report:finance/system-route-check/2026-10-27", ids)
            self.assertIn("scheduled-report:general/system-route-check/2026-10-27", ids)

    def test_unresolved_marker_prevents_posts(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            (root / "data").mkdir()
            (root / backfill.INFLIGHT).write_text(json.dumps({"id":"ambiguous"}))
            with self.assertRaisesRegex(RuntimeError, "in-flight"):
                verifier.check_no_active_sends(root, {})

    def test_existing_incomplete_probe_blocks_replay(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            (root / "data").mkdir()
            ledger = {verifier.ARTICLE_ID: {"status":"uncertain","sha256":"x"}}
            (root / backfill.LEDGER).write_text(json.dumps(ledger))
            with self.assertRaisesRegex(RuntimeError, "Unresolved"):
                verifier.check_no_active_sends(root, {verifier.ARTICLE_ID:"x"})


if __name__ == "__main__":
    unittest.main()
