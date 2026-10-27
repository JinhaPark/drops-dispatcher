#!/usr/bin/env python3
"""Delete one immutable, superseded private branch after verifying its complete contents."""
from private_repo import ApiError, DEFAULT_REPO, api, ref_head, tree_snapshot

BRANCH = "automation/report-feed"
EXPECTED = "4abcec661561b210fbc611cdff994e391a841967"
LEDGERS = ("data/discord-report-deliveries.json", "data/discord-report-inflight.json")
OLD_DOCS = frozenset(("AGENTS.md", "README.md",
    ".agents/skills/discord-feed/SKILL.md",
    ".agents/skills/discord-feed/references/delivery-contract.md"))


def retire():
    main_sha = ref_head(DEFAULT_REPO, "main")
    try:
        old_sha = ref_head(DEFAULT_REPO, BRANCH)
    except ApiError as exc:
        if exc.status == 404:
            print("Legacy private report branch is already absent")
            return
        raise
    if old_sha != EXPECTED:
        raise RuntimeError("Legacy branch changed; refuse deletion")
    _, main = tree_snapshot(DEFAULT_REPO, main_sha)
    _, old = tree_snapshot(DEFAULT_REPO, old_sha)
    if set(old) - set(main):
        raise RuntimeError("Legacy branch has unique paths")
    if any(p.startswith("reports/") for p in old):
        raise RuntimeError("Legacy branch has reports")
    if any(p not in old or p not in main or old[p]["sha"] != main[p]["sha"]
           for p in LEDGERS):
        raise RuntimeError("Legacy ledger is not preserved on main")
    changes = {p for p in old if old[p]["sha"] != main[p]["sha"]}
    if changes - OLD_DOCS:
        raise RuntimeError("Legacy branch has unique changed content")
    if ref_head(DEFAULT_REPO, BRANCH) != EXPECTED:
        raise RuntimeError("Legacy branch moved during comparison")
    api(DEFAULT_REPO, "git/refs/heads/" + BRANCH, "DELETE")
    try:
        ref_head(DEFAULT_REPO, BRANCH)
    except ApiError as exc:
        if exc.status != 404:
            raise
    else:
        raise RuntimeError("Legacy branch was not deleted")
    print("Verified obsolete branch deleted; no sources or receipts changed")


if __name__ == "__main__":
    retire()
