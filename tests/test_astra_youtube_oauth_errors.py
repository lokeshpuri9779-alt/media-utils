"""Safe OAuth error parsing regression checks."""
import unittest
from astra_v2.youtube import reason_for


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


if __name__ == "__main__":
    unittest.main()
