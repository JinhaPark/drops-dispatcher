#!/usr/bin/env python3
"""Dispatch completed Markdown; keep historical backfill on its ordered path."""
import pathlib
import re

import backfill
import chronological_backfill as chronological


def main():
    root = pathlib.Path(__file__).resolve().parents[1]
    plan = backfill.read_json(root / chronological.MANIFEST)
    if plan and not chronological.already_completed(root, plan):
        (root / '.discord-checkpoints-used').touch()
        chronological.deliver(root, plan)
        return
    publication_ids = {i['id'] for i in plan['items']} if plan else set()
    manifest = backfill.read_json(root / backfill.MANIFEST)
    if manifest and manifest.get("status") == "active" and not backfill.already_completed(root, manifest):
        (root / '.discord-checkpoints-used').touch()
        backfill.deliver(root, manifest)
        return
    # Fail closed even when the previous run crashed before its local files
    # were restored. The workflow checks out the latest remote main.
    if backfill.read_json(root / backfill.INFLIGHT, {}):
        raise RuntimeError("Unreconciled remote in-flight delivery; no live posts")
    pending = []
    ledger = backfill.read_json(root / backfill.LEDGER, {})
    # Validate every candidate before the first external POST.
    for path in sorted((root / "articles").glob("**/*.md")):
        text = path.read_text(encoding="utf-8")
        fields, _ = backfill.frontmatter(text)
        if fields.get("id") in publication_ids or backfill.is_backfill_id(fields.get("id", "")):
            continue
        if fields.get("status") != "ready":
            continue
        if (not fields.get("id") or not fields.get("canonical_url")
                or not fields.get("author")
                or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", fields.get("published_at", ""))):
            raise RuntimeError(f"Missing or invalid provenance: {path}")
        item_id = fields["id"]
        digest = backfill.sha(text)
        prior = ledger.get(item_id)
        if prior:
            if prior.get("status") != "complete" or prior.get("sha256") != digest:
                raise RuntimeError(f"{item_id} needs reconciliation; no live posts")
            continue
        pending.append((path, item_id, digest))
    for path, item_id, digest in pending:
        backfill.deliver_one(root, item_id, path, digest, plan="live")
        print(f"{item_id}: remote ledger verified", flush=True)


if __name__ == "__main__":
    main()
