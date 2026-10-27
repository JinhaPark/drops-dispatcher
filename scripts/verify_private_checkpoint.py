#!/usr/bin/env python3
"""One-shot remote checkpoint integration test on an isolated private scratch branch.

Creates no Discord messages, never touches the production branch, and removes
the temporary ref even if verification fails.
"""
import json
import os
from pathlib import Path
import tempfile

import backfill
import private_repo

REPO = "JinhaPark/drops"


def main():
    run_id = os.environ.get("GITHUB_RUN_ID", "local")
    if not run_id.isdigit():
        raise RuntimeError("GitHub run ID required")
    branch = f"automation/dispatcher-checkpoint-probe-{run_id}"
    ref = "git/refs/heads/" + branch
    created = False
    before = private_repo.ref_head(REPO, "main")
    try:
        private_repo.api(REPO, "git/refs", "POST",
                         {"ref": "refs/heads/" + branch, "sha": before})
        created = True
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger_rel = "data/probe-deliveries.json"
            marker_rel = "data/probe-inflight.json"
            ledger_file = root / ledger_rel
            ledger_file.parent.mkdir()
            ledger = {"probe": {"sha256": "a" * 64, "status": "complete", "total": 1,
                                "messages": [{"index": 0, "message_id": "synthetic-only"}]}}
            ledger_file.write_text(json.dumps(ledger))
            marker = {"id": "probe", "sha256": "a" * 64, "run_id": run_id}
            private_repo.persist_state(root, {}, marker, ledger_rel, marker_rel,
                                       backfill.merge_ledgers, branch=branch)
            private_repo.persist_state(root, marker, {}, ledger_rel, marker_rel,
                                       backfill.merge_ledgers, branch=branch)
            head = private_repo.ref_head(REPO, branch)
            _, entries = private_repo.tree_snapshot(REPO, head)
            remote_ledger = private_repo._remote_json(REPO, entries, ledger_rel)
            remote_marker = private_repo._remote_json(REPO, entries, marker_rel)
            if remote_ledger != ledger or remote_marker != {}:
                raise RuntimeError("Private checkpoint round trip was not atomic")
            if private_repo.ref_head(REPO, "main") != before:
                raise RuntimeError("Production main changed during scratch verification")
        print("Verified private REST checkpoint write, clear, and remote receipts; no Discord sends")
    finally:
        if created:
            private_repo.api(REPO, ref, "DELETE")
            try:
                private_repo.ref_head(REPO, branch)
            except private_repo.ApiError as exc:
                if exc.status != 404:
                    raise
            else:
                raise RuntimeError("Temporary private branch was not removed")


if __name__ == "__main__":
    main()
