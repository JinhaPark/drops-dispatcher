"""Offline YouTube route isolation and durable receipt regression tests."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import deliver_private_youtube as youtube

class YouTubeTests(unittest.TestCase):
    def fixture(self, root, video='abcdefghijk', source='sample', status='ready'):
        p=root/'youtube/summaries'/source/(video+'.md')
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(f'''---
id: youtube:{video}
video_id: {video}
source_id: {source}
canonical_url: https://www.youtube.com/watch?v={video}
transcript_path: youtube/transcripts/{video}.json
transcript_sha256: {'a'*64}
published_at: 2026-10-31T10:00:00+09:00
editorial_version: youtube-kakao-v1
status: {status}
---
A short reviewed summary.
''')
        return p
    def test_only_ready_summary_routes_to_finance(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);p=self.fixture(r)
            self.fixture(r,'lmnopqrstuv',status='draft')
            raw=r/'youtube/transcripts';raw.mkdir();(raw/'abcdefghijk.md').write_text('raw captions')
            items=youtube.pending(r)
            self.assertEqual(len(items),1)
            self.assertEqual(items[0][:3],(p,'youtube:abcdefghijk','DISCORD_WEBHOOK_URL_FINANCE'))
    def test_source_digest_and_id_required(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);p=self.fixture(r)
            p.write_text(p.read_text().replace('youtube:abcdefghijk','youtube:wrong'))
            with self.assertRaises(ValueError): youtube.pending(r)
    def test_duplicate_video_in_different_channel_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);self.fixture(r);self.fixture(r,source='other')
            with self.assertRaisesRegex(ValueError,'Duplicate'): youtube.pending(r)
    def test_complete_skips_changed_or_uncertain_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);p=self.fixture(r);ledger=r/youtube.LEDGER;ledger.parent.mkdir()
            record={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'status':'complete','total':1,'messages':[{'index':0,'message_id':'123'}]}
            ledger.write_text(json.dumps({'youtube:abcdefghijk':record}))
            self.assertEqual(youtube.pending(r),[])
            p.write_text(p.read_text()+'changed')
            with self.assertRaises(RuntimeError): youtube.pending(r)
    def test_inflight_blocks_before_post(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);self.fixture(r);p=r/youtube.INFLIGHT;p.parent.mkdir();p.write_text('{"id":"prior"}')
            with patch.object(youtube.subprocess,'run') as send:
                with self.assertRaises(RuntimeError): youtube.run(r)
                send.assert_not_called()
    def test_dry_run_has_no_external_side_effect(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);self.fixture(r)
            with patch.object(youtube,'checkpoint') as cp,patch.object(youtube.subprocess,'run') as send:
                youtube.run(r,dry_run=True);cp.assert_not_called();send.assert_not_called()
    def test_verified_fence_before_post_and_complete_checkpoint(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);p=self.fixture(r);events=[]
            def cp(root,prior,marker): events.append('fence' if marker else 'complete')
            def send(*args,**kwargs):
                self.assertEqual(events,['fence']);events.append('post')
                q=r/youtube.LEDGER;q.parent.mkdir(exist_ok=True)
                q.write_text(json.dumps({'youtube:abcdefghijk':{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'status':'complete','total':1,'messages':[{'index':0,'message_id':'123'}]}}))
            with patch.dict('os.environ',{'DISCORD_WEBHOOK_URL_FINANCE':'test'}),patch.object(youtube,'checkpoint',side_effect=cp),patch.object(youtube.subprocess,'run',side_effect=send):
                youtube.run(r)
            self.assertEqual(events,['fence','post','complete'])
    def test_workflow_excludes_transcripts_and_uses_independent_ledger(self):
        w=(ROOT/'.github/workflows/youtube-feed.yml').read_text()
        self.assertIn('--groups youtube/summaries data',w)
        self.assertNotIn('--groups youtube data',w)
        self.assertNotIn('DISCORD_WEBHOOK_URL_GENERAL',w)
        self.assertIn('drops-private-youtube-ledger',w)
        self.assertIn('inputs.mode == \'deliver\'',w)
        self.assertNotEqual(youtube.LEDGER,'data/discord-report-deliveries.json')
        self.assertNotEqual(youtube.INFLIGHT,'data/discord-backfill-inflight.json')
if __name__=='__main__': unittest.main()
