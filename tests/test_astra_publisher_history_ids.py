"""Regression checks for persisted Shorts publisher identities."""
import unittest
from astra_v2.creative import publisher_history_ids


class PublisherHistoryIdsTests(unittest.TestCase):
    def test_includes_pending_and_reserved_keys_and_embedded_ids(self):
        state = {
            "published": {"old": {"content_id": "original-old"}},
            "pending": {"upload-1": {"content_id": "pending-story"}},
            "reserved": {"slot-2": {"content_id": "reserved-story"}},
        }
        ids = publisher_history_ids(state)
        self.assertTrue({"old", "original-old", "upload-1", "pending-story",
                         "slot-2", "reserved-story"}.issubset(ids))

    def test_rejects_malformed_history_bucket(self):
        with self.assertRaises(ValueError):
            publisher_history_ids({"pending": []})


if __name__ == "__main__":
    unittest.main()
