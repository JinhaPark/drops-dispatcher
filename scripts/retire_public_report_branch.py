#!/usr/bin/env python3
"""Retire the obsolete *public* report ref only after byte-identical private migration checks.

This script never sends Discord messages or writes ledgers. It deletes exactly one
pinned public ref; the private main branch and historical Git objects are untouched.
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

PUBLIC = "JinhaPark/drops-dispatcher"
PRIVATE = "JinhaPark/drops"
BRANCH = "automation/report-feed"
EXPECTED_BRANCH_SHA = "65e3ec7ab08f6668cf69a22a669c2fab73ef57c4"
NEWS_SOURCE_SHA = "65b7b02802fe37e8409a66d84ed97b9d9ba83b73"
ARCHIVED_ARTICLES = "data/migration/20261027-original-article-deliveries.json"
ARCHIVED_REPORTS = "data/migration/20261027-original-report-deliveries.json"


class ApiError(RuntimeError):
    def __init__(self, status):
        self.status = status
        super().__init__(f"GitHub REST request failed (HTTP {status})")


def api(repo, path, token, method="GET"):
    url = f"https://api.github.com/repos/{repo}/{path}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "drops-public-branch-retirement",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            body = response.read()
            return json.loads(body) if body else None
    except urllib.error.HTTPError as exc:
        raise ApiError(exc.code) from None


def get_ref(repo, branch, token):
    path = "git/ref/heads/" + urllib.parse.quote(branch, safe="/")
    try:
        return api(repo, path, token)["object"]["sha"]
    except ApiError as exc:
        if exc.status == 404:
            return None
        raise


def get_tree(repo, ref, token):
    payload = api(repo, f"git/trees/{ref}?recursive=1", token)
    if payload.get("truncated"):
        raise RuntimeError("Source tree was truncated; refusing to retire branch")
    return {entry["path"]: entry["sha"] for entry in payload["tree"]
            if entry["type"] == "blob"}


def verify_migration(old_reports, old_news, private_main, public_main):
    """Checks exact Git blob IDs, not report titles, aggregate counts, or ledger totals."""
    reports = {path: sha for path, sha in old_reports.items()
               if path.startswith("reports/") and path.endswith(".md")}
    articles = {path: sha for path, sha in old_news.items()
                if path.startswith("articles/") and path.endswith(".md")}
    if len(reports) != 10 or len(articles) != 137:
        raise RuntimeError("Pinned source inventory changed; refusing ref deletion")
    for path, sha in [*reports.items(), *articles.items()]:
        if private_main.get(path) != sha:
            raise RuntimeError("A historical content blob is missing or changed in private main")
    for original, archive, expected in (
        (old_reports, ARCHIVED_REPORTS, "data/discord-report-deliveries.json"),
        (old_news, ARCHIVED_ARTICLES, "data/discord-deliveries.json"),
    ):
        if not original.get(expected) or private_main.get(archive) != original[expected]:
            raise RuntimeError("The original delivery ledger is not preserved byte-for-byte")
    if not all(path in private_main for path in (
        "data/discord-deliveries.json",
        "data/discord-report-deliveries.json",
        "data/discord-backfill-inflight.json",
        "data/discord-report-inflight.json",
    )):
        raise RuntimeError("The active private delivery state is incomplete")
    if any(path.startswith(("articles/", "reports/", "data/")) for path in public_main):
        raise RuntimeError("Public main contains content or delivery state")
    return len(articles), len(reports)


def retire():
    public_token = os.environ["GH_TOKEN"]
    private_token = os.environ["DROPS_TOKEN"]
    original_head = get_ref(PUBLIC, BRANCH, public_token)
    if original_head is None:
        print("Public legacy branch is already absent; no changes made")
        return
    if original_head != EXPECTED_BRANCH_SHA:
        raise RuntimeError("Public legacy branch moved; refusing deletion")
    private_head = get_ref(PRIVATE, "main", private_token)
    if not private_head:
        raise RuntimeError("Private main is not readable")
    public_head = get_ref(PUBLIC, "main", public_token)
    if not public_head:
        raise RuntimeError("Public main is not readable")
    counts = verify_migration(
        get_tree(PUBLIC, original_head, public_token),
        get_tree(PUBLIC, NEWS_SOURCE_SHA, public_token),
        get_tree(PRIVATE, private_head, private_token),
        get_tree(PUBLIC, public_head, public_token),
    )
    if get_ref(PUBLIC, BRANCH, public_token) != EXPECTED_BRANCH_SHA:
        raise RuntimeError("Public legacy branch moved during verification")
    api(PUBLIC, "git/refs/heads/" + BRANCH, public_token, method="DELETE")
    if get_ref(PUBLIC, BRANCH, public_token) is not None:
        raise RuntimeError("Public branch deletion was not confirmed")
    print(f"Verified {counts[0]} articles and {counts[1]} reports in private main; "
          "public legacy ref deleted. No content or delivery state changed.")


if __name__ == "__main__":
    try:
        retire()
    except (ApiError, RuntimeError, KeyError, ValueError) as exc:
        print(f"Safe stop: {exc}", file=sys.stderr)
        sys.exit(1)
