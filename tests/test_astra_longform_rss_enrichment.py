"""Offline regression tests for bounded long-form RSS enrichment."""
import unittest
from unittest.mock import patch

from astra_v2.trend_source_collector import enrich_trends
from longform_trends import build_plan, long_quality_gate, retention_contract, sourced_topics


class LongformRssEnrichmentTests(unittest.TestCase):
    @patch("astra_v2.trend_source_collector._parse_feed")
    def test_attaches_summary_publisher_domain_and_date(self, parse_feed):
        parse_feed.return_value = [{
            "title": "Mars mission reaches new milestone",
            "url": "https://news.google.com/rss/articles/example",
            "publisher": "Example Science",
            "publisher_domain": "science.example",
            "published": "2026-11-25T10:00:00+00:00",
            "summary": "<p>Mission team reports a new milestone.</p>",
        }]
        result = enrich_trends([{"title": "Mars mission", "news": []}])
        article = result[0]["news"][0]
        self.assertEqual(article["source"], "Example Science")
        self.assertEqual(article["publisher_domain"], "science.example")
        self.assertIn("new milestone", article["summary"])
        self.assertTrue(article["published"])
        parse_feed.assert_called_once()

    @patch("astra_v2.trend_source_collector._parse_feed")
    def test_preserves_existing_links_and_deduplicates_urls(self, parse_feed):
        existing = {"title": "Mars mission update", "url": "https://example.org/a", "source": "Example"}
        parse_feed.return_value = [
            {"title": "Duplicate", "url": "https://example.org/a", "publisher": "Example"},
            {"title": "Second report", "url": "https://other.org/b", "publisher": "Other",
             "publisher_domain": "other.org", "summary": "Context"},
        ]
        result = enrich_trends([{"title": "Mars mission", "news": [existing]}])
        self.assertEqual(len(result[0]["news"]), 2)
        self.assertEqual(result[0]["news"][0], existing)
        self.assertEqual(result[0]["news"][1]["source"], "Other")

    @patch("astra_v2.trend_source_collector._parse_feed")
    def test_limits_network_enrichment_to_four_topics(self, parse_feed):
        parse_feed.return_value = []
        enrich_trends([{"title": f"Topic {i}", "news": []} for i in range(8)])
        self.assertEqual(parse_feed.call_count, 4)

    def test_renderer_retains_summary_and_publisher_domain(self):
        item = {
            'title': 'Mars mission', 'traffic': '20K+',
            'news': [
                {'title': 'Mars mission reaches orbit', 'url': 'https://news.google.com/a',
                 'source': 'Publisher A', 'publisher_domain': 'publisher-a.com',
                 'summary': '<p>Mission reaches orbit.</p>', 'published': '2026-11-25'},
                {'title': 'Mars mission science update', 'url': 'https://news.google.com/b',
                 'source': 'Publisher B', 'publisher_domain': 'publisher-b.com',
                 'summary': 'Scientists describe the next phase.', 'published': '2026-11-24'},
            ],
        }
        candidate = sourced_topics([item])[0]
        self.assertEqual(len(candidate['sources']), 2)
        self.assertIn('Mission reaches orbit', candidate['sources'][0]['summary'])
        self.assertEqual(candidate['sources'][0]['published'], '2026-11-25')
    def test_story_plan_uses_source_led_distinct_beats_and_thumbnail_hook(self):
        item = {
            'title': 'Mars mission', 'traffic': '20K+',
            'news': [
                {'title': 'Mars mission reaches orbit after launch', 'url': 'https://news.google.com/a',
                 'source': 'Publisher A', 'publisher_domain': 'publisher-a.com',
                 'summary': 'Mission team reports spacecraft reached orbit after a successful launch.',
                 'published': '2026-11-25'},
                {'title': 'Mars mission scientists describe orbit milestone', 'url': 'https://news.google.com/b',
                 'source': 'Publisher B', 'publisher_domain': 'publisher-b.com',
                 'summary': 'Scientists describe the orbit milestone and the next planned observation phase.',
                 'published': '2026-11-24'},
            ],
        }
        plan, topics = build_plan([item])
        self.assertEqual(len(plan), 8)
        self.assertEqual(len({x['story_beat'] for x in plan}), 8)
        self.assertIn('spacecraft reached orbit', plan[3]['speech'])
        self.assertIn('Publisher B adds', plan[4]['speech'])
        self.assertEqual([card['name'] for card in plan[3]['source_cards']],
                         ['Publisher A', 'Publisher B'])
        self.assertIn('spacecraft reached orbit', plan[3]['source_cards'][0]['summary'])
        self.assertIn('MARS MISSION REACHES ORBIT', topics[0]['thumbnail_copy'])
        report = long_quality_gate(plan, topics)
        self.assertGreaterEqual(report['score'], 85)
        self.assertEqual(report['usable_summary_count'], 2)
        self.assertIn('what do the reports actually confirm', plan[0]['speech'].lower())
        self.assertIn('Publisher A reports:', plan[0]['speech'])
        self.assertIn('spacecraft reached orbit', plan[0]['speech'])
        self.assertLessEqual(len(plan[0]['speech'].split()), 45)
        self.assertIn('what can we actually say', plan[-1]['speech'].lower())
        self.assertLessEqual(len(plan[3]['speech'].split()), 115)
        retention = retention_contract(plan)
        self.assertLessEqual(retention['opening_words'], 45)
        self.assertEqual(retention['distinct_beats'], 8)

    def test_retention_contract_rejects_opening_without_a_question(self):
        plan = [
            {'speech': 'This is the reported headline.', 'story_beat': 'promise'},
            {'speech': 'Context.', 'story_beat': 'context'},
            {'speech': 'The ending actually say reported but unconfirmed.', 'story_beat': 'takeaway'},
        ]
        with self.assertRaisesRegex(RuntimeError, 'opening must establish'):
            retention_contract(plan)

    def test_story_plan_rejects_headlines_without_summaries(self):
        item = {
            'title': 'Mars mission', 'traffic': '20K+',
            'news': [
                {'title': 'Mars mission reaches orbit', 'url': 'https://news.google.com/a',
                 'source': 'Publisher A', 'publisher_domain': 'publisher-a.com'},
                {'title': 'Mars mission science update', 'url': 'https://news.google.com/b',
                 'source': 'Publisher B', 'publisher_domain': 'publisher-b.com'},
            ],
        }
        with self.assertRaisesRegex(RuntimeError, 'no source summaries'):
            build_plan([item])

    @patch("astra_v2.trend_source_collector._parse_feed", side_effect=OSError("offline"))
    def test_feed_failure_keeps_original_trend(self, parse_feed):
        original = {"title": "Mars mission", "news": []}
        result = enrich_trends([original])
        self.assertEqual(result[0]["title"], "Mars mission")
        self.assertEqual(result[0]["news"], [])


if __name__ == "__main__":
    unittest.main()
