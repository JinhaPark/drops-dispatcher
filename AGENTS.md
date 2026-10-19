# AGENTS.md — AI Engineering News

## Purpose
Publish a Korean, mobile-first engineering news archive from a configurable set of editorial sources. Do not assume the source list is fixed.

## Source registry
Maintain source metadata in `sources.json` (id, name, home_url, feed_url, enabled, content_type). Initially:
- `artificial-engineering`: Artificial Engineering — https://www.linkedin.com/newsletters/artificial-engineering-7324756381780140032
- `elevate`: Addy Osmani's Elevate — https://addyo.substack.com/

New sources must be added through the registry rather than hard-coded into ingestion or UI. Verify feeds before enabling automated retrieval.

## Korean editorial style
- Always write polite, natural Korean (존댓말); concise, technical, factual, not promotional.
- Order articles by publication date descending, using original source dates and ISO dates in metadata.
- Per article: publication date (YYYY.MM.DD), original English title linked to canonical source, then exactly seven Korean sentences describing the article's core technical substance.
- Keep the article summary as one readable paragraph, not a numbered list. Preserve relevant technical terminology in English where clarity benefits.
- For Artificial Engineering, include every entry in the issue's concluding weekly GitHub/project roundup as an **unnumbered list** after the seven-sentence summary. Each entry: project name, original project link when verified, and one concise Korean sentence on its function or key trade-off. Do not silently omit non-GitHub items in the roundup.
- For Elevate, omit the roundup unless the source actually includes one.
- Never invent publication dates, URLs, project names, benchmarks, or claims. Distinguish author/vendor claims from independently established results.
- Original links and attribution do not themselves grant republication rights. Summarize in original Korean prose, not bulk verbatim translation. If source access is limited, label coverage incomplete rather than fabricating content.
- Optimize for iPhone: single-column cards, readable type, comfortable line spacing, no wide tables, accessible link targets.

## Ingestion and delivery
- Detect new posts by canonical URL or stable source GUID; persist published IDs to avoid duplicates.
- Backfill historical posts without Discord notifications.
- Validate each issue's seven-sentence summary, date, title link, and completeness of weekly roundup before publishing.
- Generate RSS with canonical item GUID and absolute links. Notify Discord only for newly published, successfully validated items, never for unchanged content.
- Keep webhook URLs and model API keys in GitHub Actions Secrets, never in the repo, static website, logs, or generated RSS.
- Failed fetches or generation must not erase previous content or count as successful delivery.
- Favor isolated, parallel processing per issue where supported, with deterministic validation and controlled concurrency.
- Record provenance, fetch timestamps, and error states. Do not equate missing access with missing posts.
- Separate collection, summarization, validation, publication, and notification so future sources can be added safely.

## Git workflow
- Work on feature branches and submit reviewed pull requests when practical.
- Test source parsing, deduplication, article ordering, RSS validity, and no-duplicate Discord notification behavior before merging.
- Keep site deployment and Discord notification idempotent.
