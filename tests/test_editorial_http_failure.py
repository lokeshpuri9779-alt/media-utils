import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from astra_v2.independent_editorial_reviewer import assess


class ReviewerHTTPFailureTests(unittest.TestCase):
    def test_http_429_is_rejected_with_safe_reason(self):
        story = {"content_id": "example"}
        with patch("astra_v2.independent_editorial_reviewer.candidate_issues", return_value=[]):
            response = assess(story, [], api_key="fake-key", transport=lambda req: (_ for _ in ()).throw(
                HTTPError("https://secret.example/key", 429, "sensitive", {}, None)))
        self.assertFalse(response["approved"])
        self.assertIsNone(response["record"])
        self.assertIn("review_failed:HTTP_429", response["issues"])
        self.assertIn("review_provider:rate_limited", response["issues"])
        self.assertNotIn("secret", str(response))


if __name__ == "__main__":
    unittest.main()
