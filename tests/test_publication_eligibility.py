"""Offline selection regressions: no sender, webhook, or remote mutations."""
import contextlib
import io
import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'scripts'))
import backfill as b
import chronological_backfill as c
import deliver_articles as d


class PublicationEligibilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        (self.root / 'scripts').mkdir()
        (self.root / 'articles').mkdir()
        (self.root / 'data').mkdir()
        self.write(d.MONITOR_STATE, {'monitoring_started_at': '2026-10-19T18:17:23Z'})
        self.write(b.LEDGER, {})

    def write(self, path, value):
        (self.root / path).write_text(json.dumps(value), encoding='utf-8')

    def article(self, item_id, published_at):
        path = self.root / 'articles' / (item_id.replace(':', '-') + '.md')
        path.write_text(f'---\nid: {item_id}\nsource_id: example\n'
                        f'canonical_url: https://example.test/{item_id}\nauthor: Tester\n'
                        f'published_at: {published_at}\nstatus: ready\n---\nArticle\n', encoding='utf-8')
        return path

    def dispatch(self):
        output = io.StringIO()
        with patch.object(d, '__file__', str(self.root / 'scripts/deliver_articles.py')), \
                patch.object(b, 'deliver_one') as sender, contextlib.redirect_stdout(output):
            d.main()
        return sender, output.getvalue()

    def test_unapproved_edition_70_is_held_without_blocking_new_issue(self):
        old = self.article('artificial-engineering:edition-70', '2026-08-29')
        self.article('example:new', '2026-10-20')
        before = old.read_bytes()
        sender, output = self.dispatch()
        self.assertEqual([call.args[1] for call in sender.call_args_list], ['example:new'])
        self.assertIn('Held artificial-engineering:edition-70', output)
        self.assertIn('backfill approval required', output)
        self.assertEqual(old.read_bytes(), before)

    def test_date_only_start_day_is_held_with_reason_and_new_issue_continues(self):
        self.article('example:same-day', '2026-10-19')
        self.article('example:new', '2026-10-20')
        sender, output = self.dispatch()
        self.assertEqual([call.args[1] for call in sender.call_args_list], ['example:new'])
        self.assertIn('publication time unknown', output)

    def test_exact_timestamp_boundary_and_timezone_offsets(self):
        cases = {
            '2026-10-19T18:17:22Z': False,
            '2026-10-19T18:17:23Z': False,
            '2026-10-19T18:17:24Z': True,
            '2026-10-20T03:17:23+09:00': False,
            '2026-10-20T03:17:24+09:00': True,
            '2026-10-19T18:17:23.001Z': True,
        }
        for value, allowed in cases.items():
            with self.subTest(value=value):
                for path in (self.root / 'articles').glob('*.md'):
                    path.unlink()
                self.article('example:timestamp', value)
                sender, _ = self.dispatch()
                self.assertEqual(sender.call_count, int(allowed))

    def test_invalid_dates_and_naive_times_never_send(self):
        for value in ('2026-02-30', '2026-10-19T19:00:00', 'unknown', ''):
            with self.subTest(value=value):
                self.article('example:invalid', value)
                with patch.object(b, 'deliver_one') as sender:
                    with self.assertRaisesRegex(RuntimeError, 'provenance'):
                        self.dispatch()
                    sender.assert_not_called()

    def test_missing_or_invalid_policy_fails_closed(self):
        self.article('example:new', '2026-10-20')
        for state in (None, {}, {'monitoring_started_at': '2026-10-19'},
                      {'monitoring_started_at': 'bad'}):
            with self.subTest(state=state):
                self.write(d.MONITOR_STATE, state)
                with self.assertRaisesRegex(RuntimeError, 'monitoring_started_at'):
                    self.dispatch()
        (self.root / d.MONITOR_STATE).unlink()
        with self.assertRaisesRegex(RuntimeError, 'monitoring_started_at'):
            self.dispatch()

    def test_delivered_old_and_new_articles_are_not_resent_or_rewritten(self):
        ledger = {}
        for name, date in [('old', '2026-08-29'), ('new', '2026-10-20')]:
            path = self.article('example:' + name, date)
            ledger['example:' + name] = {'status': 'complete', 'sha256': b.sha(path.read_text())}
        self.write(b.LEDGER, ledger)
        before = (self.root / b.LEDGER).read_bytes()
        sender, _ = self.dispatch()
        sender.assert_not_called()
        self.assertEqual((self.root / b.LEDGER).read_bytes(), before)

    def test_old_uncertain_or_revised_delivery_still_requires_reconciliation(self):
        path = self.article('example:old', '2026-08-29')
        for status, digest in [('uncertain', b.sha(path.read_text())), ('complete', '0' * 64)]:
            self.write(b.LEDGER, {'example:old': {'status': status, 'sha256': digest}})
            with self.assertRaisesRegex(RuntimeError, 'reconciliation'):
                self.dispatch()

    def test_explicit_approved_chronological_set_uses_existing_backfill_path(self):
        # Only the manifest path may override the baseline. Its existing
        # validators enforce membership, active status, evidence and digests.
        self.article('example:approved', '2026-08-29')
        plan = {'status': 'active', 'items': [{'id': 'example:approved'}]}
        self.write(c.MANIFEST, plan)
        with patch.object(c, 'already_completed', return_value=False), \
                patch.object(c, 'deliver') as approved:
            sender, _ = self.dispatch()
        approved.assert_called_once_with(self.root, plan)
        sender.assert_not_called()

    def test_completed_approved_set_does_not_authorize_neighboring_old_article(self):
        self.article('example:approved', '2026-08-29')
        self.article('example:unapproved', '2026-08-30')
        self.article('example:new', '2026-10-20')
        self.write(c.MANIFEST, {'status': 'active', 'items': [{'id': 'example:approved'}]})
        with patch.object(c, 'already_completed', return_value=True):
            sender, output = self.dispatch()
        self.assertEqual([call.args[1] for call in sender.call_args_list], ['example:new'])
        self.assertIn('Held example:unapproved', output)


if __name__ == '__main__':
    unittest.main()
