# Private YouTube archive and finance-channel summaries

Canonical private storage is `JinhaPark/drops/main`:

- `youtube/transcripts/<video_id>.json`: immutable raw caption acquisition and provenance. Archive only, never sent.
- `youtube/summaries/<source_id>/<video_id>.md`: reviewed short Korean summary, one immutable identity per video. The current agent applies `JinhaPark/skills/summarize`; the dispatcher never generates summaries.
- `data/discord-youtube-deliveries.json` and `data/discord-youtube-inflight.json`: independent durable receipt and pre-send fence, initialized only by the dispatcher.

Use front matter with `id: youtube:<video_id>`, `video_id`, `source_id` matching the parent directory, `canonical_url`, verified `published_at`, `transcript_path: youtube/transcripts/<video_id>.json`, exact raw-file `transcript_sha256`, `editorial_version: youtube-kakao-v1`, and `status: ready`. Drafts are held. Dates and panel names must come from inspected source metadata and introductions, and uncertain speaker attribution remains explicit. Summaries use short Korean plain-text blocks grouped by date/panel, without tables. Caption timestamps delimit the inspected scope; metadata alone is never spoken-content evidence.

`youtube-feed.yml` reads only `youtube/summaries` plus checkpoint data. It deliberately never pulls raw captions. Ready summaries use the existing `DISCORD_WEBHOOK_URL_FINANCE` secret, with no new webhook or producer sender. Remote verified pre-send fences, content digests, complete per-message receipts and uncertain-delivery stops match the established report route. An archival commit is not delivery. A content-free wake follows a ready-summary commit only, using the event/marker contract in `event-driven-dispatch.md`.

## Conservative producer access

A video-ID cache is mandatory and consulted before any YouTube request. First reconcile the canonical private archive through GitHub; a local private cache is only a working copy. Reuse unchanged raw bytes and digest; never fetch again merely to produce a new summary. Explicit refresh must preserve prior provenance and requires a separate decision.

Serialize every outbound YouTube HTTP request across local collector processes with a persistent host-wide gate and at least 60 seconds between requests. This includes multiple internal library requests for one transcript. Do not parallelize channel discovery and caption requests or run concurrent collectors. Honor longer Retry-After periods. On HTTP 429, RequestBlocked, or IpBlocked, persist a stop and require manual review; no blind retries, account/cookie/proxy rotation, or alternate downloader requests after a block. Cache unsuccessful attempts for at least 24 hours so routine reruns do not repeatedly probe unavailable captions. A persistent stop survives process restarts. GitHub archive reads are not YouTube requests.

No new collector schedule, audio transcription service, model API, or trading runtime is installed by this route.
