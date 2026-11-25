"""Offline regression tests for bounded long-form RSS enrichment."""
import unittest
from unittest.mock import patch

from astra_v2.trend_source_collector import enrich_trends


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

    @patch("astra_v2.trend_source_collector._parse_feed", side_effect=OSError("offline"))
    def test_feed_failure_keeps_original_trend(self, parse_feed):
        original = {"title": "Mars mission", "news": []}
        result = enrich_trends([original])
        self.assertEqual(result[0]["title"], "Mars mission")
        self.assertEqual(result[0]["news"], [])


if __name__ == "__main__":
    unittest.main()
