---
name: discord-feed
description: Route completed AI articles and scheduled finance or general Markdown reports to dedicated Discord channels with table-safe rendering, message splitting, durable deduplication, and per-message receipts. Use when publishing or verifying content in JinhaPark/drops; do not use it to research or write the content.
---

# Discord Feed

Accept final Markdown, a stable item ID, its repository path, and an environment-provided webhook. Keep research and editorial work outside this skill. Read [references/delivery-contract.md](references/delivery-contract.md) before changing routing, rendering, workflow triggers, checkpoint behavior, or ledgers.

## Route

| Path | Secret | Ledger |
| --- | --- | --- |
| `articles/**/*.md` | `DISCORD_WEBHOOK_URL` | `data/discord-deliveries.json` |
| `reports/finance/**/*.md` | `DISCORD_WEBHOOK_URL_FINANCE` | `data/discord-report-deliveries.json` |
| `reports/general/**/*.md` | `DISCORD_WEBHOOK_URL_GENERAL` | `data/discord-report-deliveries.json` |

Reject every other path and never fall back between secrets.

## Recipe

~~~text
RECIPE route_completed_output(final_markdown, category, stable_id, path):
    REQUIRE category IN [ai_article, finance, general]
    route := RESOLVE_EXACT_PATH(path, category)
    branch := main

    COMMIT_IMMUTABLE_SOURCE(branch, path, final_markdown)
    # Public dispatcher delivers later; authoring never invokes the webhook.
    RETURN source_commit, delivery_status = unconfirmed

RECIPE dispatch_approved_source_in_public_runner(stable_id, path):
    route := RESOLVE_EXACT_PATH(path)
    rendered := RENDER_FOR_DISCORD(
        final_markdown,
        gfm_pipe_tables = ADAPTIVE_MOBILE_RENDERING,
        compact_numeric = ALIGNED_FENCED_BLOCK_MAX_36_DISPLAY_COLUMNS,
        descriptive_or_wide = VERTICAL_LABELED_ENTRIES,
        repeat_compact_header_when_split = true
    )
    chunks := SPLIT_WITH_BALANCED_FENCES(rendered, max_utf16_units = 1900)
    receipts := SEND_AND_CHECKPOINT(chunks, route.secret, stable_id)

    REQUIRE every receipt has discord_message_id
    REQUIRE route.ledger[stable_id].status == complete
    RETURN source_commit, workflow, ledger_receipt
~~~

For a conditional task whose correct result is silence, create no report file and invoke no webhook. Preserve unrelated article and report files and both separate ledgers on private `main`.

## Invoke

- AI article: `python .agents/skills/discord-feed/scripts/send.py --file PATH --id STABLE_ID --state data/discord-deliveries.json`
- Scheduled reports: `python .agents/skills/discord-feed/scripts/deliver_reports.py --root reports --state data/discord-report-deliveries.json`
- Preview rendering and chunk sizes by adding `--dry-run`; never require a webhook for a dry run.

The sender hashes and preserves the original Markdown. At delivery time, short 2–3-column tables with predominantly numeric cells become aligned code blocks, with a maximum of 36 display columns and Hangul/CJK-aware width. Wide or descriptive tables become vertical labeled Markdown entries without pipe delimiters. A long compact table repeats its header in separately balanced code blocks. Existing fenced blocks and non-table pipes remain unchanged. Descriptive text is preserved, not truncated. Articles and reports share private `drops/main`, with independent ledger and in-flight paths. GitHub Actions runs canonical code from public `drops-dispatcher/main`, never executable code from private content.

## Accept

- Every chunk is at most 2,000 UTF-16 units; use 1,900 as the operational limit.
- No chunk cuts through a fenced block; table fences remain balanced.
- The source SHA-256 remains the delivery identity; record the rendered SHA-256 for diagnostics.
- Every successful chunk has a Discord message ID and an atomic ledger checkpoint.
- Same ID and source digest skips; a changed digest under the same ID requires explicit revision approval.
- An ambiguous response becomes `uncertain` and blocks blind replay.
- Mentions are disabled, credentials never enter output, and rate limits use bounded retries.
- Production success requires the completed durable ledger entry, not merely a Git commit or workflow start.
