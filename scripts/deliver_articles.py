#!/usr/bin/env python3
"""Dispatch completed Markdown; keep historical backfill on its ordered path."""
import datetime
import pathlib
import re

import backfill
import chronological_backfill as chronological
import one_time_preview as preview
import devansh_recent_five as devansh


MONITOR_STATE = "data/monitor-state.json"
TIMESTAMP = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})"


def timestamp(value):
    """Require an explicit offset; never guess the publisher's timezone."""
    if not isinstance(value, str) or not re.fullmatch(TIMESTAMP, value):
        raise ValueError("Expected an ISO publication timestamp with timezone")
    return datetime.datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(datetime.timezone.utc)


def monitoring_policy(root):
    state = backfill.read_json(root / MONITOR_STATE)
    try:
        started_at = timestamp(state["monitoring_started_at"])
        source_starts = {}
        for source_id, source in state.get("sources", {}).items():
            if "monitoring_started_at" in source:
                source_starts[source_id] = max(
                    started_at, timestamp(source["monitoring_started_at"])
                )
        return started_at, source_starts
    except (TypeError, KeyError, ValueError, AttributeError) as exc:
        raise RuntimeError("Missing or invalid monitoring_started_at; no live posts") from exc


def hold_reason(published_at, started_at):
    """None means live-eligible. Backfill approval belongs to reviewed manifests."""
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", published_at):
        day = datetime.date.fromisoformat(published_at)
        if day == started_at.date():
            return "publication time unknown on monitoring start date; explicit timestamp required"
        if day < started_at.date():
            return "baseline-only historical article; explicit backfill approval required"
        return None
    if timestamp(published_at) <= started_at:
        return "publication is not strictly after monitoring start; explicit backfill approval required"
    return None


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
    # Narrow, explicit historical authorization only for two reviewed preview posts.
    # Does not relax global or source-specific live publication start times.
    preview_plan = preview.read_manifest(root)
    if preview_plan is not None and not preview.already_completed(root, preview_plan):
        if preview_plan.get("status") == "active":
            (root / ".discord-checkpoints-used").touch()
            preview.deliver(root, preview_plan)
            return
    # User-approved recent five from Devansh: the paid third item remains held.
    # Reviewed entries use the same remotely verified pre-send checkpoint path.
    devansh_plan = devansh.read_manifest(root)
    if devansh_plan is not None and not devansh.already_completed(root, devansh_plan):
        if devansh_plan.get("status") == "active":
            (root / ".discord-checkpoints-used").touch()
            devansh.deliver(root, devansh_plan)
            return
    started_at, source_starts = monitoring_policy(root)
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
                or not fields.get("author")):
            raise RuntimeError(f"Missing or invalid provenance: {path}")
        item_id = fields["id"]
        digest = backfill.sha(text)
        prior = ledger.get(item_id)
        if prior:
            if prior.get("status") != "complete" or prior.get("sha256") != digest:
                raise RuntimeError(f"{item_id} needs reconciliation; no live posts")
            continue
        try:
            reason = hold_reason(fields.get("published_at", ""), source_starts.get(fields.get("source_id"), started_at))
        except ValueError as exc:
            raise RuntimeError(f"Missing or invalid publication date provenance: {path}") from exc
        if reason:
            print(f"Held {item_id} ({path.relative_to(root)}): {reason}", flush=True)
            continue
        pending.append((path, item_id, digest))
    for path, item_id, digest in pending:
        backfill.deliver_one(root, item_id, path, digest, plan="live")
        print(f"{item_id}: remote ledger verified", flush=True)


if __name__ == "__main__":
    main()
