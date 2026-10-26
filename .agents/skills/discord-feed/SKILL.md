---
name: discord-feed
description: Route already completed AI articles and scheduled finance or general Markdown reports to their dedicated Discord channels, splitting messages safely and deduplicating with durable delivery ledgers. Does not fetch sources or write content.
---
# Discord Feed

## Scope
Input is final Markdown, a stable `item_id`, its repository path, and the Discord webhook credential available to the execution environment. Do not scrape, summarize, translate, or edit content. The caller owns research, editorial quality, and source verification.

## Routing contract

| Repository path | Content | Secret | Ledger |
| --- | --- | --- | --- |
| `articles/**/*.md` | Verified AI newsletter articles | `DISCORD_WEBHOOK_URL` | `data/discord-deliveries.json` |
| `reports/finance/**/*.md` | Markets, credit, valuation, CTA and semiconductor reports | `DISCORD_WEBHOOK_URL_FINANCE` | `data/discord-report-deliveries.json` |
| `reports/general/**/*.md` | Korean news, GitHub Trending and other general briefings | `DISCORD_WEBHOOK_URL_GENERAL` | `data/discord-report-deliveries.json` |

Reject paths outside this table. Never fall back from one webhook to another.

## Orchestration recipe

~~~text
RECIPE route_completed_output(final_markdown, task_slug, run_timestamp_utc, category):
    REQUIRE category IN [ai_article, finance, general]
    REQUIRE final_markdown equals the user-visible output bytes

    IF category == ai_article:
        path := articles/{source_id}/{published_date}-{stable_slug}.md
        branch := main
        webhook_env := DISCORD_WEBHOOK_URL
        ledger := data/discord-deliveries.json
    ELSE:
        route := finance IF category == finance ELSE general
        path := reports/{route}/{task_slug}/{run_timestamp_utc}.md
        branch := PIN_OR_CREATE("automation/report-feed", base = current_main)
        webhook_env := ROUTE(path)
        ledger := data/discord-report-deliveries.json

    COMMIT_IMMUTABLE_MARKDOWN(branch, path, final_markdown)
    workflow := RUN_SERIALIZED_DELIVERY(branch, path)
    chunks := SPLIT_EXACTLY(final_markdown, max_utf16_units = 1900)
    receipts := SEND_AND_CHECKPOINT(chunks, webhook_env, stable_id = PATH_ID(path))
    REQUIRE every receipt has discord_message_id
    REQUIRE ledger[PATH_ID(path)].status == complete
    RETURN commit, workflow, ledger_receipt
~~~

For a conditional task whose correct result is silence, do not create a report file and do not invoke Discord. Scheduled report publishers must preserve other tasks' files and ledger entries when updating `automation/report-feed`.

## Invocation
For AI articles, run `python .agents/skills/discord-feed/scripts/send.py --file PATH --id STABLE_ID --state data/discord-deliveries.json`; the default webhook is `DISCORD_WEBHOOK_URL`. For scheduled reports, run `python .agents/skills/discord-feed/scripts/deliver_reports.py --root reports --state data/discord-report-deliveries.json`; routing derives only from the validated path. Use persistent state, never a transient ledger.

## Guarantees and limitations
- Keep every Discord message at most 2000 UTF-16 code units; default to 1900 for margin. Split at paragraph, line, then character boundaries. Never silently truncate or drop Markdown.
- Escape mass mentions by disabling allowed mentions. Do not print or commit webhook credentials.
- Compute a SHA-256 content digest and use the supplied stable id for deduplication. Same id and digest already delivered => skip. Different digest under the same id => hold for explicit revision approval, not an automatic duplicate post.
- Persist per-chunk successful Discord message IDs with atomic state updates. Resume only after confirmed successes. A timeout or ambiguous response is marked uncertain and must be reconciled manually, rather than blindly retried.
- Honor Discord HTTP 429 retry_after and bounded retries on confirmed transient failures. HTTP 4xx errors other than 429 are permanent. Protect state with a process lock and never run multiple senders against the same ledger concurrently.
- Successful delivery requires a 2xx response with a message ID for every chunk and a durable completed ledger entry. Without a credential or persistent state, fail closed.
- All three webhook secrets must be configured in `JinhaPark/drops` Actions. Repository secrets are scoped to that repository and are not automatically available to ChatGPT scheduled tasks or other repositories.
- Test chunk boundaries, Unicode emoji, retries, resume, duplicate/revision behavior, and failure states before production use.
