#!/usr/bin/env python3
"""One-time reviewed Devansh recent-five approval with a paywalled issue held.

Only the exact five official archive entries visible at authorization time
are in scope. The sender never researches, summarizes, or guesses paid text.
"""
import argparse
import datetime
import pathlib
import re

import backfill
from editorial_policy import SUPPORTED_EDITORIAL_VERSIONS

MANIFEST = "data/devansh-recent-five-20261024.json"
AUTHORIZED_AT = "2026-10-24T17:16:00Z"
SOURCE = "devansh-ai-made-simple"
AUTHOR = "Devansh"

# Permanently bind the one-time user approval to the official archive five.
# Order is oldest to newest; do not substitute the unlisted October 1 post.
APPROVED = (
    ("2026-09-06", "the-dirty-math-behind-100-renewable"),
    ("2026-09-18", "how-will-ai-models-make-money"),
    ("2026-09-27", "the-ai-bubble-isnt-where-you-think"),
    ("2026-10-11", "what-everyone-misses-about-animal"),
    ("2026-10-19", "training-your-own-models-is-an-incredibly"),
)
BASE = "https://www.artificialintelligencemadesimple.com/p/"
FIELDS = ("id", "source_id", "published_at", "author", "canonical_url", "markdown_path")
HEX = re.compile(r"[0-9a-f]{64}\Z")


def expected_row(date, slug):
    return {
        "id": SOURCE + ":" + slug,
        "source_id": SOURCE,
        "published_at": date,
        "author": AUTHOR,
        "canonical_url": BASE + slug,
        "markdown_path": "articles/" + SOURCE + "/" + date + "-" + slug + ".md",
    }


def read_manifest(root):
    return backfill.read_json(pathlib.Path(root) / MANIFEST)


def validate(root, manifest):
    if not isinstance(manifest, dict) or (
        manifest.get("schema_version") != 1
        or manifest.get("kind") != "one-time-devansh-recent-five-20261024"
        or manifest.get("authorized_at") != AUTHORIZED_AT
        or manifest.get("status") not in ("held", "active")
    ):
        raise ValueError("Unknown Devansh one-time approval")
    items = manifest.get("items")
    if not isinstance(items, list) or len(items) != len(APPROVED):
        raise ValueError("Devansh approval covers exactly five posts")
    for item, (date, slug) in zip(items, APPROVED):
        expected = expected_row(date, slug)
        if not isinstance(item, dict) or any(item.get(k) != v for k, v in expected.items()):
            raise ValueError("Devansh approval scope or canonical metadata changed")
        if item.get("status") == "held":
            if set(item) != set(FIELDS) | {"status", "markdown_sha256", "reason"}:
                raise ValueError("Unexpected held Devansh metadata")
            if item["markdown_sha256"] is not None or item["reason"] != "paywalled_full_text_unavailable":
                raise ValueError("Held Devansh post must not masquerade as reviewed")
            continue
        if item.get("status") != "ready" or (
            set(item) != set(FIELDS) | {"status", "markdown_sha256", "source_review"}
        ) or item.get("source_review") != "complete_official_html":
            raise ValueError("Unreviewed Devansh post")
        digest = item["markdown_sha256"]
        if not isinstance(digest, str) or not HEX.fullmatch(digest):
            raise ValueError("Missing Devansh reviewed Markdown SHA-256")
        article = pathlib.Path(root) / item["markdown_path"]
        document = article.read_text(encoding="utf-8")
        if backfill.sha(document) != digest:
            raise ValueError("Devansh Markdown changed since review")
        fields, body = backfill.frontmatter(document)
        for key, value in expected.items():
            if key in ("markdown_path",):
                continue
            if fields.get(key) != value:
                raise ValueError("Devansh article provenance mismatch: " + key)
        if fields.get("status") != "ready" or fields.get("editorial_version") not in SUPPORTED_EDITORIAL_VERSIONS:
            raise ValueError("Devansh article editorial state mismatch")
        datetime.date.fromisoformat(fields["published_at"])
        paragraphs = [p.strip() for p in body.strip().split("\n\n") if p.strip()]
        if len(paragraphs) != 6 or not paragraphs[0].startswith("# [") or (
            "](" + expected["canonical_url"] + ")" not in paragraphs[0]
        ) or not paragraphs[1].startswith(date + " · Devansh"):
            raise ValueError("Devansh article title or summary format mismatch")
        words = len(" ".join(paragraphs[2:]).split())
        if not 250 <= words <= 350:
            raise ValueError("Devansh Korean summary must have 250-350 words")
    return items


def already_completed(root, manifest):
    items = validate(root, manifest)
    if manifest["status"] != "active" or backfill.read_json(pathlib.Path(root) / backfill.INFLIGHT, {}):
        return False
    ledger = backfill.read_json(pathlib.Path(root) / backfill.LEDGER, {})
    return all(
        ledger.get(item["id"], {}).get("status") == "complete"
        and ledger[item["id"]]["sha256"] == item["markdown_sha256"]
        for item in items if item["status"] == "ready"
    )


def deliver(root, manifest, checkpoint=backfill.persist, invoke=None):
    items = validate(root, manifest)  # Preflight all reviewed files before any external POST.
    if manifest["status"] != "active":
        print("Devansh one-time authorization held; no delivery")
        return
    if backfill.read_json(pathlib.Path(root) / backfill.INFLIGHT, {}):
        raise RuntimeError("Unreconciled remote delivery marker; stop")
    ledger = backfill.read_json(pathlib.Path(root) / backfill.LEDGER, {})
    for item in items:
        old = ledger.get(item["id"])
        if old is not None and (
            item["status"] != "ready" or old.get("status") != "complete"
            or old.get("sha256") != item["markdown_sha256"]
        ):
            raise RuntimeError("Existing Devansh delivery requires reconciliation")
    for item in items:
        if item["status"] != "ready":
            print("Devansh original held, no send:", item["id"], item["reason"], flush=True)
            continue
        if item["id"] in ledger:
            continue
        options = {"checkpoint": checkpoint, "plan": MANIFEST}
        if invoke is not None:
            options["invoke"] = invoke
        backfill.deliver_one(root, item["id"], pathlib.Path(root) / item["markdown_path"],
                             item["markdown_sha256"], **options)
        print("Devansh Discord remote ledger verified:", item["id"], flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    root = backfill.ROOT
    manifest = read_manifest(root)
    if args.validate_only:
        items = validate(root, manifest)
        print("Validated Devansh recent-five manifest:",
              sum(i["status"] == "ready" for i in items), "ready,",
              sum(i["status"] == "held" for i in items), "held")
    else:
        deliver(root, manifest)


if __name__ == "__main__":
    main()
