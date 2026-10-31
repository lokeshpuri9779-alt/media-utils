"""Safe OAuth error parsing regression checks."""
import unittest
from astra_v2.youtube import Youtube, reason_for


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


class OAuthErrorTests(unittest.TestCase):
    def test_standard_oauth_error(self):
        self.assertEqual(reason_for(FakeResponse({"error": "invalid_grant"})), "invalid_grant")

    def test_nested_oauth_error(self):
        self.assertEqual(reason_for(FakeResponse({"error": {"error": "invalid_client"}})), "invalid_client")

    def test_youtube_api_reason(self):
        self.assertEqual(reason_for(FakeResponse({"error": {"errors": [{"reason": "quotaExceeded"}]}})), "quotaExceeded")


class DiscoveryTagTests(unittest.TestCase):
    def test_trend_brief_does_not_inherit_cartoon_tags(self):
        tags, hashtags = Youtube.discover_tags(
            "Why lisandro martínez Is Getting Attention Now | RAYVAN",
            "Source-linked explainer.\nASTRA-V2-ID:trend-brief-2026-10-31-pm",
        )
        self.assertIn("lisandro martínez", tags)
        self.assertIn("news explainer", tags)
        self.assertNotIn("3D cartoon", tags)
        self.assertNotIn("animated stories", tags)
        self.assertEqual(hashtags, [])

    def test_original_story_tags_unchanged(self):
        tags, hashtags = Youtube.discover_tags(
            "The Otter and the Silent Trench",
            "An original fictional microstory. #Shorts\nASTRA-V2-ID:rayvan-gemini-abc",
        )
        self.assertIn("animated stories", tags)
        self.assertIn("3D cartoon", tags)
        self.assertIn("#Shorts", hashtags)

    def test_non_trend_explainer_does_not_bypass_existing_tags(self):
        tags, _ = Youtube.discover_tags("Why rockets Is Getting Attention Now | RAYVAN", "No identity marker")
        self.assertIn("animated stories", tags)


if __name__ == "__main__":
    unittest.main()
