# Discord delivery contract

## Responsibilities

The scheduled or editorial agent discovers sources, verifies evidence, writes the final Markdown, and commits it. GitHub Actions only renders and transports that committed artifact. If the agent cannot commit the required artifact, retain it for a later verified run and do not claim Discord delivery.

## Routing and repository scope

Configure all three webhook secrets in PUBLIC `JinhaPark/drops-dispatcher` Actions. The private repository and ChatGPT tasks do not supply these secrets to the dispatcher. Route by validated repository path only:

- `articles/` uses the AI webhook and article ledger on `main`.
- `reports/finance/` uses the finance webhook and report ledger on private `main`.
- `reports/general/` uses the general webhook and report ledger on private `main`.

The report path is its stable identity. Report files are immutable. A correctly silent conditional task creates no file or status message.

## Workflow boundaries

`.github/workflows/discord-feed.yml` reads `articles/` on private `drops/main`; `.github/workflows/report-feed.yml` reads `reports/` on the SAME private `main`. Both run canonical delivery code from public `drops-dispatcher/main`. Separate ledgers and in-flight markers remain on private `main`; fast-forward-only REST commits preserve unrelated concurrent writes. Private commits do not directly trigger public workflows and validation runs do not prove Discord delivery.

Before sending, run the affected skill tests. The report workflow requires the routed secret only when a report is pending for that category; it never falls back to another channel. Persist the appropriate ledger after every acknowledged message. If persistence fails, retain failure evidence and do not claim reliable deduplication.

## Discord rendering

Discord does not render GitHub-style pipe tables. Keep the repository artifact as authored, then run `render_for_discord` in `send.py`:

1. Recognize a pipe table only when the next row is a valid GFM delimiter with matching cell counts.
2. Preserve existing fenced code blocks and ordinary non-table pipes.
3. Short tables with 2–3 columns, predominantly numeric body cells and no more than 36 Unicode display columns are right-aligned as appropriate inside triple-backtick `text` blocks. Hangul/CJK width counts as two columns.
4. Wide or descriptive tables are rendered as vertical Markdown entries, using the first column as the bold title and the remaining columns as labeled fields, not as code blocks.
5. Split long compact tables into independently balanced code blocks with repeated headers. Long descriptive cells remain intact and use normal paragraph/line chunking without truncation.
6. Reject malformed compact fences before sending; preserve malformed source table rows rather than silently discarding content.
7. Chunk only after rendering, at most 1,900 UTF-16 units, never bisecting a fenced block.

Hash the committed source for identity and deduplication. Also record a rendered digest for diagnosis; a formatting implementation change must not silently create a new content identity.

## Ledger state machine

- `pending`: delivery can resume after the last confirmed message.
- `complete`: every chunk has a Discord message ID; skip the same source digest.
- `uncertain`: a timeout, network failure, missing message ID, or server error may have delivered content; reconcile manually before replay.

Changed content under a delivered stable ID requires explicit revision approval. HTTP 429 may use the server's bounded `retry_after`. Treat other 4xx responses as permanent and 5xx responses as uncertain. Disable allowed mentions and never log webhook URLs.

## Verification

Production delivery is verified only when the workflow finishes and the durable ledger contains `status: complete`, the expected source digest, the rendered digest for new records, the expected chunk total, and one Discord message ID per chunk.


## YouTube route

`youtube/summaries/*/<video_id>.md` uses the existing finance secret with stable identity `youtube:<video_id>`, independent `data/discord-youtube-deliveries.json` and `data/discord-youtube-inflight.json` on private main. Only `status: ready` and validated provenance are eligible. Raw `youtube/transcripts/<video_id>.json` is private archival material and must never enter a dispatcher snapshot or Discord message. `youtube-feed.yml` fetches only `youtube/summaries` and checkpoint data; ordinary code pushes validate only. The same durable pre-send fence, digest reconciliation, per-message receipts and uncertainty stop apply.
