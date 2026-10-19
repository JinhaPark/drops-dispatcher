---
name: discord-feed
description: Deliver an already completed Markdown article to Discord, splitting messages safely and deduplicating with a durable delivery ledger. Does not fetch sources or write summaries.
---
# Discord Feed

## Scope
Input is final Markdown, a stable `item_id`, optional canonical source URL, and the Discord webhook credential available to the execution environment. Do not scrape, summarize, translate, or edit the article. Caller owns editorial quality and source verification.

## Invocation
Run `python .agents/skills/discord-feed/scripts/send.py --file PATH --id STABLE_ID --state PATH`. Set `DISCORD_WEBHOOK_URL` in the runner's environment. Use a private persistent state file (not a transient work directory). See the repository workflow and delivery ledger documentation.

## Guarantees and limitations
- Keep every Discord message at most 2000 UTF-16 code units; default to 1900 for margin. Split at paragraph, line, then character boundaries. Never silently truncate or drop Markdown.
- Escape mass mentions by disabling allowed mentions. Do not print or commit webhook credentials.
- Compute a SHA-256 content digest and use the supplied stable id for deduplication. Same id and digest already delivered => skip. Different digest under the same id => hold for explicit revision approval, not an automatic duplicate post.
- Persist per-chunk successful Discord message IDs with atomic state updates. Resume only after confirmed successes. A timeout or ambiguous response is marked uncertain and must be reconciled manually, rather than blindly retried.
- Honor Discord HTTP 429 retry_after and bounded retries on confirmed transient failures. HTTP 4xx errors other than 429 are permanent. Protect state with a process lock and never run multiple senders against the same ledger concurrently.
- Successful delivery requires a 2xx response with a message ID for every chunk and a durable completed ledger entry. Without a credential or persistent state, fail closed.
- Discord webhook secret should be configured in the actual execution environment; GitHub repository secrets are scoped to Actions in that repository and are not automatically available to ChatGPT scheduled tasks or other repositories.
- Test chunk boundaries, Unicode emoji, retries, resume, duplicate/revision behavior, and failure states before production use.
