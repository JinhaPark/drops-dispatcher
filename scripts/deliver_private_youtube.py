#!/usr/bin/env python3
"""Deliver immutable private YouTube summaries with durable GitHub API fences.

Only the dispatcher owns Discord credentials. Private drops/main keeps
article and report sources with separate receipts and in-flight markers.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import sys

import backfill
from private_repo import persist_state, require_private_data_root

ROOT = Path(__file__).resolve().parents[1]
LEDGER = "data/discord-youtube-deliveries.json"
INFLIGHT = "data/discord-youtube-inflight.json"
BRANCH = "main"

sys.path.insert(0, str(ROOT / ".agents/skills/discord-feed/scripts"))


def read_state(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def pending(root: Path):
    # Raw transcripts are deliberately outside this enumeration and snapshot.
    ledger = read_state(root / LEDGER)
    if not isinstance(ledger, dict):
        raise ValueError("Invalid private YouTube ledger")
    result = []
    seen = set()
    for path in sorted((root / "youtube/summaries").glob("*/*.md")):
        if path.is_symlink():
            raise ValueError("YouTube summary symlinks are forbidden")
        fields, body = backfill.frontmatter(path.read_text(encoding="utf-8"))
        if fields.get("status") != "ready":
            continue
        video_id = path.stem
        if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
            raise ValueError("Invalid YouTube video ID")
        item_id = "youtube:" + video_id
        if item_id in seen:
            raise ValueError("Duplicate YouTube identity")
        seen.add(item_id)
        required = {"id": item_id, "video_id": video_id, "source_id": path.parent.name,
                    "canonical_url": "https://www.youtube.com/watch?v=" + video_id,
                    "transcript_path": "youtube/transcripts/" + video_id + ".json",
                    "editorial_version": "youtube-kakao-v1"}
        if any(fields.get(k) != v for k, v in required.items()):
            raise ValueError("YouTube provenance mismatch")
        if not re.fullmatch(r"[0-9a-f]{64}", fields.get("transcript_sha256", "")):
            raise ValueError("Missing YouTube transcript digest")
        if not fields.get("published_at") or not body.strip():
            raise ValueError("Missing YouTube publication provenance or summary")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        prior = ledger.get(item_id)
        if prior:
            if not valid_complete(prior, digest):
                raise RuntimeError("Unreconciled private YouTube delivery receipt")
            continue
        result.append((path, item_id, "DISCORD_WEBHOOK_URL_FINANCE", digest))
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
        raise RuntimeError("Unreconciled private YouTube in-flight marker; no Discord POSTs")
    candidates = pending(root)
    if dry_run:
        print(f"Safe YouTube candidates: {len(candidates)} (no Discord messages sent)")
        return
    for report, item_id, webhook_env, digest in candidates:
        if not os.environ.get(webhook_env):
            raise RuntimeError(f"Required routed webhook is missing: {webhook_env}")
        marker = {"id": item_id, "sha256": digest,
                  "run_id": os.environ.get("GITHUB_RUN_ID", "local"), "plan": "youtube"}
        checkpoint(root, {}, marker)  # Remotely verified fence BEFORE Discord POST.
        # Check remote-merged state: another runner might have completed this ID
        # since we took the local snapshot. Never post it a second time.
        merged_receipt = read_state(root / LEDGER).get(item_id)
        if merged_receipt:
            if not valid_complete(merged_receipt, digest):
                raise RuntimeError("Remote report receipt needs reconciliation")
            checkpoint(root, marker, {})
            continue
        try:
            subprocess.run(
                [sys.executable, str(ROOT / ".agents/skills/discord-feed/scripts/send.py"),
                 "--file", str(report), "--id", item_id, "--state", str(root / LEDGER),
                 "--webhook-env", webhook_env, "--strip-frontmatter"],
                cwd=root, check=True,
            )
        except BaseException:
            # Keep the remote marker. Never re-send without human reconciliation.
            checkpoint(root, marker, marker)
            raise
        receipt = read_state(root / LEDGER).get(item_id, {})
        if not valid_complete(receipt, digest):
            checkpoint(root, marker, marker)
            raise RuntimeError("Ambiguous private YouTube delivery; reconcile manually")
        checkpoint(root, marker, {})
        print("Confirmed private YouTube receipt")


if __name__ == "__main__":
    run(require_private_data_root(ROOT), dry_run="--dry-run" in sys.argv)

