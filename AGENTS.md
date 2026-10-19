# AGENTS.md — AI Engineering News

## Purpose
Publish a Korean, mobile-first engineering news archive from a configurable set of editorial sources. Do not assume the source list is fixed.

## Source registry
Maintain source metadata in `sources.json` (id, name, home_url, feed_url, enabled, content_type, sections). Initially:
- `artificial-engineering`: Artificial Engineering — https://www.linkedin.com/newsletters/artificial-engineering-7324756381780140032
- `elevate`: Addy Osmani's Elevate — https://addyo.substack.com/

New sources must be added through the registry rather than hard-coded into ingestion or UI. Verify feeds before enabling automated retrieval. Source policies belong in the registry, not conditional checks scattered across application code.\n\n### Source-specific section contract\n- `sections` is a list of typed configurations such as `{type: "project_roundup", required: true, display: "unnumbered_list", coverage: "all", description_chars: 120}`.\n- `artificial-engineering`: enable `project_roundup`, require complete coverage of all GitHub and non-GitHub entries in the issue's closing roundup, preserve verified project links, and display an unnumbered list after the summary.\n- `elevate`: no required additional sections; render optional sections only if configured later.\n- Future sources may define their own section types, order, requiredness, and presentation without modifying the global article contract.\n- Keep source-specific extraction adapters isolated from generic normalization, validation, storage, and UI rendering.\n

## Korean editorial style
- Always write polite, natural Korean (존댓말); concise, technical, factual, not promotional.
- Order articles by publication date descending, using original source dates and ISO dates in metadata.
- Per article: publication date (YYYY.MM.DD), original English title linked to canonical source, then approximately 500 Korean characters (target 450–550, excluding title and roundup) describing the article's core technical substance.
- Keep the article summary as one readable paragraph, not a numbered list. Preserve relevant technical terminology in English where clarity benefits.
- Apply source-specific content policies from the source registry, never hard-code source names in generic editorial, validation, or rendering logic.
- Optional article sections are controlled by each source's `sections` configuration. A section with `required: true` must be complete before publication; an absent section is not an error when not configured.
- Never invent publication dates, URLs, project names, benchmarks, or claims. Distinguish author/vendor claims from independently established results.
- Original links and attribution do not themselves grant republication rights. Summarize in original Korean prose, not bulk verbatim translation. If source access is limited, label coverage incomplete rather than fabricating content.
- Optimize for iPhone: single-column cards, readable type, comfortable line spacing, no wide tables, accessible link targets.

## Ingestion and delivery
- Detect new posts by canonical URL or stable source GUID; persist published IDs to avoid duplicates.
- Backfill historical posts without Discord notifications.
- Validate the approximately 500-character summary, date, canonical title link, and every configured required section before publishing.
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
