"""Focused offline checks: two historical refs, private paths, receipts, fail-closed sends."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import backfill
import deliver_private_reports
import migrate_private_data as migration
import private_repo


def receipt(text, message_id):
    return {"sha256": hashlib.sha256(text).hexdigest(), "status": "complete",
            "total": 1, "messages": [{"index": 0, "message_id": message_id}]}


def save(root, rel, payload):
    file = root / rel
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_bytes(payload if isinstance(payload, bytes) else payload.encode())
    return file


def save_json(root, rel, payload):
    return save(root, rel, json.dumps(payload, ensure_ascii=False) + "\n")


def commit_fixture(root):
    subprocess.run(["git", "init", "-q", str(root)], check=True, capture_output=True)
    for key, value in (("user.name", "Fixture"), ("user.email", "fixture@example.invalid")):
        subprocess.run(["git", "-C", str(root), "config", key, value], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(root), "add", "."], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "immutable historical fixture"],
                   check=True, capture_output=True)


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.news = self.base / "public-main"
        self.reports = self.base / "public-report-feed"
        self.private = self.base / "private-main"
        for p in (self.news, self.reports, self.private):
            p.mkdir()
        self.article = b"---\nid: test-news\n---\n\n# Korean news\n"
        self.report = b"# Finance report\n\nOriginal exact bytes.\n"
        save(self.news, "articles/source/2026-10-27.md", self.article)
        save_json(self.news, "data/discord-deliveries.json",
                  {"news:id": receipt(self.article, "news-discord-123")})
        save_json(self.news, "data/monitor-state.json", {"monitoring_started_at": "2026-10-20T00:00:00Z"})
        save_json(self.news, "data/reviewed-approvals.json", {"approved": ["news:id"]})
        save_json(self.news, "sources.json", {"sources": ["source"]})
        save(self.reports, "reports/finance/example/2026-10-27.md", self.report)
        save_json(self.reports, "data/discord-report-deliveries.json",
                  {"scheduled-report:finance/example/2026-10-27": receipt(self.report, "report-discord-321")})
        save_json(self.private, "data/discord-report-deliveries.json",
                  {"scheduled-report:finance/earlier/2026-10-26": receipt(b"prior", "existing-id")})
        save_json(self.private, "data/discord-report-inflight.json", {})
        commit_fixture(self.news)
        commit_fixture(self.reports)

    def test_sources_copied_identically_receipts_merged_and_idempotent(self):
        original_news = (self.news / migration.ARTICLE_LEDGER).read_bytes()
        original_report = (self.reports / migration.REPORT_LEDGER).read_bytes()
        migration.migrate(self.news, self.reports, self.private)
        for original, destination in ((self.news / "articles/source/2026-10-27.md",
                                        self.private / "articles/source/2026-10-27.md"),
                                       (self.reports / "reports/finance/example/2026-10-27.md",
                                        self.private / "reports/finance/example/2026-10-27.md"),
                                       (self.news / "data/reviewed-approvals.json",
                                        self.private / "data/reviewed-approvals.json")):
            self.assertEqual(hashlib.sha256(original.read_bytes()).hexdigest(),
                             hashlib.sha256(destination.read_bytes()).hexdigest())
        self.assertEqual((self.private / migration.ARCHIVE_ARTICLE).read_bytes(), original_news)
        self.assertEqual((self.private / migration.ARCHIVE_REPORT).read_bytes(), original_report)
        ledger = json.loads((self.private / migration.REPORT_LEDGER).read_text())
        self.assertEqual(len(ledger), 2)
        self.assertEqual(ledger["scheduled-report:finance/example/2026-10-27"]["messages"][0]["message_id"],
                         "report-discord-321")
        self.assertEqual(ledger["scheduled-report:finance/earlier/2026-10-26"]["messages"][0]["message_id"],
                         "existing-id")
        migration.migrate(self.news, self.reports, self.private, verify_only=True)
        migration.migrate(self.news, self.reports, self.private)
        self.assertEqual((self.news / migration.ARTICLE_LEDGER).read_bytes(), original_news)

    def test_divergent_private_file_refuses_before_any_write(self):
        save(self.private, "articles/source/2026-10-27.md", b"modified article")
        with self.assertRaisesRegex(RuntimeError, "content conflict"):
            migration.migrate(self.news, self.reports, self.private)
        self.assertFalse((self.private / "reports/finance/example/2026-10-27.md").exists())

    def test_report_marker_refuses_migration(self):
        save_json(self.private, "data/discord-report-inflight.json", {"id": "unresolved"})
        with self.assertRaisesRegex(RuntimeError, "in-flight"):
            migration.migrate(self.news, self.reports, self.private)
        self.assertFalse((self.private / "reports/finance/example/2026-10-27.md").exists())

    def test_missing_or_code_checkout_data_root_rejected(self):
        root = Path(__file__).resolve().parents[1]
        with patch.dict(os.environ, {}, clear=True), self.assertRaisesRegex(RuntimeError, "DROPS_DATA_ROOT"):
            private_repo.require_private_data_root(root)
        with patch.dict(os.environ, {"DROPS_DATA_ROOT": str(root)}), self.assertRaisesRegex(RuntimeError, "separate"):
            private_repo.require_private_data_root(root)
        with patch.dict(os.environ, {"DROPS_DATA_ROOT": str(self.private)}):
            self.assertEqual(private_repo.require_private_data_root(root), self.private.resolve())

    def test_missing_auth_and_rest_transport_block_before_writing(self):
        with patch.dict(os.environ, {"GH_TOKEN": ""}):
            with self.assertRaisesRegex(RuntimeError, "Missing GH_TOKEN"):
                private_repo.api(private_repo.DEFAULT_REPO, "git/ref/heads/main")
        with patch.dict(os.environ, {"DROPS_DATA_ROOT": str(self.private), "DROPS_PRIVATE_REST": "0"}):
            with self.assertRaisesRegex(RuntimeError, "private REST transport"):
                backfill.persist(self.private, {}, {"id": "blocked"})

    def test_failed_presend_checkpoint_never_invokes_report_sender(self):
        report = save(self.private, "reports/finance/example/2026-10-27.md", self.report)
        self.assertTrue(report.is_file())
        with patch.dict(os.environ, {"DISCORD_WEBHOOK_URL_FINANCE": "https://example.invalid/webhook"}), \
             patch.object(deliver_private_reports, "checkpoint", side_effect=RuntimeError("auth refused")), \
             patch.object(deliver_private_reports.subprocess, "run") as sender:
            with self.assertRaisesRegex(RuntimeError, "auth refused"):
                deliver_private_reports.run(self.private)
            sender.assert_not_called()

    def test_failed_article_checkpoint_never_invokes_sender(self):
        article = save(self.private, "articles/source/2026-10-27.md", self.article)
        digest = hashlib.sha256(self.article).hexdigest()
        sender = Mock()
        with self.assertRaisesRegex(RuntimeError, "checkpoint refused"):
            backfill.deliver_one(self.private, "news:id", article, digest,
                                 checkpoint=Mock(side_effect=RuntimeError("checkpoint refused")),
                                 invoke=sender)
        sender.assert_not_called()


if __name__ == "__main__":
    unittest.main()
