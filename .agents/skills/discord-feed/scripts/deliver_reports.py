#!/usr/bin/env python3
"""Route completed scheduled reports to the configured Discord channel."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


SEND_SCRIPT = Path(__file__).with_name("send.py")
ROUTES = {
    "finance": "DISCORD_WEBHOOK_URL_FINANCE",
    "general": "DISCORD_WEBHOOK_URL_GENERAL",
}


def report_identity(root: Path, report: Path) -> tuple[str, str]:
    relative = report.resolve().relative_to(root.resolve())
    if len(relative.parts) < 3 or relative.parts[0] not in ROUTES:
        raise ValueError(f"unsupported scheduled-report path: {relative.as_posix()}")
    route = relative.parts[0]
    item_id = "scheduled-report:" + relative.with_suffix("").as_posix()
    return item_id, ROUTES[route]


def pending_reports(root: Path, state_path: Path) -> list[tuple[Path, str, str]]:
    if not root.is_dir():
        raise ValueError(f"report root does not exist: {root}")
    try:
        ledger = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    except json.JSONDecodeError:
        raise ValueError("scheduled-report delivery ledger is not valid JSON") from None
    if not isinstance(ledger, dict):
        raise ValueError("scheduled-report delivery ledger must be an object")
    result = []
    for report in sorted(root.rglob("*.md")):
        item_id, webhook_env = report_identity(root, report)
        record = ledger.get(item_id)
        if not isinstance(record, dict) or record.get("status") != "complete":
            result.append((report, item_id, webhook_env))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    reports = pending_reports(args.root, args.state)
    for report, item_id, webhook_env in reports:
        command = [
            sys.executable,
            str(SEND_SCRIPT),
            "--file",
            str(report),
            "--id",
            item_id,
            "--state",
            str(args.state),
            "--webhook-env",
            webhook_env,
        ]
        if args.dry_run:
            command.append("--dry-run")
        subprocess.run(command, check=True)
    print(json.dumps({"candidate_count": len(reports), "dry_run": args.dry_run}))


if __name__ == "__main__":
    main()
