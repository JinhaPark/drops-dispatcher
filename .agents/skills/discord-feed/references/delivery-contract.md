# Discord delivery contract

## Responsibilities

The scheduled or editorial agent discovers sources, verifies evidence, writes the final Markdown, and commits it. GitHub Actions only renders and transports that committed artifact. If the agent cannot commit the required artifact, retain it for a later verified run and do not claim Discord delivery.

## Routing and repository scope

Configure all three webhook secrets in `JinhaPark/drops` Actions. A secret in another repository or in a ChatGPT task is not shared with this repository. Route by validated repository path only:

- `articles/` uses the AI webhook and article ledger on `main`.
- `reports/finance/` uses the finance webhook and report ledger on `automation/report-feed`.
- `reports/general/` uses the general webhook and report ledger on `automation/report-feed`.

The report path is its stable identity. Report files are immutable. A correctly silent conditional task creates no file or status message.

## Workflow boundaries

`.github/workflows/discord-feed.yml` handles approved AI article paths and explicit backfill manifests on `main`. `.github/workflows/report-feed.yml` handles finance and general report files on `automation/report-feed`. Both workflows serialize ledger mutations and ignore ledger-only commits as delivery triggers.

Before sending, run the affected skill tests. The report workflow validates both routed secrets because one invocation scans both report categories. Persist the appropriate ledger after every acknowledged message. If persistence fails, retain failure evidence and do not claim reliable deduplication.

## Discord rendering

Discord does not render GitHub-style pipe tables. Keep the repository artifact as authored, then run `render_for_discord` in `send.py`:

1. Detect a table only when a pipe-containing row is followed by a valid Markdown delimiter row.
2. Ignore tables already inside backtick or tilde fences.
3. Wrap detected tables in triple backticks.
4. Split a long table into independently balanced code blocks and repeat its header and delimiter rows.
5. Fail before delivery when one row plus the repeated header cannot fit the table-block budget.
6. Chunk the rendered text without cutting any fenced block.

Hash the committed source for identity and deduplication. Also record a rendered digest for diagnosis; a formatting implementation change must not silently create a new content identity.

## Ledger state machine

- `pending`: delivery can resume after the last confirmed message.
- `complete`: every chunk has a Discord message ID; skip the same source digest.
- `uncertain`: a timeout, network failure, missing message ID, or server error may have delivered content; reconcile manually before replay.

Changed content under a delivered stable ID requires explicit revision approval. HTTP 429 may use the server's bounded `retry_after`. Treat other 4xx responses as permanent and 5xx responses as uncertain. Disable allowed mentions and never log webhook URLs.

## Verification

Production delivery is verified only when the workflow finishes and the durable ledger contains `status: complete`, the expected source digest, the rendered digest for new records, the expected chunk total, and one Discord message ID per chunk.
