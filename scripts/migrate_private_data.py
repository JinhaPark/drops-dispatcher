#!/usr/bin/env python3
"""Stage byte-preserving migration from two immutable public worktrees to private main.

This script never sends Discord messages, pushes Git refs, or prints source
content. Its caller must verify the private-only destination and commit/push
only after every hash and receipt check succeeds.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


REPORT_LEDGER = "data/discord-report-deliveries.json"
ARTICLE_LEDGER = "data/discord-deliveries.json"
ARCHIVE_REPORT = "data/migration/20261027-original-report-deliveries.json"
ARCHIVE_ARTICLE = "data/migration/20261027-original-article-deliveries.json"


def files_under(root: Path, group: str) -> dict[str, bytes]:
    base = root / group
    if not base.is_dir() or base.is_symlink():
        raise RuntimeError(f"Missing or unsafe source directory: {group}")
    found = {}
    for path in sorted(base.rglob("*")):
        if path.is_symlink():
            raise RuntimeError("Symlink in migration source")
        if path.is_file():
            found[path.relative_to(root).as_posix()] = path.read_bytes()
    return found


def get_required(root: Path, name: str) -> bytes:
    path = root / name
    if not path.is_file() or path.is_symlink():
        raise RuntimeError(f"Missing required source: {name}")
    return path.read_bytes()


def records(blob: bytes, name: str) -> dict:
    payload = json.loads(blob.decode("utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"Invalid ledger: {name}")
    for key, record in payload.items():
        if not isinstance(key, str) or not isinstance(record, dict):
            raise RuntimeError(f"Invalid delivery record in {name}")
        if record.get("status") != "complete":
            raise RuntimeError(f"Unresolved historical receipt in {name}")
        total, messages = record.get("total"), record.get("messages")
        if (not isinstance(total, int) or isinstance(total, bool) or total < 1
                or not isinstance(messages, list) or len(messages) != total
                or any(not isinstance(m, dict) or m.get("index") != i
                       or not m.get("message_id") for i, m in enumerate(messages))):
            raise RuntimeError(f"Incomplete message IDs in {name}")
    return payload


def merge_receipts(target: Path, name: str, original: bytes) -> bytes:
    legacy = records(original, name)
    existing = records(target.read_bytes(), name) if target.exists() else {}
    merged = dict(existing)
    for key, record in legacy.items():
        if key in merged and merged[key] != record:
            raise RuntimeError(f"Conflicting historical delivery ID in {name}")
        merged[key] = record
    if merged == existing:
        return target.read_bytes()
    return (json.dumps(merged, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def migrate(news: Path, reports: Path, private: Path, verify_only: bool = False):
    roots = [p.resolve(strict=True) for p in (news, reports, private)]
    if len(set(roots)) != 3:
        raise RuntimeError("News, reports and private paths must be different")
    news, reports, private = roots
    source = files_under(news, "articles")
    if len(source) == 0 or not any(p.endswith(".md") for p in source):
        raise RuntimeError("Missing historical Markdown articles")
    source.update(files_under(news, "data"))
    source["sources.json"] = get_required(news, "sources.json")
    source[ARCHIVE_ARTICLE] = get_required(news, ARTICLE_LEDGER)
    source[ARCHIVE_REPORT] = get_required(reports, REPORT_LEDGER)
    report_files = files_under(reports, "reports")
    if not report_files or not all(p.endswith(".md") for p in report_files):
        raise RuntimeError("Missing historical Markdown reports")
    source.update(report_files)
    for name in ("data/monitor-state.json", ARTICLE_LEDGER):
        if name not in source:
            raise RuntimeError(f"Missing monitored source: {name}")
    inflight = reports / "data/discord-report-inflight.json"
    if inflight.exists() and json.loads(inflight.read_text()) != {}:
        raise RuntimeError("Historical report in-flight requires reconciliation")
    live_marker = private / "data/discord-report-inflight.json"
    if live_marker.exists() and json.loads(live_marker.read_text()) != {}:
        raise RuntimeError("Private report in-flight requires reconciliation")

    # Do not replace the newer private ledgers: retain additional receipts while
    # copying every legacy message ID unchanged. Archive both original byte streams.
    for ledger, original in ((ARTICLE_LEDGER, get_required(news, ARTICLE_LEDGER)),
                             (REPORT_LEDGER, get_required(reports, REPORT_LEDGER))):
        source[ledger] = merge_receipts(private / ledger, ledger, original)

    # Check every file and every source hash before making *any* change.
    hashes = {name: hashlib.sha256(blob).hexdigest() for name, blob in source.items()}
    updates = {}
    for name, blob in source.items():
        target = private / name
        if target.is_symlink():
            raise RuntimeError(f"Unsafe private destination: {name}")
        if target.exists():
            if not target.is_file():
                raise RuntimeError(f"Unsafe private file: {name}")
            if target.read_bytes() != blob:
                if name not in (ARTICLE_LEDGER, REPORT_LEDGER):
                    raise RuntimeError(f"Private content conflict: {name}")
                updates[name] = blob
        else:
            updates[name] = blob
    if not verify_only:
        for name, blob in updates.items():
            target = private / name
            target.parent.mkdir(parents=True, exist_ok=True)
            staged = target.with_name(target.name + ".migration-tmp")
            if staged.exists():
                raise RuntimeError(f"Stale migration staging file: {name}")
            try:
                with staged.open("xb") as out:
                    out.write(blob)
                os.replace(staged, target)
            finally:
                staged.unlink(missing_ok=True)

    for name, blob in source.items():
        target = private / name
        if verify_only and name in updates:
            raise RuntimeError(f"Private migration incomplete: {name}")
        if (hashlib.sha256(blob).hexdigest() != hashes[name]
                or not target.is_file()
                or hashlib.sha256(target.read_bytes()).hexdigest() != hashes[name]):
            raise RuntimeError(f"Post-migration SHA-256 mismatch: {name}")
    print(f"Migration verified: {len(source)} byte-hashed files; {len(updates)} staged changes; no sends")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--news", type=Path, required=True, help="Pinned historical public main worktree")
    parser.add_argument("--reports", type=Path, required=True, help="Pinned historical report-feed worktree")
    parser.add_argument("--private", type=Path, required=True, help="Private data checkout only")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    migrate(args.news, args.reports, args.private, args.verify_only)


if __name__ == "__main__":
    main()
