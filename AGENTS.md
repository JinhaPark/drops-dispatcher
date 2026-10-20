# AGENTS.md — AI Newsletter to Discord

## Mission and separation of responsibilities
Monitor the configured newsletters, research each new issue, produce a complete Korean editorial Markdown document, and commit it under `articles/`. GitHub Actions then sends that already completed Markdown to Discord using the local `.agents/skills/discord-feed/SKILL.md`. The delivery skill must never research, translate, summarize, or modify prose. Do not use GitHub Pages, RSS, or a separate model API.

## Sources (extensible)
Maintain sources in `sources.json` or the agent task configuration, never scatter source-name checks through generic delivery code.
- Artificial Engineering: https://www.linkedin.com/newsletters/artificial-engineering-7324756381780140032 — author André Lindenberg. Additional mandatory `project_roundup` section.
- Elevate: https://addyo.substack.com/archive — author Addy Osmani. No mandatory roundup.
Future sources define their own editorial sections, access rules, and completeness requirements.

## Reader, voice and writing quality
Readers are highly educated Korean adults educated in Korea, including technically curious readers who may not specialize in every subfield. Respect their background without assuming familiarity with every technical acronym.
Use natural Korean polite endings (합니다/입니다) in every complete prose sentence. Do not mix with 한다/이다 narration. Preserve original English titles, proper nouns, and technical names where needed.
Avoid literal translation from English, stacked abstract nouns, gratuitous passive voice, choppy one-sentence paragraphs, marketing clichés, and mechanical connector phrases. Make clear who does what and why. Explain unfamiliar terms on first use; connect problem, mechanism, conditions, evidence, trade-offs, and practical implications in a flowing narrative.
Keep each article's main Korean summary approximately **300 space-delimited Korean eojeol** (target 250–350, excluding metadata and source-specific extras). Use 3–5 readable paragraphs on mobile. Do not mistake 300 words for 300 characters. Avoid needless decimals and unverified benchmarks. Attribute author claims and separate verified observations from interpretations.
Do not reproduce full copyrighted third-party articles; write an original substantive Korean synopsis, preserving original source links.

## Per-article Markdown contract
One file per canonical issue under `articles/<source-id>/<YYYY-MM-DD>-<stable-slug>.md`, UTF-8. Use front matter containing: `id`, `source_id`, `canonical_url`, `author`, `published_at`, `source_sha256` (when full source text is accessible), `editorial_version`, `status: ready`. Never substitute the fetch date for unknown publication date. Keep stable `id` derived from source and canonical issue identifier; corrections to author/date must not generate a new ID.
Body: original English title as a Markdown link to the canonical URL, date and author, followed by the approximately 300-eojeol Korean summary.
Artificial Engineering only: verify every GitHub and other technology/project entry in the issue's concluding weekly roundup, then include **all entries** as an unnumbered Markdown list with original verified links and a concise natural Korean description each. Do not silently omit items. If the complete roundup cannot be verified, hold the issue rather than publish an incomplete document.
Elevate has no required roundup. Future sources can add source-specific sections through declarative policy.
Never invent titles, URLs, dates, authors, project names, or facts. If source access is blocked, retain a pending item rather than pretending it was read.

## Monitoring and cache
The ChatGPT scheduled agent checks both sources every six hours. A missing or inaccessible source is not equivalent to no new posts.
Use canonical URL plus stable publisher ID as primary identity, persist original author and publication date as independently verified metadata. Use source text SHA-256 to detect content changes; use editorial policy version and content digest to decide whether a rewrite is needed. Reuse unchanged Markdown; retain revision history in Git. No full scraped copyrighted article text or credentials in this public repository.
Backfills must not send historical posts to Discord. Before first live delivery, establish an explicit baseline or carefully approved publication set. No old content should be treated as new solely because the workflow was installed.

### Explicit one-time authorization: Artificial Engineering Editions 1–64
On 2026-10-20 the user explicitly authorized one historical backfill, Edition 1 through 64, in that order. This overrides the default historical-send prohibition only for this exact set; it creates no schedule. Read `data/artificial-engineering-backfill.json`: `held` means research/archival work only, and only `active` permits delivery. Every ready entry must have independently verified issue number (including a directly inspected cover image when necessary), date, full-source digest, complete project inventory, and reviewed Markdown digest. Stop before the first unverified edition; never infer issue numbers from dates or skip a gap. Earlier issues may distribute technology links throughout the body rather than have a separate concluding roundup; record that format and preserve the complete verified inventory.
Use `scripts/backfill.py` for this set. It checkpoints an in-flight marker to remote main before each edition, then sends through the unchanged local skill, and persists/verifies the completed ledger before continuing. A remaining in-flight marker blocks replay after a crash or failed persistence and requires reconciliation against Discord IDs and Actions artifacts. Do not delete it merely to retry. Keep Editions 65–69, Elevate, their original Markdown bytes, and existing delivery records intact.

## Discord delivery and durability
Read `.agents/skills/discord-feed/SKILL.md` and run its tests. The `DISCORD_WEBHOOK_URL` secret must be in **JinhaPark/news → Settings → Secrets and variables → Actions**; a secret in JinhaPark/skills is not shared.
The delivery workflow triggers on committed `articles/**/*.md`, the explicitly approved backfill manifest, and manual dispatch, never on delivery-ledger or in-flight checkpoint commits. Use serialized runs and a durable `data/discord-deliveries.json` ledger. Record each successful Discord message ID and avoid resending the same ID/content hash. Changed content under an already delivered ID requires explicit revision approval. A timeout or uncertain delivery requires manual reconciliation, not blind retry.
Ensure each message stays below Discord's 2,000 UTF-16 code-unit limit; no truncation, disable allowed mentions, respect rate limits, and never log webhook credentials. Only send after Markdown editorial validation and successful per-chunk delivery tracking. Persist the ledger back to the repository; if persisting fails, do not claim reliable deduplication.
The agent, not GitHub Actions, is responsible for researching and writing Markdown. If agent-to-repository commit is unavailable, report the limitation instead of claiming a feed was sent.

## Git and validation
Before modifying files, read current main and this AGENTS.md. Avoid unrelated edits. Validate Markdown front matter, dates, links, article length, required source-specific sections, and the delivery unit tests. Do not call a code commit a verified Discord delivery; inspect Actions and delivery ledger. Use feature branches/PRs for substantial future changes; avoid overwriting unrelated concurrent work.
