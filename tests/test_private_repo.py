"""Offline regression checks for the GitHub REST private-data transport."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import private_repo


class PrivateRepoTests(unittest.TestCase):
    def test_rejects_other_repositories(self):
        with self.assertRaises(ValueError):
            private_repo.api("JinhaPark/drops-dispatcher", "git/ref/heads/main")

    def test_pull_requires_consistent_verified_snapshot(self):
        with tempfile.TemporaryDirectory() as d:
            entries = {
                "articles/x.md": {"type": "blob", "sha": "a", "mode": "100644"},
                "data/discord-deliveries.json": {"type": "blob", "sha": "b", "mode": "100644"},
            }
            with patch.object(private_repo, "ref_head", side_effect=["head", "head"]), \
                 patch.object(private_repo, "tree_snapshot", return_value=("tree", entries)), \
                 patch.object(private_repo, "blob_bytes", side_effect=lambda r, s: {"a": b"# Safe", "b": b"{}"}[s]):
                private_repo.pull("JinhaPark/drops", "main", Path(d), ("articles", "data"))
            self.assertEqual((Path(d) / "articles/x.md").read_bytes(), b"# Safe")
            self.assertEqual((Path(d) / "data/discord-deliveries.json").read_bytes(), b"{}")

    def test_snapshot_change_is_fatal(self):
        with tempfile.TemporaryDirectory() as d:
            entries = {"articles/x.md": {"type": "blob", "sha": "a", "mode": "100644"}}
            with patch.object(private_repo, "ref_head", side_effect=["head", "newhead"]), \
                 patch.object(private_repo, "tree_snapshot", return_value=("tree", entries)), \
                 patch.object(private_repo, "blob_bytes", return_value=b"# Original"):
                with self.assertRaisesRegex(RuntimeError, "changed during snapshot"):
                    private_repo.pull("JinhaPark/drops", "main", Path(d), ("articles",))

    def test_unreconciled_remote_marker_prevents_any_api_write(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "data").mkdir()
            (root / "data/discord-deliveries.json").write_text("{}")
            with patch.object(private_repo, "ref_head", return_value="head"), \
                 patch.object(private_repo, "tree_snapshot", return_value=("tree", {})), \
                 patch.object(private_repo, "_remote_json", return_value={"id": "uncertain"}), \
                 patch.object(private_repo, "api") as api:
                with self.assertRaisesRegex(RuntimeError, "Unreconciled"):
                    private_repo.persist_state(
                        root, {}, {"id": "next"}, "data/discord-deliveries.json",
                        "data/discord-backfill-inflight.json", lambda a, b: {**a, **b})
                api.assert_not_called()

    def test_atomic_checkpoint_commit_and_remote_verification(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "data").mkdir()
            ledger = {"issue1": {"sha256": "abc", "status": "complete", "total": 1, "messages": [{"index": 0, "message_id": "123"}]}}
            (root / "data/discord-deliveries.json").write_text(json.dumps(ledger))
            responses = iter([{"sha": "blob-ledger"}, {"sha": "blob-marker"},
                              {"sha": "tree-commit"}, {"sha": "new-head"}, {}])
            def fake_api(repo, endpoint, method="GET", payload=None):
                self.assertNotEqual(method, "DELETE")
                return next(responses)
            marker = {"id": "issue1", "sha256": "abc"}
            with patch.object(private_repo, "ref_head", side_effect=["old-head", "new-head"]), \
                 patch.object(private_repo, "tree_snapshot", side_effect=[("old-tree", {}), ("new-tree", {"verified": {}})]), \
                 patch.object(private_repo, "_remote_json", side_effect=[{}, {}, marker, ledger]), \
                 patch.object(private_repo, "api", side_effect=fake_api) as api:
                private_repo.persist_state(root, {}, marker,
                    "data/discord-deliveries.json", "data/discord-backfill-inflight.json",
                    lambda a, b: {**a, **b})
            self.assertEqual(json.loads((root / "data/discord-backfill-inflight.json").read_text()), marker)
            self.assertEqual(api.call_count, 5)
            self.assertEqual(api.call_args_list[-1].args[2], "PATCH")
            self.assertIs(api.call_args_list[-1].args[3]["force"], False)


if __name__ == "__main__":
    unittest.main()
