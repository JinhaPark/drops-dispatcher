#!/usr/bin/env python3
"""One-time, explicitly approved, ordered backfill. No research or model calls."""
import argparse
import datetime
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = "data/artificial-engineering-backfill.json"
LEDGER = "data/discord-deliveries.json"
INFLIGHT = "data/discord-backfill-inflight.json"


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def is_backfill_id(item_id):
    match = re.fullmatch(r"artificial-engineering:edition-(\d+)", item_id)
    return bool(match and 1 <= int(match[1]) <= 64)


def already_completed(root, manifest):
    if manifest.get("status") != "active":
        return False
    items = validate_manifest(root, manifest)
    ledger = read_json(root / LEDGER, {})
    if read_json(root / INFLIGHT, {}):
        return False
    return all(item["status"] == "ready" and
               ledger.get(f'artificial-engineering:edition-{item["edition_number"]}', {}).get("status") == "complete" and
               ledger[f'artificial-engineering:edition-{item["edition_number"]}']["sha256"] == item["markdown_sha256"]
               for item in items)


def read_json(path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def frontmatter(text):
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        raise ValueError("Missing front matter")
    header, body = text[4:].split("\n---\n", 1)
    fields = {}
    for line in header.splitlines():
        if not line.strip():
            continue
        key, value = line.split(":", 1)
        if key in fields:
            raise ValueError("Duplicate front matter field")
        fields[key] = value.strip().strip('"').strip("'")
    return fields, body


def validate_article(root, item):
    n = item["edition_number"]
    path = item["markdown_path"]
    if not re.fullmatch(r"articles/artificial-engineering/\d{4}-\d{2}-\d{2}-edition-" + str(n) + r"\.md", path):
        raise ValueError(f"Invalid article path for Edition {n}")
    text = (root / path).read_text(encoding="utf-8")
    if sha(text) != item["markdown_sha256"]:
        raise ValueError(f"Unreviewed content change: Edition {n}")
    fields, body = frontmatter(text)
    required = {"id": f"artificial-engineering:edition-{n}", "source_id": "artificial-engineering",
                "edition_number": str(n), "author": "André Lindenberg", "status": "ready",
                "editorial_version": "ko-300eojeol-v1", "roundup_verified": "true"}
    for key, value in required.items():
        if fields.get(key) != value:
            raise ValueError(f"Invalid {key}: Edition {n}")
    for key in ("canonical_url", "published_at", "source_sha256"):
        if fields.get(key) != item.get(key):
            raise ValueError(f"Manifest provenance mismatch: {key}")
    date = datetime.date.fromisoformat(fields["published_at"]).isoformat()
    if not path.endswith(f"{date}-edition-{n}.md"):
        raise ValueError("Publication date/path mismatch")
    if not fields["canonical_url"].startswith("https://www.linkedin.com/pulse/"):
        raise ValueError("Unexpected canonical source")
    if not re.fullmatch(r"[0-9a-f]{64}", fields["source_sha256"]):
        raise ValueError("Full source digest is required")
    if not item.get("edition_evidence") or not item.get("roundup_evidence"):
        raise ValueError("Missing reviewed source evidence")
    sections = body.split("### 주간 GitHub 및 기술 프로젝트")
    if len(sections) != 2:
        raise ValueError("Missing roundup section")
    paragraphs = [p.strip() for p in sections[0].strip().split("\n\n") if p.strip()]
    if len(paragraphs) < 5 or not paragraphs[0].startswith("# ["):
        raise ValueError("Missing title or summary")
    summary = paragraphs[2:]
    count = len(" ".join(summary).split())
    if not 3 <= len(summary) <= 5 or not 250 <= count <= 350:
        raise ValueError(f"Summary length invalid: {count} eojeol/{len(summary)} paragraphs")
    listed = [line for line in sections[1].splitlines() if line.startswith("- ")]
    projects = item.get("projects", [])
    if len(listed) != len(projects) or len(projects) != item["roundup_count"]:
        raise ValueError("Roundup count mismatch")
    for line, project in zip(listed, projects):
        if project["name"] not in line or f'({project["url"]})' not in line:
            raise ValueError("Roundup name/link mismatch")
    return fields["id"], text


def validate_manifest(root, manifest):
    if manifest.get("status") not in ("held", "active"):
        raise ValueError("Unknown backfill activation state")
    if manifest.get("source_id") != "artificial-engineering" or manifest.get("range") != [1, 64]:
        raise ValueError("Unexpected backfill scope")
    items = manifest["editions"]
    if [item["edition_number"] for item in items] != list(range(1, 65)):
        raise ValueError("Manifest must enumerate Edition 1 through 64 exactly once in order")
    for item in items:
        if item["status"] == "ready":
            validate_article(root, item)
    return items


def merge_ledgers(remote, local):
    """Never discard remote successes or silently reconcile uncertainty."""
    merged = dict(remote)
    for key, new in local.items():
        old = merged.get(key)
        if old is None or old == new:
            merged[key] = new
            continue
        if old["sha256"] != new["sha256"] or old["total"] != new["total"]:
            raise RuntimeError(f"Ledger identity conflict: {key}")
        a, b = old["messages"], new["messages"]
        if a != b[:len(a)] and b != a[:len(b)]:
            raise RuntimeError(f"Discord message ID conflict: {key}")
        if "uncertain" in (old["status"], new["status"]):
            raise RuntimeError(f"Uncertain ledger requires reconciliation: {key}")
        chosen = old if len(a) > len(b) else new
        if old["status"] == "complete":
            chosen = old
        elif new["status"] == "complete":
            chosen = new
        merged[key] = chosen
    return merged


def git(*args, root=ROOT, data=None, env=None, check=True):
    return subprocess.run(["git", *args], cwd=root, input=data, text=True,
                          capture_output=True, check=check, env=env).stdout.strip()


def remote_json(root, ref, path, default):
    value = subprocess.run(["git", "show", f"{ref}:{path}"], cwd=root, text=True, capture_output=True)
    if value.returncode:
        if git("ls-tree", ref, "--", path, root=root):
            raise RuntimeError(f"Could not read remote checkpoint: {path}")
        return default
    return json.loads(value.stdout)


def persist(root, expected_marker, marker):
    """Commit only ledger and crash marker onto latest main; retain other changes."""
    local = read_json(root / LEDGER, {})
    for attempt in range(5):
        git("fetch", "origin", "main", root=root)
        parent = git("rev-parse", "origin/main", root=root)
        remote_marker = remote_json(root, parent, INFLIGHT, {})
        if remote_marker not in (expected_marker, marker):
            raise RuntimeError("Another in-flight delivery requires reconciliation")
        merged = merge_ledgers(remote_json(root, parent, LEDGER, {}), local)
        with tempfile.TemporaryDirectory() as temp:
            env = {**os.environ, "GIT_INDEX_FILE": str(pathlib.Path(temp) / "index")}
            git("read-tree", parent, root=root, env=env)
            for path, value in ((LEDGER, merged), (INFLIGHT, marker)):
                payload = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
                blob = git("hash-object", "-w", "--stdin", root=root, data=payload)
                git("update-index", "--add", "--cacheinfo", f"100644,{blob},{path}", root=root, env=env)
            tree = git("write-tree", root=root, env=env)
            commit = git("commit-tree", tree, "-p", parent, "-m", "chore: checkpoint ordered Discord backfill", root=root)
        push = subprocess.run(["git", "push", "origin", f"{commit}:refs/heads/main"], cwd=root, capture_output=True, text=True)
        git("fetch", "origin", "main", root=root)
        saved_ledger = remote_json(root, "origin/main", LEDGER, {})
        # A lost push response must not cause another Discord POST.
        if (remote_json(root, "origin/main", INFLIGHT, {}) == marker and
                all(saved_ledger.get(k) == v for k, v in merged.items())):
            (root / LEDGER).write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n")
            (root / INFLIGHT).write_text(json.dumps(marker, indent=2) + "\n")
            return
        if push.returncode == 0:
            raise RuntimeError("Remote ledger verification failed; stop before next edition")
    raise RuntimeError("Could not persist ledger; remote in-flight marker blocks replay")



def deliver_one(root, item_id, article_path, digest, *, text=None,
                checkpoint=persist, invoke=subprocess.run, plan=None):
    """One article, one remotely verified transaction; used by backfills and live feeds.

    A remotely committed in-flight marker is the fence before Discord POST.
    Local per-chunk IDs are saved by send.py and copied to the remote ledger
    on success or best-effort on failure. The marker remains on any ambiguity.
    """
    if read_json(root / INFLIGHT, {}):
        raise RuntimeError("Prior in-flight delivery requires manual reconciliation")
    if text is None:
        text = pathlib.Path(article_path).read_text(encoding="utf-8")
    if sha(text) != digest:
        raise RuntimeError(f"Article changed before delivery: {item_id}")
    previous = read_json(root / LEDGER, {}).get(item_id)
    if previous:
        if previous.get("sha256") != digest or previous.get("status") != "complete":
            raise RuntimeError(f"Delivery requires reconciliation: {item_id}")
        return False

    marker = {"id": item_id, "sha256": digest,
              "run_id": os.environ.get("GITHUB_RUN_ID", "local")}
    if plan:
        marker["plan"] = plan
    # Never POST if the pre-send remote commit/push/verification fails.
    checkpoint(root, {}, marker)
    command = [sys.executable, str(root / ".agents/skills/discord-feed/scripts/send.py"),
               "--file", str(article_path), "--id", item_id,
               "--state", str(root / LEDGER)]
    try:
        result = invoke(command, cwd=root)
    except BaseException:
        # Do not clear the remote marker. Preserve locally known chunk IDs.
        checkpoint(root, marker, marker)
        raise
    record = read_json(root / LEDGER, {}).get(item_id, {})
    messages = record.get("messages", [])
    total = record.get("total", 0)
    complete = (result.returncode == 0 and record.get("sha256") == digest
                and record.get("status") == "complete"
                and isinstance(total, int) and total > 0
                and isinstance(messages, list) and len(messages) == total
                and all(isinstance(msg, dict)
                        and msg.get("index") == index
                        and msg.get("message_id") for index, msg in enumerate(messages)))
    if not complete:
        # If this checkpoint fails, the original remote in-flight marker still
        # blocks replay, while the runner's failure artifact retains local IDs.
        checkpoint(root, marker, marker)
        raise RuntimeError(f"Delivery incomplete or uncertain: {item_id}; reconcile, do not retry")
    # Any push/verification failure here is fatal; never send the next article.
    checkpoint(root, marker, {})
    return True


def deliver(root, manifest, checkpoint=persist, invoke=subprocess.run):
    items = validate_manifest(root, manifest)
    if manifest.get("status") != "active":
        print("Backfill held:", manifest.get("status"))
        return
    if read_json(root / INFLIGHT, {}):
        raise RuntimeError("Prior in-flight delivery must be reconciled; do not rerun blindly")
    for item in items:
        n = item["edition_number"]
        if item["status"] != "ready":
            print(f"Stopped before unverified Edition {n}")
            return
        item_id, text = validate_article(root, item)
        deliver_one(root, item_id, root / item["markdown_path"], sha(text),
                    text=text, checkpoint=checkpoint, invoke=invoke,
                    plan=MANIFEST)
        print(f"Edition {n}: remote ledger verified", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    manifest = read_json(ROOT / MANIFEST)
    if not manifest:
        print("No backfill manifest")
        return
    if args.validate_only:
        items = validate_manifest(ROOT, manifest)
        print("Validated", sum(i["status"] == "ready" for i in items), "ready editions")
    else:
        deliver(ROOT, manifest)


if __name__ == "__main__":
    main()
