#!/usr/bin/env python3
"""Deliver immutable private finance/general reports with durable GitHub API fences.

Only the dispatcher owns Discord credentials. The report branch contains the
source, chunk receipts and an in-flight marker in the SAME private commit.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import backfill
from private_repo import persist_state

ROOT = Path(__file__).resolve().parents[1]
LEDGER = "data/discord-report-deliveries.json"
INFLIGHT = "data/discord-report-inflight.json"
BRANCH = "automation/report-feed"

sys.path.insert(0, str(ROOT / ".agents/skills/discord-feed/scripts"))
from deliver_reports import report_identity  # noqa: E402


def read_state(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def pending(root: Path):
    reports = root / "reports"
    if not reports.exists():
        return []
    ledger = read_state(root / LEDGER)
    if not isinstance(ledger, dict):
        raise ValueError("Invalid private report ledger")
    result = []
    for report in sorted(reports.rglob("*.md")):
        item_id, webhook_env = report_identity(reports, report)
        digest = hashlib.sha256(report.read_bytes()).hexdigest()
        prior = ledger.get(item_id)
        if prior:
            if prior.get("sha256") != digest or prior.get("status") != "complete":
                raise RuntimeError(f"Unreconciled delivery receipt for {item_id}")
            continue
        result.append((report, item_id, webhook_env, digest))
    return result


def valid_complete(record: dict, digest: str) -> bool:
    messages = record.get("messages", [])
    total = record.get("total")
    return (record.get("sha256") == digest
            and record.get("status") == "complete"
            and isinstance(total, int) and total > 0
            and isinstance(messages, list) and len(messages) == total
            and all(isinstance(m, dict) and m.get("index") == i and m.get("message_id")
                    for i, m in enumerate(messages)))


def checkpoint(root, prior, next_marker):
    return persist_state(
        root, prior, next_marker, LEDGER, INFLIGHT,
        merge_ledgers=backfill.merge_ledgers, branch=BRANCH
    )


def run(root: Path, dry_run=False):
    inflight = read_state(root / INFLIGHT)
    if inflight:
        raise RuntimeError("Unreconciled private report in-flight marker; no Discord POSTs")
    candidates = pending(root)
    if dry_run:
        print(f"Safe report candidates: {len(candidates)} (no Discord messages sent)")
        return
    for report, item_id, webhook_env, digest in candidates:
        if not os.environ.get(webhook_env):
            raise RuntimeError(f"Required routed webhook is missing: {webhook_env}")
        marker = {"id": item_id, "sha256": digest,
                  "run_id": os.environ.get("GITHUB_RUN_ID", "local"), "plan": "reports"}
        checkpoint(root, {}, marker)  # Remotely verified fence BEFORE Discord POST.
        try:
            subprocess.run(
                [sys.executable, str(root / ".agents/skills/discord-feed/scripts/send.py"),
                 "--file", str(report), "--id", item_id, "--state", str(root / LEDGER),
                 "--webhook-env", webhook_env],
                cwd=root, check=True,
            )
        except BaseException:
            # Keep the remote marker. Never re-send without human reconciliation.
            checkpoint(root, marker, marker)
            raise
        receipt = read_state(root / LEDGER).get(item_id, {})
        if not valid_complete(receipt, digest):
            checkpoint(root, marker, marker)
            raise RuntimeError(f"Ambiguous report delivery: {item_id}; reconcile manually")
        checkpoint(root, marker, {})
        print(f"Confirmed private report receipt for {item_id}")


if __name__ == "__main__":
    run(ROOT, dry_run="--dry-run" in sys.argv)
