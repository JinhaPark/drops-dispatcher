"""Prevent private-fixture path drift from breaking public CI checks."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ("backfill.py", "chronological_backfill.py", "devansh_recent_five.py")


class ValidationLayoutTests(unittest.TestCase):
    def test_public_code_is_not_copied_into_private_snapshot(self):
        workflow = (ROOT / ".github/workflows/validate-discord.yml").read_text(encoding="utf-8")
        self.assertNotIn("cd private-data", workflow)
        self.assertNotIn("cp -a tests", workflow)
        self.assertNotIn("private-data/scripts", workflow)
        self.assertNotIn("private-data/.github", workflow)
        self.assertIn("python -m unittest discover -s tests -v", workflow)
        for name in SCRIPTS:
            self.assertIn(
                f"python scripts/{name} --validate-only --data-root private-data",
                workflow,
            )

    def test_data_root_cannot_be_used_for_live_backfill(self):
        with tempfile.TemporaryDirectory() as d:
            for name in SCRIPTS:
                with self.subTest(script=name):
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "scripts" / name), "--data-root", d],
                        cwd=ROOT, text=True, capture_output=True, check=False,
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("--data-root requires --validate-only", result.stderr)

    def test_validation_root_is_selected_without_copying_code(self):
        with tempfile.TemporaryDirectory() as d:
            for name, expected in (
                ("backfill.py", "No backfill manifest"),
                ("chronological_backfill.py", "No chronological publication plan"),
            ):
                with self.subTest(script=name):
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "scripts" / name),
                         "--validate-only", "--data-root", d],
                        cwd=ROOT, text=True, capture_output=True, check=True,
                    )
                    self.assertIn(expected, result.stdout)


if __name__ == "__main__":
    unittest.main()
