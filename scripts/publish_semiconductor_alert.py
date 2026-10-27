#!/usr/bin/env python3
"""Publish verified Korean semiconductor alerts only into private drops/main.

This producer never has a Discord webhook. The existing report-feed workflow
owns delivery and acknowledged message receipts. Writes use one atomic Git tree
update with a non-forced ref move; competing changes fail closed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import private_repo

REPO = "JinhaPark/drops"
BRANCH = "main"
STATE = "data/semiconductor-export-monitor.json"
REPORT_ROOT = "reports/finance/semiconductor-export-alert"
EVIDENCE_ROOT = "data/semiconductor-export-evidence"


def metadata(release: dict) -> tuple[str, str, str]:
    month = release.get("observation_month")
    article = str(release.get("article_id", ""))
    if not isinstance(month, str) or not re.fullmatch(r"20\d{2}-(0[1-9]|1[0-2])", month):
        raise ValueError("invalid release month")
    if not re.fullmatch(r"[0-9]{1,16}", article):
        raise ValueError("invalid article id")
    if release.get("title") != f"{month[:4]}년 {int(month[5:])}월 수출입 동향":
        raise ValueError("not an exact monthly release title")
    if release.get("responsible_department") != "수출입과":
        raise ValueError("not an official monthly 수출입과 release")
    slug = month + "-" + article
    return month, REPORT_ROOT + "/" + slug + ".md", EVIDENCE_ROOT + "/" + slug + ".json"


def read_remote_state() -> tuple[str, str, dict, dict | None]:
    head = private_repo.ref_head(REPO, BRANCH)
    base_tree, entries = private_repo.tree_snapshot(REPO, head)
    blob = entries.get(STATE)
    state = json.loads(private_repo.blob_bytes(REPO, blob["sha"])) if blob else None
    if state is not None and (
        not isinstance(state, dict)
        or state.get("schema_version") != 1
        or not isinstance(state.get("last_processed"), dict)
    ):
        raise ValueError("private semiconductor monitor state is invalid")
    return head, base_tree, entries, state


def new_state(release: dict, status: str) -> dict:
    if status not in {"baseline", "queued"}:
        raise ValueError("producer cannot mark a Discord delivery complete")
    return {"schema_version": 1, "last_processed": {
        **release, "delivery_status": status,
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    }}


def prepare_updates(state: dict | None, existing: dict[str, str],
                    release: dict, markdown: str | None = None,
                    evidence: dict | None = None, *, baseline: bool = False) -> dict[str, str]:
    month, report_path, evidence_path = metadata(release)
    if baseline:
        if state is not None:
            return {}  # Another bootstrap already won; never backfill.
        if markdown is not None or evidence is not None:
            raise ValueError("baseline must not publish Markdown")
        return {STATE: json.dumps(new_state(release, "baseline"), ensure_ascii=False, indent=2) + "\n"}

    if state is None:
        raise ValueError("missing private baseline; refuse historical delivery")
    prior = state["last_processed"]
    prior_id = str(prior.get("article_id", ""))
    prior_month = prior.get("observation_month")
    if not isinstance(prior_month, str) or not re.fullmatch(r"20\d{2}-(0[1-9]|1[0-2])", prior_month):
        raise ValueError("corrupt private baseline observation month")
    if month < prior_month:
        raise ValueError("older release than private baseline; refuse replay")
    if prior_id == str(release["article_id"]):
        return {}  # Already observed; no duplicate or forced send.
    if markdown is None or not markdown.strip() or evidence is None:
        raise ValueError("new release requires rendered Markdown and evidence")
    if evidence.get("release", {}).get("article_id") != release["article_id"]:
        raise ValueError("evidence release mismatch")
    if evidence.get("content_sha256") != hashlib.sha256(markdown.encode("utf-8")).hexdigest():
        raise ValueError("evidence content hash mismatch")
    if report_path in existing or evidence_path in existing:
        raise ValueError("immutable release artifact already exists; reconcile before retry")
    if prior.get("delivery_status") not in {"baseline", "queued"}:
        raise ValueError("unexpected producer monitor state")
    return {
        report_path: markdown,
        evidence_path: json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
        STATE: json.dumps(new_state(release, "queued"), ensure_ascii=False, indent=2) + "\n",
    }


def write_updates(head: str, base_tree: str, updates: dict[str, str]) -> None:
    tree_elements = []
    for path, content in sorted(updates.items()):
        blob = private_repo.api(REPO, "git/blobs", "POST", {"content": content, "encoding": "utf-8"})
        tree_elements.append({"path": path, "mode": "100644", "type": "blob", "sha": blob["sha"]})
    tree = private_repo.api(REPO, "git/trees", "POST", {"base_tree": base_tree, "tree": tree_elements})
    commit = private_repo.api(REPO, "git/commits", "POST", {
        "message": "Queue verified Korean semiconductor export alert in private drops",
        "tree": tree["sha"], "parents": [head],
    })
    # No force: concurrent report receipt updates are never overwritten.
    private_repo.api(REPO, "git/refs/heads/main", "PATCH", {"sha": commit["sha"], "force": False})
    if private_repo.ref_head(REPO, BRANCH) != commit["sha"]:
        raise RuntimeError("private publication commit not confirmed; reconcile before retry")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["hydrate", "baseline", "publish"])
    parser.add_argument("--state-out", type=Path)
    parser.add_argument("--release", type=Path)
    parser.add_argument("--markdown", type=Path)
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()
    head, tree, entries, state = read_remote_state()
    if args.command == "hydrate":
        if not args.state_out:
            parser.error("hydrate requires --state-out")
        if state is not None:
            args.state_out.parent.mkdir(parents=True, exist_ok=True)
            args.state_out.write_text(json.dumps(state, ensure_ascii=False) + "\n", encoding="utf-8")
        print("Private monitor state available" if state is not None else "No private monitor baseline; first release will be baseline only")
        return
    if not args.release:
        parser.error("baseline/publish require --release")
    release = json.loads(args.release.read_text(encoding="utf-8"))
    if not isinstance(release, dict):
        raise ValueError("release must be an object")
    markdown = args.markdown.read_text(encoding="utf-8") if args.markdown else None
    evidence = json.loads(args.evidence.read_text(encoding="utf-8")) if args.evidence else None
    month, report, receipt_path = metadata(release)
    existing = {path: "exists" for path in (report, receipt_path) if path in entries}
    updates = prepare_updates(state, existing, release, markdown, evidence,
                              baseline=args.command == "baseline")
    if not updates:
        print(f"No eligible new artifact for {month}; no private writes or Discord posts")
        return
    write_updates(head, tree, updates)
    print(f"Committed private {month} monitor state and {len(updates)-1} immutable artifacts; Discord delivery is separate")


if __name__ == "__main__":
    main()
