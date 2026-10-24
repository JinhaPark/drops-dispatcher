#!/usr/bin/env python3
"""Exactly two user-approved historical preview posts, never a generic backfill."""
import argparse
import datetime
import pathlib
import re

import backfill
from editorial_policy import SUPPORTED_EDITORIAL_VERSIONS

MANIFEST = "data/one-time-preview-20261023.json"

# These exact two articles were explicitly approved 2026-10-23.
# Keep the allowlist in code so a changed manifest cannot expand the approval.
APPROVED = (
    ("simon-willison:battledrones", "simon-willison",
     "2026-10-20", "Simon Willison",
     "https://simonwillison.net/2026/Oct/20/battledrones/",
     "articles/simon-willison/2026-10-20-battledrones.md"),
    ("hamel-husain:how-to-use-decision-models-for-evals", "hamel-husain",
     "2026-10-20", "Hamel Husain and Antaripa Saha",
     "https://hamelhusain.substack.com/p/how-to-use-decision-models-for-evals",
     "articles/hamel-husain/2026-10-20-how-to-use-decision-models-for-evals.md"),
)
FIELDS = ("id", "source_id", "published_at", "author", "canonical_url", "markdown_path")


def read_manifest(root):
    return backfill.read_json(pathlib.Path(root) / MANIFEST)


def validate(root, manifest):
    if not isinstance(manifest, dict) or (
        manifest.get("schema_version") != 1
        or manifest.get("kind") != "one-time-simon-hamel-preview-20261023"
        or manifest.get("authorized_at") != "2026-10-23"
        or manifest.get("status") not in ("held", "active")
    ):
        raise ValueError("Unknown one-time preview approval")
    items = manifest.get("items")
    if not isinstance(items, list) or len(items) != 2:
        raise ValueError("One-time approval must contain exactly two posts")
    approved = [dict(zip(FIELDS, row)) for row in APPROVED]
    for item, expected in zip(items, approved):
        if not isinstance(item, dict) or any(item.get(k) != v for k, v in expected.items()):
            raise ValueError("One-time preview scope or canonical metadata changed")
        if set(item) != set(FIELDS) | {"markdown_sha256"}:
            raise ValueError("Unexpected one-time preview metadata")
        digest = item["markdown_sha256"]
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("Missing reviewed Markdown SHA-256")
        path = pathlib.Path(root) / item["markdown_path"]
        text = path.read_text(encoding="utf-8")
        if backfill.sha(text) != digest:
            raise ValueError("One-time preview Markdown changed since review")
        fields, body = backfill.frontmatter(text)
        for key in ("id", "source_id", "published_at", "author", "canonical_url"):
            if fields.get(key) != expected[key]:
                raise ValueError("One-time preview front matter mismatch: " + key)
        if fields.get("status") != "ready" or fields.get("editorial_version") not in SUPPORTED_EDITORIAL_VERSIONS:
            raise ValueError("One-time preview editorial state incorrect")
        datetime.date.fromisoformat(fields["published_at"])
        paragraphs = [p.strip() for p in body.strip().split("\n\n") if p.strip()]
        if len(paragraphs) != 6 or not paragraphs[0].startswith("# [") or (
            f"]({item['canonical_url']})" not in paragraphs[0]
        ):
            raise ValueError("One-time preview title or paragraph structure invalid")
        word_count = len(" ".join(paragraphs[2:]).split())
        if not 250 <= word_count <= 350:
            raise ValueError("One-time preview summary must be 250-350 Korean words")
    return items


def already_completed(root, manifest):
    items = validate(root, manifest)
    if manifest["status"] != "active" or backfill.read_json(pathlib.Path(root) / backfill.INFLIGHT, {}):
        return False
    ledger = backfill.read_json(pathlib.Path(root) / backfill.LEDGER, {})
    return all(
        ledger.get(item["id"], {}).get("status") == "complete"
        and ledger[item["id"]]["sha256"] == item["markdown_sha256"]
        for item in items
    )


def deliver(root, manifest, checkpoint=backfill.persist, invoke=None):
    # Preflight both posts and the whole approval BEFORE the first remote POST.
    items = validate(root, manifest)
    if manifest["status"] != "active":
        print("One-time preview held; no delivery")
        return
    if backfill.read_json(pathlib.Path(root) / backfill.INFLIGHT, {}):
        raise RuntimeError("Unreconciled remote delivery marker; stop")
    ledger = backfill.read_json(pathlib.Path(root) / backfill.LEDGER, {})
    for item in items:
        old = ledger.get(item["id"])
        if old is not None and (old.get("status") != "complete" or old.get("sha256") != item["markdown_sha256"]):
            raise RuntimeError("Existing preview delivery requires reconciliation")
    # Never touch the ongoing live monitor baseline or historical backfill plans.
    kwargs = {"checkpoint": checkpoint, "plan": MANIFEST}
    if invoke is not None:
        kwargs["invoke"] = invoke
    for item in items:
        path = pathlib.Path(root) / item["markdown_path"]
        backfill.deliver_one(root, item["id"], path, item["markdown_sha256"], **kwargs)
        print("One-time preview verified in durable delivery ledger:", item["id"], flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    options = parser.parse_args()
    root = backfill.ROOT
    manifest = read_manifest(root)
    if options.validate_only:
        print("Validated one-time approved previews:", len(validate(root, manifest)))
    else:
        deliver(root, manifest)


if __name__ == "__main__":
    main()
