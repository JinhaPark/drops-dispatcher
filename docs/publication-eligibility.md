# Automatic Discord publication eligibility

`status: ready` means editorial completion, not permission to send historical
content. The ordinary dispatcher reads `monitoring_started_at` from
`data/monitor-state.json` before collecting live candidates. A missing or invalid
baseline fails closed, without sending anything.

- A `YYYY-MM-DD` publication date later than the baseline's UTC calendar date is
  eligible. An earlier date is archive-only.
- A date matching that calendar date is held because publication time is unknown.
  Do not infer midnight, noon, a fetch time, or a publisher timezone.
- A verified ISO timestamp with seconds and an explicit `Z` or `±HH:MM` offset
  is compared as a UTC instant. Only a strictly later instant is eligible;
  equality is held. Fractional seconds are supported. Naive timestamps and
  impossible dates fail provenance validation before any live post.
- Held historical/same-day articles are skipped with an article ID, path and
  reason in the workflow log; they do not block eligible live articles.
- Previously completed IDs with the same Markdown hash are skipped. Changed or
  uncertain delivery records still require reconciliation, even for old content.

The only historical exceptions remain the explicit existing backfill manifests
and their ordered delivery paths. Their activation, reviewed membership,
provenance, Markdown digest checks, and ledger rules are unchanged. A nearby
edition, a ready flag, or completing an approved set does not extend approval.
Do not add an article-level override to bypass these manifests.

Live selection still preflights all candidates before calling the existing
`backfill.deliver_one()` transaction. The remote pre-send marker, per-article
ledger verification, uncertain-state fence, and concurrency behavior are intact.
Selection does not modify articles, manifests, monitoring state or delivery data.

## Offline verification

Run from the repository root (no Discord credential required):

```sh
python -m unittest discover -s .agents/skills/discord-drops/tests -v
python -m unittest discover -s tests -v
python scripts/backfill.py --validate-only
python scripts/chronological_backfill.py --validate-only
python -m compileall -q scripts tests
```

`tests/test_publication_eligibility.py` covers the unapproved historical Edition
70 reproduction, newer date-only issues, the start date with unknown time,
strict timestamp boundaries and offsets, invalid/missing policy, explicit
backfill routing, adjacent unapproved history, completed records, and uncertain
or revised old records. Dispatcher tests mock the delivery transaction; existing
backfill and checkpoint tests use fake sends and temporary local Git remotes.
No real Discord requests are made.
