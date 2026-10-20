#!/usr/bin/env python3
"""Reviewed, one-time multi-source publication set in publication-date order."""
import argparse
import datetime
import os
import re
import subprocess
import sys

import backfill as b

MANIFEST = 'data/chronological-backfill.json'
ELEVATE = 'data/elevate-backfill.json'


def key(item):
    return item['published_at'], item['source_id'], item['id']


def validate_elevate(root, item):
    path = item['markdown_path']
    if not re.fullmatch(r'articles/elevate/\d{4}-\d{2}-\d{2}-[a-z0-9-]+\.md', path):
        raise ValueError('Invalid Elevate path')
    text = (root / path).read_text(encoding='utf-8')
    fields, body = b.frontmatter(text)
    expected = {'id': item['id'], 'source_id': 'elevate', 'author': 'Addy Osmani',
                'published_at': item['published_at'], 'canonical_url': item['canonical_url'],
                'source_sha256': item['source_sha256'], 'archive_index': str(item['archive_index']),
                'editorial_version': 'ko-300eojeol-v1', 'status': 'ready'}
    for name, value in expected.items():
        if fields.get(name) != value:
            raise ValueError(f'Elevate provenance mismatch: {name}')
    if 'edition_number' in fields:
        raise ValueError('Do not invent publisher issue numbers for Elevate')
    date = datetime.date.fromisoformat(fields['published_at']).isoformat()
    if not path.startswith(f'articles/elevate/{date}-'):
        raise ValueError('Elevate publication date/path mismatch')
    slug = fields['canonical_url'].removeprefix('https://addyo.substack.com/p/')
    if not re.fullmatch('[a-z0-9-]+', slug) or item['id'] != f'elevate:{slug}':
        raise ValueError('Invalid canonical Elevate identity')
    if not re.fullmatch('[a-f0-9]{64}', item['source_sha256']) or not item.get('full_source_verified') or not item.get('source_evidence'):
        raise ValueError('Full Elevate source verification required')
    if b.sha(text) != item['markdown_sha256']:
        raise ValueError('Unreviewed Elevate content change')
    paragraphs = [p.strip() for p in body.strip().split('\n\n') if p.strip()]
    if paragraphs[0] != f"# [{item['title']}]({item['canonical_url']})":
        raise ValueError('Original Elevate title/link mismatch')
    summary = paragraphs[2:]
    count = len(' '.join(summary).split())
    if not 3 <= len(summary) <= 5 or not 250 <= count <= 350:
        raise ValueError(f'Invalid Elevate summary: {count} eojeol')
    return fields['id'], text


def reviewed_catalog(root):
    ae = b.read_json(root / b.MANIFEST)
    ae_items = b.validate_manifest(root, ae)
    elevate = b.read_json(root / ELEVATE)
    if elevate.get('index_basis') != 'official-sitemap-publication-date-ascending' or elevate.get('range') != [1, 64]:
        raise ValueError('Unknown Elevate archive scope')
    items = elevate['articles']
    if [x['archive_index'] for x in items] != list(range(1, 65)):
        raise ValueError('Elevate must enumerate exactly 64 archive positions')
    if len({x['id'] for x in items}) != 64 or len({x['canonical_url'] for x in items}) != 64:
        raise ValueError('Duplicate Elevate source identity')
    if items != sorted(items, key=lambda x: (x['published_at'], x['id'])):
        raise ValueError('Elevate archive positions must follow publication dates')
    for item in items:
        if item['status'] == 'ready':
            validate_elevate(root, item)
        elif item['status'] != 'pending' or not item.get('reason'):
            raise ValueError('Unverified Elevate article needs an explicit reason')
    return ae_items + items


def validate_manifest(root, manifest):
    if manifest.get('status') not in ('held', 'active') or manifest.get('ordering') != 'published_at,source_id,id':
        raise ValueError('Invalid chronological publication plan')
    catalog = reviewed_catalog(root)
    ready = {i['id']: i for i in catalog if i['status'] == 'ready'}
    items = manifest['items']
    if len(items) != len(ready) or {i['id'] for i in items} != set(ready):
        raise ValueError('Publication plan must contain every verified article exactly once')
    if items != sorted(items, key=key):
        raise ValueError('Publication plan is not chronological')
    for item in items:
        source = ready[item['id']]
        for name in ('id', 'source_id', 'published_at', 'canonical_url', 'markdown_path', 'markdown_sha256'):
            if item.get(name) != source.get(name):
                raise ValueError(f'Publication plan differs from reviewed source: {name}')
    pending = {i['id'] for i in catalog if i['status'] != 'ready'}
    if set(manifest.get('excluded_unverified_ids', [])) != pending:
        raise ValueError('Every unverified source must be disclosed')
    return items


def already_completed(root, manifest):
    if manifest.get('status') != 'active' or b.read_json(root / b.INFLIGHT, {}):
        return False
    items = validate_manifest(root, manifest)
    ledger = b.read_json(root / b.LEDGER, {})
    return all(ledger.get(i['id'], {}).get('status') == 'complete' and
               ledger[i['id']]['sha256'] == i['markdown_sha256'] for i in items)


def deliver(root, manifest, checkpoint=b.persist, invoke=subprocess.run):
    items = validate_manifest(root, manifest)
    if manifest['status'] != 'active':
        print('Chronological backfill held; no delivery')
        return
    if b.read_json(root / b.INFLIGHT, {}):
        raise RuntimeError('Prior in-flight delivery requires reconciliation; do not replay')
    ledger = b.read_json(root / b.LEDGER, {})
    missing_seen = False
    for item in items:
        previous = ledger.get(item['id'])
        if previous is None:
            missing_seen = True
        elif previous.get('status') != 'complete' or previous.get('sha256') != item['markdown_sha256']:
            raise RuntimeError(f"{item['id']} requires reconciliation before any new send")
        elif missing_seen:
            raise RuntimeError('Delivery ledger is not a chronological prefix; reconcile order first')
    for item in items:
        item_id = item['id']
        text = (root / item['markdown_path']).read_text(encoding='utf-8')
        if b.sha(text) != item['markdown_sha256']:
            raise RuntimeError('Content changed after validation')
        previous = b.read_json(root / b.LEDGER, {}).get(item_id)
        if previous:
            if previous['sha256'] != item['markdown_sha256'] or previous['status'] != 'complete':
                raise RuntimeError(f'{item_id} requires reconciliation')
            continue
        marker = {'id': item_id, 'sha256': item['markdown_sha256'],
                  'run_id': os.environ.get('GITHUB_RUN_ID', 'local'), 'plan': MANIFEST}
        checkpoint(root, {}, marker)
        result = invoke([sys.executable, str(root / '.agents/skills/discord-feed/scripts/send.py'),
                         '--file', str(root / item['markdown_path']), '--id', item_id,
                         '--state', str(root / b.LEDGER)], cwd=root)
        record = b.read_json(root / b.LEDGER, {}).get(item_id, {})
        if result.returncode or record.get('status') != 'complete' or record.get('sha256') != item['markdown_sha256']:
            checkpoint(root, marker, marker)
            raise RuntimeError(f'{item_id} did not complete; no later article sent')
        checkpoint(root, marker, {})
        print(f"{item['published_at']} {item_id}: remote ledger verified", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--validate-only', action='store_true')
    args = parser.parse_args()
    manifest = b.read_json(b.ROOT / MANIFEST)
    if not manifest:
        print('No chronological publication plan')
    elif args.validate_only:
        print('Validated chronological articles:', len(validate_manifest(b.ROOT, manifest)))
    else:
        deliver(b.ROOT, manifest)


if __name__ == '__main__':
    main()
