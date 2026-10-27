#!/usr/bin/env python3
"""One-shot, at-most-once Discord route probe with durable private receipts.

Never processes a regular article or report. Creates three tiny synthetic
Markdown files only in the ephemeral runner; only receipts go to private main.
"""
import hashlib
import os
from pathlib import Path

import backfill
import deliver_private_reports as reports
import private_repo

ROOT = Path(__file__).resolve().parents[1]
CHECK_DATE = "2026-10-27"
ARTICLE_ID = "system:discord-route-check:ai:20261027"
REPORT_PATHS = (
    "reports/finance/system-route-check/2026-10-27.md",
    "reports/general/system-route-check/2026-10-27.md",
)
TEXT = {
    "ai": "**Discord AI 경로 점검** — 2026-10-27\nChatGPT 예약작업과 GitHub Actions 전달 경로의 단발성 검증 메시지입니다.\n",
    "finance": "**Discord 금융 경로 점검** — 2026-10-27\n자동 발송·메시지 ID·비공개 체크포인트를 확인하는 단발성 시험입니다.\n",
    "general": "**Discord 일반 경로 점검** — 2026-10-27\n자동 발송·메시지 ID·비공개 체크포인트를 확인하는 단발성 시험입니다.\n",
}
WEBHOOKS = ("DISCORD_WEBHOOK_URL", "DISCORD_WEBHOOK_URL_FINANCE",
            "DISCORD_WEBHOOK_URL_GENERAL")


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_fixture(root):
    if (root / "reports").exists():
        raise RuntimeError("Unexpected real reports in isolated verification workspace")
    test_file = root / "route-check-ai.md"
    test_file.write_text(TEXT["ai"], encoding="utf-8")
    ids = {ARTICLE_ID: digest(TEXT["ai"])}
    for category, name in zip(("finance", "general"), REPORT_PATHS):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(TEXT[category], encoding="utf-8")
        report_id, webhook = reports.report_identity(root / "reports", path)
        required_webhook = ("DISCORD_WEBHOOK_URL_FINANCE"
                            if category == "finance" else "DISCORD_WEBHOOK_URL_GENERAL")
        if webhook != required_webhook:
            raise RuntimeError("Report route mismatch")
        ids[report_id] = digest(TEXT[category])
    return test_file, ids


def check_no_active_sends(root, ids):
    for name in (backfill.INFLIGHT, reports.INFLIGHT):
        if backfill.read_json(root / name, {}):
            raise RuntimeError("Existing in-flight marker; never blindly retry")
    for ledger_name in (backfill.LEDGER, reports.LEDGER):
        ledger = backfill.read_json(root / ledger_name, {})
        if not isinstance(ledger, dict):
            raise RuntimeError("Invalid private delivery ledger")
        for key, record in ledger.items():
            if not isinstance(record, dict) or record.get("status") != "complete":
                raise RuntimeError("Unresolved previous delivery; no new route probes")
            if key in ids and not reports.valid_complete(record, ids[key]):
                raise RuntimeError("Prior route probe differs from expected immutable receipt")


def remote_proof(ids):
    head = private_repo.ref_head(private_repo.DEFAULT_REPO, "main")
    _, entries = private_repo.tree_snapshot(private_repo.DEFAULT_REPO, head)
    article_ledger = private_repo._remote_json(
        private_repo.DEFAULT_REPO, entries, backfill.LEDGER)
    report_ledger = private_repo._remote_json(
        private_repo.DEFAULT_REPO, entries, reports.LEDGER)
    for name in (backfill.INFLIGHT, reports.INFLIGHT):
        if private_repo._remote_json(private_repo.DEFAULT_REPO, entries, name):
            raise RuntimeError("A private in-flight marker remains set")
    for item_id, sha in ids.items():
        state = article_ledger if item_id == ARTICLE_ID else report_ledger
        if not reports.valid_complete(state.get(item_id, {}), sha):
            raise RuntimeError("Remote private receipt missing or incomplete for route " + item_id)
    print("All three Discord routes verified: durable remote message IDs and empty in-flight markers")


def main():
    if os.environ.get("DROPS_PRIVATE_REST") != "1":
        raise RuntimeError("Refuse probe without private REST checkpoints")
    if any(not os.environ.get(key) for key in WEBHOOKS):
        raise RuntimeError("All three dedicated Discord webhook secrets are required")
    for name in (backfill.INFLIGHT, reports.INFLIGHT):
        if backfill.read_json(ROOT / name, {}):
            raise RuntimeError("Existing private in-flight marker")
    path, ids = build_fixture(ROOT)
    check_no_active_sends(ROOT, ids)
    backfill.deliver_one(ROOT, ARTICLE_ID, path, ids[ARTICLE_ID],
                         text=TEXT["ai"], plan="system-route-check")
    reports.run(ROOT)
    remote_proof(ids)


if __name__ == "__main__":
    main()
