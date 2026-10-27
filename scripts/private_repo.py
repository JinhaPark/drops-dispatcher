#!/usr/bin/env python3
"""Private GitHub content transport using the installation-token REST API.

Git operations are deliberately avoided: the private repository's Git HTTP
transport may reject an installation token even when its Contents API works.
Only the approved private repository may be accessed.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path, PurePosixPath
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_REPO = "JinhaPark/drops"
MAX_BLOB = 2 * 1024 * 1024
MAX_TOTAL = 32 * 1024 * 1024


class ApiError(RuntimeError):
    def __init__(self, status: int, endpoint: str):
        self.status = status
        super().__init__(f"GitHub API status {status} at {endpoint.split('?')[0]}")


def api(repo: str, endpoint: str, method: str = "GET", payload=None):
    if repo != DEFAULT_REPO:
        raise ValueError("Unexpected private repository")
    token = os.environ.get("GH_TOKEN")
    if not token:
        raise RuntimeError("Missing GH_TOKEN installation token")
    url = "https://api.github.com/repos/" + repo + "/" + endpoint
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        url, data=data, method=method,
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "drops-private-transport",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read()
            return json.loads(body.decode("utf-8")) if body else {}
    except urllib.error.HTTPError as exc:
        raise ApiError(exc.code, endpoint) from None


def ref_head(repo: str, branch: str) -> str:
    name = urllib.parse.quote(branch, safe="/")
    return api(repo, "git/ref/heads/" + name)["object"]["sha"]


def tree_snapshot(repo: str, sha: str):
    commit = api(repo, "git/commits/" + sha)
    tree_sha = commit["tree"]["sha"]
    tree = api(repo, "git/trees/" + tree_sha + "?recursive=1")
    if tree.get("truncated"):
        raise RuntimeError("GitHub private tree is truncated; refuse incomplete snapshot")
    entries = {x["path"]: x for x in tree["tree"] if x["type"] == "blob"}
    return tree_sha, entries


def blob_bytes(repo: str, sha: str) -> bytes:
    blob = api(repo, "git/blobs/" + sha)
    if blob.get("encoding") != "base64":
        raise RuntimeError("Unexpected private Git blob encoding")
    value = base64.b64decode(blob["content"], validate=False)
    if len(value) > MAX_BLOB:
        raise RuntimeError("Oversized private Git blob")
    return value


def _safe_path(path: str) -> bool:
    parts = PurePosixPath(path).parts
    return bool(parts and all(x not in ("..", ".", "") for x in parts)
                and not path.startswith("/") and "\\" not in path)


def pull(repo: str, branch: str, destination: Path, groups: tuple[str, ...]):
    head = ref_head(repo, branch)
    _, entries = tree_snapshot(repo, head)
    selected = {
        name: entry for name, entry in entries.items()
        if _safe_path(name) and
        (any(name.startswith(group + "/") for group in groups)
         or ("sources" in groups and name == "sources.json"))
    }
    if "articles" in groups and not any(p.startswith("articles/") for p in selected):
        raise RuntimeError("No private Markdown articles found")
    size = 0
    for name, entry in sorted(selected.items()):
        if entry.get("mode") not in ("100644", "100755"):
            raise RuntimeError("Unexpected Git file mode in private snapshot")
        content = blob_bytes(repo, entry["sha"])
        size += len(content)
        if size > MAX_TOTAL:
            raise RuntimeError("Private snapshot exceeds maximum transport size")
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    if head != ref_head(repo, branch):
        raise RuntimeError("Private branch changed during snapshot; retry without sending")
    print(f"Verified private snapshot: {len(selected)} files from {branch}; no content logged")


def _remote_json(repo, entries, path):
    entry = entries.get(path)
    if entry is None:
        return {}
    return json.loads(blob_bytes(repo, entry["sha"]).decode("utf-8"))


def persist_state(root: Path, expected_marker: dict, marker: dict,
                  ledger_path: str, marker_path: str, merge_ledgers,
                  branch="main", repo=DEFAULT_REPO):
    """Atomically commit ledger+marker with an optimistic, fast-forward-only ref update."""
    local_path = root / ledger_path
    local_ledger = json.loads(local_path.read_text()) if local_path.exists() else {}
    for attempt in range(5):
        head = ref_head(repo, branch)
        base_tree, entries = tree_snapshot(repo, head)
        current_marker = _remote_json(repo, entries, marker_path)
        if current_marker not in (expected_marker, marker):
            raise RuntimeError("Unreconciled remote in-flight checkpoint")
        merged = merge_ledgers(_remote_json(repo, entries, ledger_path), local_ledger)
        ledger_text = json.dumps(merged, ensure_ascii=False, indent=2) + "\n"
        marker_text = json.dumps(marker, ensure_ascii=False, indent=2) + "\n"
        updates = []
        for path, content in ((ledger_path, ledger_text), (marker_path, marker_text)):
            blob = api(repo, "git/blobs", "POST", {"content": content, "encoding": "utf-8"})
            updates.append({"path": path, "mode": "100644", "type": "blob", "sha": blob["sha"]})
        tree = api(repo, "git/trees", "POST", {"base_tree": base_tree, "tree": updates})
        commit = api(repo, "git/commits", "POST", {
            "message": "chore: checkpoint private Discord delivery",
            "tree": tree["sha"], "parents": [head],
        })
        try:
            api(repo, "git/refs/heads/" + urllib.parse.quote(branch, safe="/"), "PATCH",
                {"sha": commit["sha"], "force": False})
        except ApiError as exc:
            if exc.status not in (409, 422):
                raise
        remote_head = ref_head(repo, branch)
        _, saved_entries = tree_snapshot(repo, remote_head)
        saved_marker = _remote_json(repo, saved_entries, marker_path)
        saved_ledger = _remote_json(repo, saved_entries, ledger_path)
        if saved_marker == marker and all(saved_ledger.get(k) == v for k, v in merged.items()):
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_text(ledger_text, encoding="utf-8")
            marker_file = root / marker_path
            marker_file.parent.mkdir(parents=True, exist_ok=True)
            marker_file.write_text(marker_text, encoding="utf-8")
            return
        if remote_head == commit["sha"]:
            raise RuntimeError("Private checkpoint verification mismatch; no more sends")
    raise RuntimeError("Private checkpoint concurrency conflict; stop")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["pull"])
    parser.add_argument("--branch", default="main")
    parser.add_argument("--destination", default="private-data")
    parser.add_argument("--groups", nargs="+", choices=["articles", "reports", "data", "sources"],
                        default=["articles", "data", "sources"])
    args = parser.parse_args()
    pull(DEFAULT_REPO, args.branch, Path(args.destination), tuple(args.groups))


if __name__ == "__main__":
    main()
