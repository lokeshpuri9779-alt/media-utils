import sqlite3
import tempfile
import unittest
from pathlib import Path
from astra_v2.adaptive_queue import Queue


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.queue = Queue(Path(self.temp.name) / "queue.sqlite")

    def tearDown(self):
        self.temp.cleanup()

    def add(self, content_id="one"):
        self.queue.enqueue(content_id, "file:///video.mp4", "hash",
                           "approved_manifest_digest", "qa_digest")

    def test_single_claim(self):
        self.add()
        first = self.queue.claim(now=100)
        self.assertEqual(first["content_id"], "one")
        self.assertIsNone(Queue(self.queue.database).claim(now=100))
        self.assertEqual(self.queue.status("one"), "reserved")

    def test_confirm_and_no_duplicate(self):
        self.add()
        claimed = self.queue.claim(now=100, lease_seconds=50)
        self.queue.confirm("one", claimed["lease_token"], "youtube-1", now=101)
        self.assertEqual(self.queue.status("one"), "published")
        self.assertIsNone(self.queue.claim(now=102))
        with self.assertRaises(ValueError):
            self.queue.confirm("one", claimed["lease_token"], "youtube-1", now=103)

    def test_expired_requires_reconciliation(self):
        self.add()
        claimed = self.queue.claim(now=100, lease_seconds=10)
        self.assertEqual(self.queue.expired(now=111), ["one"])
        self.assertIsNone(self.queue.claim(now=111))
        with self.assertRaises(ValueError):
            self.queue.confirm("one", claimed["lease_token"], "youtube-2", now=111)

    def test_duplicate_rejected(self):
        self.add()
        with self.assertRaises(sqlite3.IntegrityError):
            self.add()


if __name__ == "__main__":
    unittest.main()
