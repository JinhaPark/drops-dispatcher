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
    def test_short_numeric_table_is_aligned_without_pipe_delimiters(self):
        source = "# 보고서\n\n| 지표 | 값 |\n|---|---:|\n| SOXX | 478.20 |\n\n해석 문단입니다.\n"
        rendered = mod.render_for_discord(source)
        self.assertIn("```text\n지표", rendered)
        self.assertIn("SOXX", rendered)
        self.assertIn("478.20", rendered)
        self.assertNotIn("|---", rendered)
        self.assertNotIn("| SOXX |", rendered)
        self.assertEqual(rendered.count("```"), 2)
        self.assertTrue(rendered.endswith("해석 문단입니다.\n"))

    def test_vertical_long_descriptive_table(self):
        source = (
            "| 단계 | 실제 확인·수행 | 결과 |\n"
            "| --- | --- | --- |\n"
            "| Self reflection | 보고서 검증과 독립 검토 차이를 확인 | 자체 검토만 수행 |\n"
            "| Prioritize | 브랜치와 금융모형 검증 증거 대조 | 개선 과제 2건 |\n"
        )
        rendered = mod.render_for_discord(source)
        self.assertIn("**Self reflection**", rendered)
        self.assertIn("- **실제 확인·수행:** 보고서 검증과 독립 검토 차이를 확인", rendered)
        self.assertIn("- **결과:** 자체 검토만 수행", rendered)
        self.assertIn("**Prioritize**", rendered)
        self.assertNotIn("| ---", rendered)
        self.assertNotIn("```", rendered)

    def test_wide_financial_table_uses_vertical_entries(self):
        source = (
            "| 기업 | 10/23 주가 | 시총(십억$) | NTM 보정 FCF 전망(십억$) | NTM FCF/시총 | 실제 5Y CDS |\n"
            "| --- | ---: | ---: | ---: | ---: | --- |\n"
            "| Check Point (CHKP) | 159.03 | 16.24 | 0.84 | 약 5.2% | NA |\n"
        )
        rendered = mod.render_for_discord(source)
        self.assertIn("**Check Point (CHKP)**", rendered)
        self.assertIn("- **NTM FCF/시총:** 약 5.2%", rendered)
        self.assertIn("- **실제 5Y CDS:** NA", rendered)
        self.assertNotIn("| Check Point", rendered)

    def test_unicode_alignment_fits_phone_width(self):
        source = "| 종목 | 가격 | 수익률 |\n|---|---:|---:|\n| 삼성전자 | 100 | 6% |\n| CHKP | 159 | 5% |\n"
        compact = mod._compact_numeric_table(source.splitlines())
        self.assertIsNotNone(compact)
        self.assertLessEqual(max(mod._display_width(row) for row in compact), 36)
        self.assertEqual(mod._display_width("삼성전자"), 8)

    def test_non_table_pipes_are_unchanged(self):
        source = "선택지는 A | B 입니다.\n"
        self.assertEqual(mod.render_for_discord(source), source)

    def test_escaped_pipe_cell_is_preserved(self):
        source = r"| 구분 | 설명 |" + "\n" + "|---|---|\n" + r"| 판단 | 장점 \| 단점 |" + "\n"
        rendered = mod.render_for_discord(source)
        self.assertIn("장점 | 단점", rendered)
        self.assertIn("**판단**", rendered)

    def test_existing_code_block_is_not_double_wrapped(self):
        source = "```\n| a | b |\n|---|---|\n| 1 | 2 |\n```\n"
        self.assertEqual(mod.render_for_discord(source), source)

    def test_long_compact_table_repeats_header_in_balanced_blocks(self):
        rows = [f"| 종목 {index} | {index * 100} |" for index in range(20)]
        source = "| 종목 | 값 |\n|---|---:|\n" + "\n".join(rows) + "\n"
        rendered = mod.render_for_discord(source, table_limit=125)
        self.assertGreater(rendered.count("```"), 2)
        self.assertEqual(rendered.count("```") % 2, 0)
        self.assertEqual(rendered.count("종목"), 20 + rendered.count("```") // 2)
        self.assertNotIn("|---", rendered)
        parts = mod.chunks(rendered, 200)
        self.assertTrue(all(part.count("```") % 2 == 0 for part in parts))
        self.assertTrue(all(mod.units(part) <= 200 for part in parts))

    def test_long_descriptive_cell_keeps_all_text_without_truncation(self):
        note = "설명" * 300
        source = f"| 구분 | 내용 |\n|---|---|\n| 검토 | {note} |\n"
        rendered = mod.render_for_discord(source)
        self.assertIn(note, rendered)
        self.assertNotIn("|---|", rendered)
        self.assertEqual("".join(mod.chunks(rendered)), rendered)


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
