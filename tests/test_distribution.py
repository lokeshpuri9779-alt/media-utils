import unittest

from distribution import distribution_state, source_quality


class DistributionTests(unittest.TestCase):
    def test_tiny_source_is_not_ranked(self):
        self.assertIsNone(source_quality({"views": 3, "estimatedMinutesWatched": 30}))

    def test_retention_quality_beats_raw_clicks(self):
        data = {"videos": {"v1": {
            "genre": "science",
            "analytics_reports": {"traffic_sources": {"status": "available", "rows": [
                {"insightTrafficSourceType": "YT_SEARCH", "views": 100, "estimatedMinutesWatched": 40},
                {"insightTrafficSourceType": "RELATED_VIDEO", "views": 25, "estimatedMinutesWatched": 30},
            ]}}
        }}}
        state = distribution_state(data)
        self.assertEqual(state["mode"], "learn")
        self.assertEqual(state["ranked_sources"][0]["source"], "RELATED_VIDEO")

    def test_excluded_video_never_trains_distribution(self):
        data = {"videos": {"owner": {
            "learning_excluded": True,
            "analytics_reports": {"traffic_sources": {"status": "available", "rows": [
                {"insightTrafficSourceType": "YT_SEARCH", "views": 1000, "estimatedMinutesWatched": 1000}
            ]}}
        }}}
        state = distribution_state(data)
        self.assertEqual(state["mode"], "explore")
        self.assertEqual(state["ranked_sources"], [])


if __name__ == "__main__":
    unittest.main()
