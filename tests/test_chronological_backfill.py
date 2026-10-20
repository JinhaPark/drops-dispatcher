import json
import pathlib
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'scripts'))
import backfill as b
import chronological_backfill as c


class ChronologicalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        (self.root / 'data').mkdir()
        (self.root / b.LEDGER).write_text('{}')
        self.items = []
        for day, source, name in [('2023-11-21', 'elevate', 'growth'),
                                  ('2025-05-18', 'artificial-engineering', 'edition-3'),
                                  ('2025-05-19', 'elevate', 'later')]:
            item_id = f'{source}:{name}'
            path = f'{name}.md'
            (self.root / path).write_text(item_id)
            self.items.append({'id': item_id, 'source_id': source, 'published_at': day,
                               'canonical_url': 'https://example.test/' + name,
                               'markdown_path': path, 'markdown_sha256': b.sha(item_id), 'status': 'ready'})
        self.pending = {'id': 'elevate:paid', 'status': 'pending', 'reason': 'restricted'}
        self.plan = {'status': 'active', 'ordering': 'published_at,source_id,id',
                     'items': self.items, 'excluded_unverified_ids': [self.pending['id']]}
        self.events = []

    def checkpoint(self, root, old, new):
        self.events.append(('checkpoint', new.get('id')))

    def invoke(self, args, cwd):
        item_id = args[args.index('--id') + 1]
        self.events.append(('send', item_id))
        ledger = b.read_json(self.root / b.LEDGER)
        ledger[item_id] = {'status': 'complete', 'sha256': b.sha(item_id), 'total': 1,
                           'messages': [{'index': 0, 'message_id': str(100 + len(self.events))}]}
        (self.root / b.LEDGER).write_text(json.dumps(ledger))
        return SimpleNamespace(returncode=0)

    def run_delivery(self, checkpoint=None, invoke=None):
        with patch.object(c, 'reviewed_catalog', return_value=self.items + [self.pending]):
            c.deliver(self.root, self.plan, checkpoint or self.checkpoint, invoke or self.invoke)

    def test_both_sources_are_interleaved_chronologically_with_remote_checkpoints(self):
        self.run_delivery()
        self.assertEqual(self.events, [event for item in self.items for event in
                                      [('checkpoint', item['id']), ('send', item['id']), ('checkpoint', None)]])

    def test_nonchronological_manifest_rejected_before_post(self):
        self.plan['items'] = list(reversed(self.items))
        with self.assertRaises(ValueError):
            self.run_delivery()
        self.assertEqual(self.events, [])

    def test_missing_verified_article_and_undisclosed_pending_rejected(self):
        with patch.object(c, 'reviewed_catalog', return_value=self.items + [self.pending]):
            for change in ({'items': self.items[:2]}, {'excluded_unverified_ids': []}):
                with self.assertRaises(ValueError):
                    c.validate_manifest(self.root, {**self.plan, **change})

    def test_held_plan_and_inflight_never_send(self):
        self.plan['status'] = 'held'
        self.run_delivery()
        self.assertEqual(self.events, [])
        self.plan['status'] = 'active'
        (self.root / b.INFLIGHT).write_text('{"id":"previous"}')
        with self.assertRaises(RuntimeError):
            self.run_delivery()
        self.assertEqual(self.events, [])

    def test_remote_persistence_failure_stops_before_second_article(self):
        def fail(root, old, new):
            self.checkpoint(root, old, new)
            if not new:
                raise RuntimeError('Remote checkpoint failed')
        with self.assertRaises(RuntimeError):
            self.run_delivery(checkpoint=fail)
        self.assertEqual([e for e in self.events if e[0] == 'send'], [('send', self.items[0]['id'])])

    def test_uncertain_failure_preserves_marker_and_stops(self):
        with self.assertRaises(RuntimeError):
            self.run_delivery(invoke=lambda *a, **kw: SimpleNamespace(returncode=1))
        self.assertEqual(self.events, [('checkpoint', self.items[0]['id'])] * 2)

    def test_rerun_skips_success_and_changed_content_fails(self):
        self.run_delivery()
        self.events.clear()
        self.run_delivery()
        self.assertEqual(self.events, [])
        (self.root / self.items[0]['markdown_path']).write_text('changed')
        with self.assertRaises(RuntimeError):
            self.run_delivery()
        self.assertEqual(self.events, [])

    def test_later_success_without_earlier_success_blocks_all_new_posts(self):
        item = self.items[1]
        (self.root / b.LEDGER).write_text(json.dumps({item['id']: {
            'status': 'complete', 'sha256': item['markdown_sha256']}}))
        with self.assertRaises(RuntimeError):
            self.run_delivery()
        self.assertEqual(self.events, [])

    def test_same_day_tie_break_is_deterministic(self):
        self.items[0]['published_at'] = self.items[1]['published_at']
        self.plan['items'] = sorted(self.items, key=c.key)
        with patch.object(c, 'reviewed_catalog', return_value=self.items + [self.pending]):
            c.validate_manifest(self.root, self.plan)
        self.assertEqual(self.plan['items'][0]['source_id'], 'artificial-engineering')


if __name__ == '__main__':
    unittest.main()
