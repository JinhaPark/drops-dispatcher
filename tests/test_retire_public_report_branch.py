"""Focused, offline safeguards for retiring the public legacy report branch."""
import importlib.util
import pathlib
import unittest

TARGET = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "retire_public_report_branch.py"
spec = importlib.util.spec_from_file_location("retire_public_report_branch", TARGET)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class MigrationParityTests(unittest.TestCase):
    def setUp(self):
        self.old_reports = {f"reports/finance/old-{i}.md": f"report-{i}" for i in range(10)}
        self.old_news = {f"articles/source/old-{i}.md": f"article-{i}" for i in range(137)}
        self.old_reports["data/discord-report-deliveries.json"] = "original-report-ledger"
        self.old_news["data/discord-deliveries.json"] = "original-article-ledger"
        self.private = {
            **self.old_reports, **self.old_news,
            module.ARCHIVED_REPORTS: "original-report-ledger",
            module.ARCHIVED_ARTICLES: "original-article-ledger",
            "data/discord-backfill-inflight.json": "checkpoint-articles",
            "data/discord-report-inflight.json": "checkpoint-reports",
        }
        self.public = {"scripts/deliver_articles.py": "safe-code"}

    def verify(self):
        return module.verify_migration(
            self.old_reports, self.old_news, self.private, self.public)

    def test_exact_old_content_preserved(self):
        self.assertEqual(self.verify(), (137, 10))

    def test_missing_historical_report_is_blocked(self):
        del self.private["reports/finance/old-0.md"]
        with self.assertRaises(RuntimeError):
            self.verify()

    def test_modified_historical_article_is_blocked(self):
        self.private["articles/source/old-19.md"] = "different-sha"
        with self.assertRaises(RuntimeError):
            self.verify()

    def test_unarchived_original_receipt_is_blocked(self):
        del self.private[module.ARCHIVED_REPORTS]
        with self.assertRaises(RuntimeError):
            self.verify()

    def test_public_main_with_private_data_is_blocked(self):
        self.public["data/discord-deliveries.json"] = "should-not-be-public"
        with self.assertRaises(RuntimeError):
            self.verify()

    def test_missing_active_checkpoint_is_blocked(self):
        del self.private["data/discord-backfill-inflight.json"]
        with self.assertRaises(RuntimeError):
            self.verify()

    def test_incomplete_source_count_is_blocked(self):
        del self.old_news["articles/source/old-0.md"]
        with self.assertRaises(RuntimeError):
            self.verify()


if __name__ == "__main__":
    unittest.main()
