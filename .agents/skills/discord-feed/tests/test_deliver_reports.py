import importlib.util
import json
import pathlib
import tempfile
import unittest


path = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "deliver_reports.py"
spec = importlib.util.spec_from_file_location("deliver_reports", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class ReportRoutingTests(unittest.TestCase):
    def test_finance_route_uses_finance_secret(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory) / "reports"
            report = root / "finance" / "dbmf" / "2026-10-26T090000Z.md"
            report.parent.mkdir(parents=True)
            report.write_text("report")
            self.assertEqual(
                mod.report_identity(root, report),
                (
                    "scheduled-report:finance/dbmf/2026-10-26T090000Z",
                    "DISCORD_WEBHOOK_URL_FINANCE",
                ),
            )

    def test_general_route_uses_general_secret(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory) / "reports"
            report = root / "general" / "weekly-korea" / "2026-10-26T090000Z.md"
            report.parent.mkdir(parents=True)
            report.write_text("report")
            self.assertEqual(
                mod.report_identity(root, report)[1], "DISCORD_WEBHOOK_URL_GENERAL"
            )

    def test_unknown_route_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory) / "reports"
            report = root / "other" / "task" / "2026-10-26T090000Z.md"
            report.parent.mkdir(parents=True)
            report.write_text("report")
            with self.assertRaisesRegex(ValueError, "unsupported"):
                mod.report_identity(root, report)

    def test_completed_report_is_not_pending(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory) / "reports"
            report = root / "finance" / "credit" / "2026-10-26T090000Z.md"
            report.parent.mkdir(parents=True)
            report.write_text("report")
            item_id, _ = mod.report_identity(root, report)
            ledger = pathlib.Path(directory) / "ledger.json"
            ledger.write_text(json.dumps({item_id: {"status": "complete"}}))
            self.assertEqual(mod.pending_reports(root, ledger), [])


if __name__ == "__main__":
    unittest.main()
