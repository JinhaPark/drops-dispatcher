"""Fresh private ticketing data fence; never researches or holds a webhook.

Called synchronously before each Discord POST, including definite-429 retries.
This cannot make GitHub state and Discord delivery one atomic transaction.
"""
from datetime import datetime, timezone
import hashlib
from pathlib import Path, PurePosixPath
import re
import stat

from private_repo import DEFAULT_REPO, api
from yunchan_dispatch_gate import strict_ledger, validate_pre_post

LEDGER = 'data/ticketing-monitor-state.json'
PREFIX = 'reports/general/ticketing/'
MANAGED = 'automation-ticketing-prepost/v1'


def enrolled_snapshot(root):
    """Feature selection from the existing pinned private snapshot, not authority.

    Producer enrollment and its first immutable report share a single commit.
    Legacy runs retain their original path; enrolled runs still fetch live state
    before EVERY POST and never use this snapshot as freshness evidence.
    """
    try:
        path = Path(root) / LEDGER
        need(not path.is_symlink())
        if not path.exists():
            return False
        need(path.is_file() and not path.is_symlink()
             and path.resolve().is_relative_to(Path(root).resolve()))
        need(stat.S_ISREG(path.stat().st_mode) and path.stat().st_size <= 8_000_000)
        ledger = strict_ledger(path.read_bytes())
        need(isinstance(ledger, dict) and isinstance(ledger.get('caller', {}), dict))
        runtime = ledger.get('caller', {}).get('automation_runtime', {})
        need(isinstance(runtime, dict))
        marker = runtime.get('managed_dispatch')
        if marker is None:
            need(not runtime.get('queued_notices'))
            return False
        need(marker == MANAGED)
        return True
    except Exception:
        raise RuntimeError('Ticketing enrollment metadata requires reconciliation') from None


def need(condition):
    if not condition:
        raise RuntimeError('Ticketing pre-POST identity is unavailable or changed')


def sha(value):
    need(isinstance(value, str) and re.fullmatch('[0-9a-f]{40}', value))
    return value


def main_head():
    obj = api(DEFAULT_REPO, 'git/ref/heads/main')
    need(isinstance(obj, dict) and obj.get('ref') == 'refs/heads/main')
    ref = obj.get('object', {})
    need(ref.get('type') == 'commit')
    return sha(ref.get('sha'))


def pinned_bytes(path, head, limit):
    """Resolve the exact path by Git tree, rejecting symlinks and truncation."""
    import base64
    commit = api(DEFAULT_REPO, 'git/commits/' + sha(head))
    need(isinstance(commit, dict) and commit.get('sha') == head)
    tree_sha = sha(commit.get('tree', {}).get('sha'))
    tree = api(DEFAULT_REPO, 'git/trees/' + tree_sha + '?recursive=1')
    need(isinstance(tree, dict) and tree.get('sha') == tree_sha
         and tree.get('truncated') is False and isinstance(tree.get('tree'), list)
         and len(tree['tree']) <= 20000)
    rows = [row for row in tree['tree'] if isinstance(row, dict) and row.get('path') == path]
    need(len(rows) == 1)
    row = rows[0]
    need(row.get('type') == 'blob' and row.get('mode') == '100644')
    blob_sha = sha(row.get('sha'))
    blob = api(DEFAULT_REPO, 'git/blobs/' + blob_sha)
    need(isinstance(blob, dict) and blob.get('sha') == blob_sha
         and blob.get('encoding') == 'base64' and isinstance(blob.get('content'), str)
         and len(blob['content']) <= 2 * limit)
    raw = base64.b64decode(''.join(blob['content'].split()), validate=True)
    need(0 < len(raw) <= limit)
    need(hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == blob_sha)
    return raw


def _require_current(report_path, source_bytes, item_id):
    """Acquire actual latest ledger/report; pure gate cannot certify its origin."""
    path = PurePosixPath(report_path)
    need(isinstance(report_path, str) and report_path.startswith(PREFIX)
         and len(path.parts) == 4 and path.as_posix() == report_path
         and path.suffix == '.md' and len(report_path) <= 240)
    need(item_id == 'scheduled-report:' + report_path[len('reports/'): -3])
    need(isinstance(source_bytes, bytes) and 0 < len(source_bytes) <= 50000)
    head = main_head()
    raw = pinned_bytes(LEDGER, head, 8_000_000)
    need(pinned_bytes(report_path, head, 50000) == source_bytes)
    ledger = strict_ledger(raw)
    need(isinstance(ledger, dict))
    caller = ledger.get('caller', {})
    need(isinstance(caller, dict))
    runtime = caller.get('automation_runtime', {})
    need(isinstance(runtime, dict))
    marker = runtime.get('managed_dispatch')
    need(marker == MANAGED)
    records = runtime.get('queued_notices', {})
    need(isinstance(records, dict))
    matches = [(key, record) for key, record in records.items()
               if isinstance(record, dict) and record.get('path') == report_path]
    need(len(matches) == 1)
    notice_id, record = matches[0]
    notices = []
    entries = ledger.get('entries', {})
    need(isinstance(entries, dict))
    for entry in entries.values():
        if isinstance(entry, dict) and isinstance(entry.get('pending'), dict):
            notice = entry['pending'].get(notice_id)
            if notice is not None:
                notices.append(notice)
    intents = runtime.get('reminder_intents', [])
    need(isinstance(intents, list))
    notices.extend(notice for notice in intents if isinstance(notice, dict)
                   and notice.get('notification_id') == notice_id)
    need(len(notices) == 1 and record.get('notification_id') == notice_id)
    # A moving ref invalidates this snapshot; do not retry a Discord POST.
    need(main_head() == head)
    validate_pre_post(raw, notices[0], report_path=report_path,
                      report_bytes=source_bytes, now=datetime.now(timezone.utc))
    # No content, identities, hashes, receipts or token values are logged.


def require_current(report_path, source_bytes, item_id):
    """Never expose private API endpoints, source identities or raw errors."""
    try:
        return _require_current(report_path, source_bytes, item_id)
    except Exception:
        raise RuntimeError('Ticketing current-state verification failed; no POST attempted') from None

