"""Focused, network-free checks for private semiconductor alert publishing."""
import hashlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import publish_semiconductor_alert as publisher


def release(month="2026-09", article="172254"):
    return {
        "observation_month": month, "article_id": article,
        "title": f"{month[:4]}년 {int(month[5:])}월 수출입 동향",
        "responsible_department": "수출입과",
        "page_url": "https://www.motir.go.kr/kor/article/test",
    }


def evidence(item, markdown):
    return {"release": item, "content_sha256": hashlib.sha256(markdown.encode()).hexdigest()}


class PrivateSemiconductorPublicationTests(unittest.TestCase):
    def test_first_run_records_baseline_only_without_report(self):
        updates = publisher.prepare_updates(None, {}, release(), baseline=True)
        self.assertEqual(set(updates), {publisher.STATE})
        self.assertEqual(json.loads(updates[publisher.STATE])["last_processed"]["delivery_status"], "baseline")

    def test_new_official_article_creates_one_private_finance_report_and_evidence(self):
        current = publisher.new_state(release(), "baseline")
        latest = release("2026-10", "172500")
        body = "## 확정된 10월 반도체 수출 알림"
        updates = publisher.prepare_updates(current, {}, latest, body, evidence(latest, body))
        self.assertEqual(len(updates), 3)
        self.assertIn("reports/finance/semiconductor-export-alert/2026-10-172500.md", updates)
        self.assertIn("data/semiconductor-export-evidence/2026-10-172500.json", updates)
        self.assertEqual(json.loads(updates[publisher.STATE])["last_processed"]["delivery_status"], "queued")
        self.assertNotIn("delivered", updates[publisher.STATE])

    def test_same_article_is_not_requeued(self):
        current = publisher.new_state(release(), "queued")
        self.assertEqual(publisher.prepare_updates(current, {}, release()), {})

    def test_no_private_baseline_blocks_first_historical_send(self):
        with self.assertRaisesRegex(ValueError, "baseline"):
            publisher.prepare_updates(None, {}, release(), "text", evidence(release(), "text"))

    def test_stale_article_is_not_sent_again(self):
        current = publisher.new_state(release("2026-10", "172500"), "queued")
        with self.assertRaisesRegex(ValueError, "older release"):
            publisher.prepare_updates(current, {}, release(), "text", evidence(release(), "text"))

    def test_immutable_path_conflict_requires_reconciliation(self):
        current = publisher.new_state(release(), "baseline")
        latest = release("2026-10", "172500")
        report = publisher.metadata(latest)[1]
        with self.assertRaisesRegex(ValueError, "immutable"):
            publisher.prepare_updates(current, {report: "exists"}, latest, "text", evidence(latest, "text"))

    def test_receipt_hash_mismatch_rejected(self):
        current = publisher.new_state(release(), "baseline")
        latest = release("2026-10", "172500")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            publisher.prepare_updates(current, {}, latest, "text", evidence(latest, "other text"))

    def test_official_release_title_and_department_are_required(self):
        invalid = release()
        invalid["responsible_department"] = "ICT"
        with self.assertRaisesRegex(ValueError, "수출입과"):
            publisher.metadata(invalid)

    def test_producer_cannot_mark_discord_delivery_complete(self):
        with self.assertRaisesRegex(ValueError, "cannot mark"):
            publisher.new_state(release(), "delivered")


class SemiconductorWorkflowAuthTests(unittest.TestCase):
    """Keep private skills checkout authenticated even after repo visibility changes."""

    @classmethod
    def setUpClass(cls):
        cls.workflow = (
            Path(__file__).resolve().parents[1]
            / ".github/workflows/semiconductor-export-monitor.yml"
        ).read_text(encoding="utf-8")

    def test_skills_checkouts_use_scoped_read_only_installation_token(self):
        workflow = self.workflow
        self.assertIn("id: skills-token", workflow)
        self.assertIn("repositories: skills", workflow)
        self.assertIn("permission-contents: read", workflow)
        self.assertEqual(
            workflow.count("token: ${{ steps.skills-token.outputs.token }}"), 2
        )
        self.assertEqual(workflow.count("persist-credentials: false"), 5)

    def test_motir_cron_concentrates_on_first_of_month_korean_time(self):
        workflow = self.workflow
        self.assertIn('cron: "23 0,2,5,8 1 * *"', workflow)
        self.assertIn('cron: "37 0,6 2-3 * *"', workflow)
        self.assertEqual(workflow.count("- cron:"), 2)
        self.assertNotIn('cron: "17 0 * * *"', workflow)
        self.assertNotIn("*/15", workflow)

    def test_ecos_branch_is_checked_out_with_token_not_fetched_anonymously(self):
        workflow = self.workflow
        self.assertIn("ref: automation/ecos-cache", workflow)
        self.assertIn("path: skills-cache-repo", workflow)
        self.assertIn("git -C skills-cache-repo rev-parse HEAD", workflow)
        self.assertIn("git -C skills-cache-repo show", workflow)
        self.assertNotIn("git -C skills-repo fetch", workflow)


if __name__ == "__main__":
    unittest.main()
