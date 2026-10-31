# Discord dispatcher CI reliability runbook

## Failure categories and operator response

- **Offline code or workflow regression:** The Python test root is the public `drops-dispatcher` checkout. Do not copy code, tests, YAML or `.dispatch` files into `private-data`. Update the code-side regression or its test, then run the focused offline suite. The private API snapshot supplies data only via explicit `--data-root` for validation-only backfill commands.
- **Private GitHub 404 / git exit 128:** A private repository may be deliberately hidden from unauthorized credentials. Check the GitHub App installation's access to the exact `drops` or `skills` repository and its per-repository read/write token scope. Treat persistent 401/403/404 as configuration errors, not transient outages; do not retry them blindly or print tokens. `GITHUB_TOKEN` for the public dispatcher is not a substitute for an App token authorized on private repositories.
- **Private `main` moved during snapshot:** Producers and the different delivery routes share one private main, and checkpoint commits can arrive mid-read. The *read-only* pinned snapshot need not follow a moving branch. For live delivery, retry the complete REST snapshot up to three times, without writing any candidate data until the head is stable. If it still changes, stop without posting; the next scheduled/event wakeup can try again.
- **Private checkpoint 409/422:** Re-read the remote in-flight marker and ledger, and only attempt a safe merge using the existing optimistic fast-forward update. Preserve the fence on uncertainty. Never force-update or delete a marker to make a run green.
- **Discord POST timeout / unknown receipt:** A network failure does not prove a message was not delivered. Do not automatically replay or rerun a sender job. Reconcile remote in-flight state and recorded Discord message IDs before allowing any additional POST.
- **Scheduled report run succeeded but no alert appeared:** `success` can mean no eligible new item; check pending/digest state and private complete receipts. A public workflow success alone does not establish a Discord delivery.

## Validation contract

The `checkpoint-tests.yml` PR job is offline, needs no private checkout, and uses the public code root. The `validate-discord.yml` push job uses a scoped read-only GitHub App token to fetch a pinned private fixture snapshot. Its backfill commands are always `--validate-only --data-root private-data`. Both must be read-only with respect to private receipts and must never send a webhook.

On recovery, run the affected tests first, merge only a tested commit, and inspect the newly triggered main validation. Confirm production dispatch separately from the private complete ledger and message IDs; do not retry historical sends merely because validation failed.
