# Private-data migration and dispatcher cutover

## Current authoritative layout

- `JinhaPark/drops-dispatcher` (public `main`): delivery scripts, tests, Actions workflows, and Discord webhook secrets in **Actions secrets only**. No Markdown articles, report content, or state files in the working Git tree.
- `JinhaPark/drops` (private `main`): `articles/**`, `reports/finance/**`, `reports/general/**`, `data/**`, `sources.json`. Articles use `data/discord-deliveries.json`; reports use `data/discord-report-deliveries.json`, with independent in-flight markers.
- GitHub Actions fetches a verified private snapshot via the GitHub Contents/Git Data REST API. `DROPS_DATA_ROOT` is mandatory and points to that ephemeral snapshot, separate from the code checkout. Each pre-send and post-send checkpoint commits to private `JinhaPark/drops/main` through `GH_TOKEN` and `DROPS_PRIVATE_REST=1`.
- The scheduled publisher writes Markdown to private `main`; it never sends Discord directly. No eligible artifact means no placeholder and no Discord post.

## Immutable source snapshots

- Public historical news base: `65b7b02802fe37e8409a66d84ed97b9d9ba83b73` (137 articles, approval manifests, monitoring baseline, original 138-record news ledger).
- Public historical report base: `65e3ec7ab08f6668cf69a22a669c2fab73ef57c4` (10 report Markdown files, original 10-record report ledger).
- The private `main` already contains these 137 articles, the same source and approval blobs, the 10 report files, a merged 12-record report ledger, and an independently advanced 139-record article ledger. The **raw, byte-exact** original ledgers are preserved as `data/migration/20261027-original-{article,report}-deliveries.json`; do not overwrite newer receipts with historical snapshots.

## Offline staging and verification (never resends)

Use separate local, pinned, read-only worktrees for the two source commits. Verify the checkout commit IDs before use. Run in a private working directory on an authorized machine, not in a public Actions log or artifact:

```bash
git -C dispatcher rev-parse 65b7b02802fe37e8409a66d84ed97b9d9ba83b73
git -C dispatcher rev-parse 65e3ec7ab08f6668cf69a22a669c2fab73ef57c4
git -C dispatcher worktree add --detach ../news-snapshot 65b7b02802fe37e8409a66d84ed97b9d9ba83b73
git -C dispatcher worktree add --detach ../report-snapshot 65e3ec7ab08f6668cf69a22a669c2fab73ef57c4
python dispatcher/scripts/migrate_private_data.py \
  --news news-snapshot --reports report-snapshot --private drops-private
python dispatcher/scripts/migrate_private_data.py \
  --news news-snapshot --reports report-snapshot --private drops-private --verify-only
```

The `drops-private` destination must be an authenticated checkout of the private repository (or an equivalent isolated local working tree). The script preflights all paths, rejects conflicting content, unions receipts **without modifying message IDs**, preserves both original ledgers by exact bytes, and compares SHA-256 for all staged files before and after. It makes **no Git commits, remote pushes, webhook calls, or external network requests**. Any later private commit must be reviewed and pushed with a fast-forward check by an authorized operator. Never add the original public snapshots back to the public `main`; do not rewrite the historical public Git object graph.

## External configuration and live verification

Only the `drops-dispatcher` Actions settings require `DROPS_APP_ID`, `DROPS_APP_PRIVATE_KEY`, and the routed `DISCORD_WEBHOOK_URL`, `DISCORD_WEBHOOK_URL_FINANCE`, `DISCORD_WEBHOOK_URL_GENERAL`. The GitHub App installation used by Actions must be granted access to **private `JinhaPark/drops`** with `Contents: read/write`; the ChatGPT GitHub connector having access does *not* prove these repository Actions secrets or installation permissions are configured. Never print token/key/webhook values.

Validate manually in `mode=validate` first, inspect workflow results without sharing private content, and only enable actual delivery when the private ledger and empty in-flight markers are verified. Production `report-feed` and `discord-feed` schedules are **transport only**. If private authentication, snapshot consistency, checkpoint commit, or remote receipt verification fails, stop before further POSTs. A completed receipt must never trigger re-send.

Focused offline regression:

```bash
python -m unittest discover -s tests -p test_private_migration.py -v
python -m unittest discover -s tests -p test_private_repo.py -v
python -m unittest discover -s tests -p test_private_reports.py -v
python -m unittest discover -s tests -p test_live_checkpoints.py -v
```

These are scoped tests and do not perform full historical backfills, contact Discord, or require live Actions credentials.
