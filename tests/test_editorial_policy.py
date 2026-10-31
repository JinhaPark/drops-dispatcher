"""Word terminology must preserve archive verification and delivery safeguards."""
import copy
import json
import os
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
FIXTURE_ROOT = pathlib.Path(os.environ.get("DROPS_TEST_DATA_ROOT", str(ROOT)))
sys.path.insert(0, str(ROOT / "scripts"))
import backfill
import chronological_backfill
import editorial_policy
import one_time_preview


class EditorialPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)

    def copy_article(self, item, version):
        target = self.root / item["markdown_path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        original = (FIXTURE_ROOT / item["markdown_path"]).read_text()
        text = original.replace(editorial_policy.LEGACY_EDITORIAL_VERSION, version)
        target.write_text(text)
        updated = copy.deepcopy(item)
        updated["markdown_sha256"] = backfill.sha(text)
        return updated

    def test_current_policy_uses_standard_english(self):
        self.assertEqual(editorial_policy.EDITORIAL_VERSION, "ko-300words-v1")
        for name, key in [(backfill.MANIFEST, "editions"), (chronological_backfill.ELEVATE, "articles")]:
            items = json.loads((FIXTURE_ROOT / name).read_text())[key]
            counts = [i["summary_word_count"] for i in items if "summary_word_count" in i]
            self.assertTrue(counts)
            self.assertTrue(all(c is None or 250 <= c <= 350 for c in counts))

    def test_ae_and_elevate_accept_current_and_legacy_versions_but_reject_unknown_versions(self):
        ae = json.loads((FIXTURE_ROOT / backfill.MANIFEST).read_text())
        elevate = json.loads((FIXTURE_ROOT / chronological_backfill.ELEVATE).read_text())
        for items, validate in [(ae["editions"], backfill.validate_article), (elevate["articles"], chronological_backfill.validate_elevate)]:
            item = next(i for i in items if i["status"] == "ready")
            for version in [editorial_policy.LEGACY_EDITORIAL_VERSION, editorial_policy.EDITORIAL_VERSION]:
                with self.subTest(source=item["source_id"], version=version):
                    updated = self.copy_article(item, version)
                    self.assertEqual(validate(self.root, updated)[0], item["id"])
            updated = self.copy_article(item, "unknown-policy")
            with self.assertRaisesRegex(ValueError, "editorial_version"):
                validate(self.root, updated)

    def test_preview_accepts_both_versions_without_relaxing_digest_checks(self):
        original = json.loads((FIXTURE_ROOT / one_time_preview.MANIFEST).read_text())
        for version in [editorial_policy.LEGACY_EDITORIAL_VERSION, editorial_policy.EDITORIAL_VERSION]:
            manifest = copy.deepcopy(original)
            manifest["items"] = [self.copy_article(item, version) for item in original["items"]]
            self.assertEqual(len(one_time_preview.validate(self.root, manifest)), 2)
        item = manifest["items"][0]
        path = self.root / item["markdown_path"]
        path.write_text(path.read_text() + "Unreviewed change\n")
        with self.assertRaisesRegex(ValueError, "changed since review"):
            one_time_preview.validate(self.root, manifest)

    def test_preview_rejects_unknown_version_even_with_a_matching_digest(self):
        manifest = json.loads((FIXTURE_ROOT / one_time_preview.MANIFEST).read_text())
        manifest["items"] = [self.copy_article(item, "unknown-policy") for item in manifest["items"]]
        with self.assertRaisesRegex(ValueError, "editorial state"):
            one_time_preview.validate(self.root, manifest)


if __name__ == "__main__":
    unittest.main()
