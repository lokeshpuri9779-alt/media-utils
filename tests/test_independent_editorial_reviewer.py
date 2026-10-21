import unittest
from unittest.mock import patch

from astra_v2.independent_editorial_reviewer import assess


class EditorialReviewerTests(unittest.TestCase):
    def setUp(self):
        self.story = {"content_id": "test-1", "kind": "authored_causal_story",
                      "production_ready": True, "title": "A Story",
                      "plot_fingerprint": "unique-plot",
                      "story_beats": [{"story_beat": "reveal", "speech": "hello"}]}

    def test_missing_key_fails_closed(self):
        with patch("astra_v2.independent_editorial_reviewer.candidate_issues", return_value=[]):
            result = assess(self.story, api_key="")
        self.assertFalse(result["approved"])
        self.assertIsNone(result["record"])

    def test_approval_uses_existing_manifest(self):
        response = {"candidates": [{"finishReason": "STOP", "content": {
            "parts": [{"text": '{"decision":"approve","reasons":["Clear causal narrative"]}'}]}}]}
        with patch("astra_v2.independent_editorial_reviewer.candidate_issues", return_value=[]), \
             patch("astra_v2.independent_editorial_reviewer.review_decision", return_value=[]) as gate:
            result = assess(self.story, api_key="test", transport=lambda request: response)
        self.assertTrue(result["approved"])
        self.assertEqual(result["record"]["decision"], "approve")
        self.assertEqual(len(result["record"]["story_sha256"]), 64)
        gate.assert_called_once()

    def test_rejection_does_not_produce_approval(self):
        response = {"candidates": [{"finishReason": "STOP", "content": {
            "parts": [{"text": '{"decision":"reject","reasons":["Incoherent ending"]}'}]}}]}
        with patch("astra_v2.independent_editorial_reviewer.candidate_issues", return_value=[]):
            result = assess(self.story, api_key="test", transport=lambda request: response)
        self.assertFalse(result["approved"])
        self.assertIsNone(result["record"])

    def test_incomplete_response_fails_closed(self):
        response = {"candidates": [{"finishReason": "MAX_TOKENS", "content": {"parts": []}}]}
        with patch("astra_v2.independent_editorial_reviewer.candidate_issues", return_value=[]):
            result = assess(self.story, api_key="test", transport=lambda request: response)
        self.assertFalse(result["approved"])


if __name__ == "__main__":
    unittest.main()
