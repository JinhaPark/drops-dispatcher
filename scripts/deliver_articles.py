#!/usr/bin/env python3
"""Dispatch completed Markdown; keep historical backfill on its ordered path."""
import pathlib
import re
import subprocess
import sys

import backfill


def main():
    root = pathlib.Path(__file__).resolve().parents[1]
    manifest = backfill.read_json(root / backfill.MANIFEST)
    if manifest and manifest.get("status") == "active" and not backfill.already_completed(root, manifest):
        backfill.deliver(root, manifest)
        return
    for path in sorted((root / "articles").glob("**/*.md")):
        text = path.read_text(encoding="utf-8")
        fields, _ = backfill.frontmatter(text)
        if backfill.is_backfill_id(fields.get("id", "")):
            continue
        if fields.get("status") != "ready":
            continue
        if not fields.get("id") or not fields.get("canonical_url") or not fields.get("author") or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", fields.get("published_at", "")):
            raise SystemExit(f"Missing or invalid provenance: {path}")
        result = subprocess.run([sys.executable, str(root / ".agents/skills/discord-feed/scripts/send.py"),
                                 "--file", str(path), "--id", fields["id"],
                                 "--state", str(root / backfill.LEDGER)], cwd=root)
        if result.returncode:
            raise SystemExit(f"Discord delivery failed for {path}; preserve ledger and inspect uncertain state")


if __name__ == "__main__":
    main()
