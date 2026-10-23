"""Offline RSS/Atom regression tests (no network, credentials or webhook)."""
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from feed_discovery import canonical_key, discover, parse_time, run

ATOM = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry><title>New agent post</title><id>tag:example,2026:new</id>
   <link rel="alternate" type="text/html" href="https://simonwillison.net/2026/Oct/23/new/?utm_source=rss"/>
   <published>2026-10-23T01:00:00Z</published><updated>2026-10-23T02:00:00Z</updated>
   <summary>Original text</summary></entry>
  <entry><title>Older article, recently edited</title>
   <link rel="alternate" href="https://simonwillison.net/2026/Oct/20/old/"/>
   <published>2026-10-20T01:00:00Z</published><updated>2026-10-23T02:00:00Z</updated></entry>
  <entry><title>No publication timestamp</title>
   <link href="https://simonwillison.net/2026/Oct/23/undated/"/>
   <updated>2026-10-23T03:00:00Z</updated></entry>
</feed>"""

RSS = """<?xml version="1.0"?>
<rss version="2.0"><channel><item><title>New evals</title>
<link>https://hamelhusain.substack.com/p/new-evals?utm_source=mail</link>
<guid>article-xyz</guid><pubDate>Fri, 23 Oct 2026 03:00:00 GMT</pubDate>
<description>Evaluation details</description></item>
<item><title>Old evals, republished in feed</title>
<link>https://hamelhusain.substack.com/p/old-evals</link>
<guid>article-old</guid><pubDate>Tue, 20 Oct 2026 02:00:00 GMT</pubDate></item>
</channel></rss>"""

SIMON = {"id": "simon-willison", "author": "Simon Willison", "feed_format": "atom",
         "enabled": True, "feed_url": "https://simonwillison.net/atom/entries/"}
HAMEL = {"id": "hamel-husain", "author": "Hamel Husain", "feed_format": "rss",
         "enabled": True, "feed_url": "https://hamelhusain.substack.com/feed"}
START = "2026-10-22T16:54:19Z"


class FeedDiscoveryTests(unittest.TestCase):
    def cutoff(self):
        return parse_time(START)

    def test_atom_uses_published_not_updated_and_excludes_old(self):
        items = discover(ATOM, SIMON, self.cutoff())
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["date"], "2026-10-23")
        self.assertEqual(items[0]["published_at"], "2026-10-23T01:00:00Z")
        self.assertEqual(items[0]["status"], "needs_editorial_review")

    def test_rss_parses_timezone_and_excludes_pre_onboarding(self):
        items = discover(RSS, HAMEL, self.cutoff())
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "New evals")
        self.assertEqual(items[0]["published_at"], "2026-10-23T03:00:00Z")

    def test_existing_url_is_suppressed_across_sources(self):
        seen = {canonical_key("https://hamelhusain.substack.com/p/new-evals")}
        self.assertEqual(discover(RSS, HAMEL, self.cutoff(), seen), [])

    def test_canonical_url_removes_tracking_only(self):
        self.assertEqual(canonical_key("https://www.example.com/post/?utm_medium=rss&ref=mail#intro"),
                         canonical_key("http://example.com/post"))
        self.assertNotEqual(canonical_key("https://example.com/post?a=1"),
                            canonical_key("https://example.com/post?a=2"))

    def test_invalid_date_or_missing_zone_never_falls_back_to_today(self):
        for value in ("", "2026-10-23T01:00:00", "2026-02-30T01:00:00Z"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    parse_time(value)
        undated = RSS.replace("Fri, 23 Oct 2026 03:00:00 GMT", "not a date")
        self.assertEqual(discover(undated, HAMEL, self.cutoff()), [])

    def test_exact_cutoff_excluded(self):
        xml = ATOM.replace("2026-10-23T01:00:00Z", START)
        self.assertEqual(discover(xml, SIMON, self.cutoff()), [])

    def test_malformed_atom_fails_without_creating_data(self):
        with self.assertRaises(Exception):
            discover("<html>not a feed</html>", SIMON, self.cutoff())

    def test_live_run_new_two_only_and_second_run_dedupes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "data").mkdir()
            (root / "articles/elevate").mkdir(parents=True)
            (root / "sources.json").write_text(json.dumps([
                {"id": "elevate", "url": "https://addyo.substack.com/archive", "author": "Addy Osmani", "sections": []},
                SIMON, HAMEL]))
            state = {"monitoring_started_at": "2026-10-19T18:17:23Z",
                     "sources": {"elevate": {"status": "unchanged"},
                                 "simon-willison": {"monitoring_started_at": START},
                                 "hamel-husain": {"monitoring_started_at": START}}}
            (root / "data/monitor-state.json").write_text(json.dumps(state))
            (root / "articles/elevate/known.md").write_text(
                "---\ncanonical_url: https://hamelhusain.substack.com/p/new-evals\n---\n")
            def request(url):
                return ATOM if "simonwillison" in url else RSS
            one = run(root, request)
            self.assertEqual([x["source"] for x in one], ["simon-willison"])
            self.assertEqual(run(root, request), [])
            current = json.loads((root / "data/monitor-state.json").read_text())
            self.assertEqual(current["monitoring_started_at"], state["monitoring_started_at"])
            self.assertEqual(current["sources"]["elevate"], state["sources"]["elevate"])
            self.assertEqual(len(json.loads((root / "data/pending.json").read_text())), 1)

    def test_registry_preserves_existing_writers_and_original_urls(self):
        sources = json.loads((pathlib.Path(__file__).resolve().parents[1] / "sources.json").read_text(encoding="utf-8"))
        urls = {source["id"]: source["url"] for source in sources}
        self.assertEqual(urls["artificial-engineering"],
                         "https://www.linkedin.com/newsletters/artificial-engineering-7324756381780140032")
        self.assertEqual(urls["elevate"], "https://addyo.substack.com/archive")
        self.assertEqual(len(urls), 4)

    def test_source_specific_cutoff_does_not_move_global_old_source_baseline(self):
        import deliver_articles as delivery
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "data").mkdir()
            (root / "data/monitor-state.json").write_text(json.dumps({
                "monitoring_started_at": "2026-10-19T18:17:23Z",
                "sources": {"simon-willison": {"monitoring_started_at": START},
                            "hamel-husain": {"monitoring_started_at": START}}}))
            global_start, overrides = delivery.monitoring_policy(root)
            self.assertEqual(global_start, parse_time("2026-10-19T18:17:23Z"))
            self.assertEqual(overrides["simon-willison"], parse_time(START))
            self.assertIsNone(delivery.hold_reason("2026-10-20", global_start))
            self.assertIsNotNone(delivery.hold_reason("2026-10-20", overrides["simon-willison"]))
            self.assertIsNotNone(delivery.hold_reason("2026-10-22", overrides["hamel-husain"]))
            self.assertIsNone(delivery.hold_reason("2026-10-23", overrides["hamel-husain"]))

    def test_missing_new_source_baseline_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "data").mkdir()
            (root / "sources.json").write_text(json.dumps([HAMEL]))
            (root / "data/monitor-state.json").write_text(
                json.dumps({"monitoring_started_at": "2026-10-19T18:17:23Z", "sources": {}}))
            with self.assertRaisesRegex(RuntimeError, "Missing per-source monitoring baseline"):
                run(root, lambda _: RSS)


    def test_no_new_candidates_do_not_mutate_checkpoint_or_create_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "data").mkdir()
            (root / "sources.json").write_text(json.dumps([SIMON, HAMEL]))
            state = {"monitoring_started_at": "2026-10-19T18:17:23Z",
                     "sources": {"simon-willison": {"monitoring_started_at": "2026-10-24T00:00:00Z"},
                                 "hamel-husain": {"monitoring_started_at": "2026-10-24T00:00:00Z"}}}
            checkpoint = root / "data/monitor-state.json"
            checkpoint.write_text(json.dumps(state, indent=2) + "\n")
            before = checkpoint.read_bytes()
            def request(url):
                return ATOM if "simonwillison" in url else RSS
            self.assertEqual(run(root, request), [])
            self.assertEqual(checkpoint.read_bytes(), before)
            self.assertFalse((root / "data/pending.json").exists())

    def test_unreadable_feed_is_not_recorded_as_successful_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "data").mkdir()
            (root / "sources.json").write_text(json.dumps([SIMON, HAMEL]))
            state = {"monitoring_started_at": "2026-10-19T18:17:23Z",
                     "sources": {"simon-willison": {"monitoring_started_at": START},
                                 "hamel-husain": {"monitoring_started_at": START}}}
            checkpoint = root / "data/monitor-state.json"
            checkpoint.write_text(json.dumps(state))
            before = checkpoint.read_bytes()
            def request(url):
                raise OSError("feed unavailable")
            self.assertEqual(run(root, request), [])
            self.assertEqual(checkpoint.read_bytes(), before)
            self.assertFalse((root / "data/pending.json").exists())


if __name__ == "__main__":
    unittest.main()
