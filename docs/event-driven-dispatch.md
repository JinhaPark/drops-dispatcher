# Event-driven wakeups for private drops

This public repository is the **only** Discord sender. Private `JinhaPark/drops/main` is the source of immutable Markdown and all receipt/checkpoint state. No private Actions minutes, webhook secrets, private text, paths, content hashes, or message IDs are placed in public commits.

## Transport

After a producer successfully commits a new immutable artifact to private `drops/main`:

1. Reports (`reports/finance/` or `reports/general/`): wake the public `report-feed.yml`.
2. AI articles (`articles/`): wake the public `discord-feed.yml`.
3. The public workflow pulls the latest private snapshot using its existing short-lived GitHub App token, validates pending identities, routes to the appropriate Discord webhook, and checkpoints receipts back to the private main.
4. Confirm delivery only from the private complete ledger with every Discord message ID. An accepted wake event or a successful commit is **not** a receipt.

### Preferred API event (for capable producers)

With a token authorized to write **only to the public dispatcher**, call the GitHub API endpoint

`POST https://api.github.com/repos/JinhaPark/drops-dispatcher/dispatches`

using one of these event types and **no private data in `client_payload`**:

- `drops-reports-ready` — finance or general report
- `drops-articles-ready` — approved live article

This invokes the corresponding public GitHub Actions workflow directly. The API sender uses a GitHub App installation token or another properly scoped credential; do not store it in the private repository or print it.

### GitHub connector fallback (when no dispatch API is available)

After verifying the private commit, read the matching public `.dispatch/wake-reports.json` or `.dispatch/wake-articles.json` and update that **same** file on `drops-dispatcher/main` using its latest blob SHA. Example non-sensitive payload:

```json
{"version":1,"signal":"2026-10-30T09:30:00Z"}
```

The signal must be a new unique value on each committed publication, but **must not contain** the private filename, title, body, stable ID, SHA, user information, or Discord credentials. GitHub's public `push` event wakes the route-specific workflow. If the file SHA changed concurrently, refetch once and retry; otherwise leave the private artifact for scheduled polling. Never create new signal filenames, rewrite the report, or force push.

### Safety and compatibility

- The existing report (hourly) and article (six-hour) scheduled checks remain as fallback.
- A public workflow wakeup fetches **all** pending items in that route, not private paths supplied by an untrusted event.
- Ordinary code pushes and default `workflow_dispatch` validation do **not** post Discord; explicit signal pushes, typed repository-dispatch events, approved manual `mode=deliver`, and schedules do.
- Each route has its existing concurrency group, remote pre-send in-flight fence, digest comparison, and private completed ledger. Repeated wakeups cannot override an uncertain marker or intentionally resend a completed digest.
- If public wakeup fails, do not mark delivery successful. The next scheduled run attempts only still-eligible, safe items. Reconcile any uncertain in-flight state before retrying.

This scheme provides near-immediate wakeup **only when the producer emits the signal after the private commit**. A private repository push made by an unmodified producer does not, by itself, trigger the public workflow.
