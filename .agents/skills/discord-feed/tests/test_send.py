import importlib.util
import pathlib
import unittest


path = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "send.py"
spec = importlib.util.spec_from_file_location("discord_feed", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class SplitTests(unittest.TestCase):
    def test_emoji_and_exact_reconstruction(self):
        text = "한국어 🧪 테스트 문장입니다.\n\n" * 400
        parts = mod.chunks(text, 1900)
        self.assertEqual("".join(parts), text)
        self.assertTrue(all(mod.units(part) <= 1900 for part in parts))

    def test_unbroken_long_token(self):
        text = "x" * 5500
        parts = mod.chunks(text)
        self.assertEqual("".join(parts), text)
        self.assertEqual(len(parts), 3)

    def test_empty_rejected(self):
        with self.assertRaises(ValueError):
            mod.chunks("   ")

    def test_multiline_markdown(self):
        text = "# 제목\n\n" + "- **항목** [링크](https://example.com)\n" * 200
        self.assertEqual("".join(mod.chunks(text)), text)

    def test_fenced_block_is_not_split(self):
        fenced = "```\n" + "표 안의 긴 행\n" * 80 + "```\n"
        text = "앞 문단\n\n" + fenced + "\n뒤 문단\n"
        parts = mod.chunks(text, 1000)
        containing = [part for part in parts if "표 안의 긴 행" in part]
        self.assertEqual(len(containing), 1)
        self.assertEqual(containing[0].count("```"), 2)


class DiscordTableRenderingTests(unittest.TestCase):
    def test_gfm_table_is_wrapped_in_triple_backticks(self):
        source = (
            "# 보고서\n\n"
            "| 지표 | 값 |\n"
            "|---|---:|\n"
            "| SOXX | 478.20 |\n\n"
            "해석 문단입니다.\n"
        )
        rendered = mod.render_for_discord(source)
        self.assertIn("```\n| 지표 | 값 |\n|---|---:|\n| SOXX | 478.20 |\n```", rendered)
        self.assertTrue(rendered.endswith("해석 문단입니다.\n"))

    def test_non_table_pipes_are_unchanged(self):
        source = "선택지는 A | B 입니다.\n"
        self.assertEqual(mod.render_for_discord(source), source)

    def test_existing_code_block_is_not_double_wrapped(self):
        source = "```\n| a | b |\n|---|---|\n| 1 | 2 |\n```\n"
        self.assertEqual(mod.render_for_discord(source), source)

    def test_long_table_repeats_header_in_balanced_blocks(self):
        rows = [f"| 지표 {index} | {'값' * 40} |" for index in range(20)]
        source = "| 지표 | 값 |\n|---|---|\n" + "\n".join(rows) + "\n"
        rendered = mod.render_for_discord(source, table_limit=500)
        self.assertGreater(rendered.count("```"), 2)
        self.assertEqual(rendered.count("```") % 2, 0)
        self.assertEqual(rendered.count("| 지표 | 값 |"), rendered.count("```") // 2)
        parts = mod.chunks(rendered, 600)
        self.assertTrue(all(part.count("```") % 2 == 0 for part in parts))
        self.assertTrue(all(mod.units(part) <= 600 for part in parts))

    def test_oversized_single_row_fails_closed(self):
        source = "| 지표 | 값 |\n|---|---|\n| SOXX | " + "x" * 500 + " |\n"
        with self.assertRaisesRegex(ValueError, "row exceeds"):
            mod.render_for_discord(source, table_limit=200)


class DurableRecordTests(unittest.TestCase):
    def test_matching_pending_record_can_resume(self):
        record = {
            "sha256": "source",
            "rendered_sha256": "rendered",
            "status": "pending",
            "total": 3,
            "messages": [],
        }
        self.assertEqual(
            mod.validate_existing_record(record, "source", "rendered", 3), "pending"
        )

    def test_pending_legacy_rendering_requires_reconciliation(self):
        record = {
            "sha256": "source",
            "status": "pending",
            "total": 2,
            "messages": [],
        }
        with self.assertRaisesRegex(RuntimeError, "Rendered content changed"):
            mod.validate_existing_record(record, "source", "rendered", 3)

    def test_completed_legacy_record_still_deduplicates(self):
        record = {"sha256": "source", "status": "complete"}
        self.assertEqual(
            mod.validate_existing_record(record, "source", "rendered", 3), "complete"
        )


if __name__ == "__main__":
    unittest.main()
