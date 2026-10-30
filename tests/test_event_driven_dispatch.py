"""Static regression checks for safe event-driven dispatcher wakeups."""
from pathlib import Path
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]


class EventDrivenDispatchTests(unittest.TestCase):
    def check_workflow(self, workflow_file, route_name, marker_file, event_type, original_cron):
        text = (ROOT / ".github/workflows" / workflow_file).read_text(encoding="utf-8")
        self.assertIn("repository_dispatch:", text)
        self.assertIn(f"types: [{event_type}]", text)
        self.assertIn(f"- '.dispatch/{marker_file}'", text)
        self.assertIn("branches: [main]", text)
        self.assertIn(f"cron: '{original_cron}'", text)
        self.assertIn("github.event_name == 'repository_dispatch'", text)
        self.assertIn("github.event_name == 'schedule'", text)
        self.assertIn("github.event_name == 'workflow_dispatch' && inputs.mode == 'deliver'", text)
        self.assertIn(f"github.event.head_commit.message == 'Wake private {route_name} dispatcher'", text)
        self.assertNotIn("github.event.head_commit.modified", text)
        self.assertNotIn("github.event.head_commit.added", text)
        self.assertIn("github.event_name == 'push'", text)
        signal = json.loads((ROOT / ".dispatch" / marker_file).read_text(encoding="utf-8"))
        self.assertEqual(signal["version"], 1)
        self.assertEqual(set(signal), {"version", "signal"})
        self.assertIsInstance(signal["signal"], str)

    def test_reports_wakeup_is_gated_and_retains_hourly_fallback(self):
        self.check_workflow(
            "report-feed.yml", "reports", "wake-reports.json",
            "drops-reports-ready", "29 * * * *")

    def test_articles_wakeup_is_gated_and_retains_six_hour_fallback(self):
        self.check_workflow(
            "discord-feed.yml", "articles", "wake-articles.json",
            "drops-articles-ready", "17 */6 * * *")

    def test_public_markers_do_not_contain_private_artifacts(self):
        for name in ("wake-reports.json", "wake-articles.json"):
            text = (ROOT / ".dispatch" / name).read_text(encoding="utf-8")
            self.assertNotIn("reports/", text)
            self.assertNotIn("articles/", text)
            self.assertNotIn("discord", text.lower())
            self.assertNotIn("sha256", text.lower())


if __name__ == "__main__":
    unittest.main()
