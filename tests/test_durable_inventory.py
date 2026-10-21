"""Regression tests for transactional inventory and stale worker fencing."""
import tempfile
import unittest
from pathlib import Path

from astra_v2.durable_inventory import Inventory


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = str(Path(self.temp.name) / "inventory.db")
        self.db = Inventory(self.path)
        self.db.register("story-a", '{"manifest":"sha256:a"}')

    def test_unapproved_cannot_claim(self):
        self.assertIsNone(self.db.claim("worker-a", now=100))

    def test_approval_and_publication(self):
        self.db.set_approval("story-a", True)
        lease = self.db.claim("worker-a", now=100, ttl=20)
        self.assertEqual(lease["fencing"], 1)
        self.db.complete("story-a", "worker-a", 1, "video-a")
        self.assertIsNone(self.db.claim("worker-b", now=200))

    def test_expired_worker_cannot_complete(self):
        self.db.set_approval("story-a", True)
        old = self.db.claim("worker-a", now=100, ttl=10)
        self.assertIsNone(self.db.claim("worker-b", now=105))
        new = self.db.claim("worker-b", now=111)
        self.assertEqual(new["fencing"], old["fencing"] + 1)
        with self.assertRaisesRegex(ValueError, "stale"):
            self.db.complete("story-a", "worker-a", old["fencing"], "wrong")
        self.db.complete("story-a", "worker-b", new["fencing"], "correct")

    def test_revoke_approval_blocks_completion(self):
        self.db.set_approval("story-a", True)
        lease = self.db.claim("worker-a", now=100)
        self.db.set_approval("story-a", False)
        with self.assertRaisesRegex(ValueError, "stale"):
            self.db.complete("story-a", "worker-a", lease["fencing"], "wrong")

    def test_receipt_conflict_rejected(self):
        with self.assertRaisesRegex(ValueError, "conflicting"):
            self.db.register("story-a", '{"manifest":"different"}')

    def test_renew_and_release(self):
        self.db.set_approval("story-a", True)
        lease = self.db.claim("worker-a", now=100, ttl=10)
        self.db.renew("story-a", "worker-a", lease["fencing"], ttl=30, now=105)
        self.assertIsNone(self.db.claim("worker-b", now=120))
        self.db.release("story-a", "worker-a", lease["fencing"])
        replacement = self.db.claim("worker-b", now=121)
        self.assertEqual(replacement["fencing"], lease["fencing"] + 1)

    def test_stale_renew_and_release_rejected(self):
        self.db.set_approval("story-a", True)
        old = self.db.claim("worker-a", now=100, ttl=10)
        self.db.claim("worker-b", now=111)
        with self.assertRaisesRegex(ValueError, "stale"):
            self.db.renew("story-a", "worker-a", old["fencing"], now=112)
        with self.assertRaisesRegex(ValueError, "stale"):
            self.db.release("story-a", "worker-a", old["fencing"])

    def test_expired_renew_rejected(self):
        self.db.set_approval("story-a", True)
        lease = self.db.claim("worker-a", now=100, ttl=10)
        with self.assertRaisesRegex(ValueError, "expired"):
            self.db.renew("story-a", "worker-a", lease["fencing"], now=111)

    def test_reopen_persists(self):
        self.db.set_approval("story-a", True)
        reopened = Inventory(self.path)
        self.assertEqual(reopened.claim("worker-a", now=100)["content_id"], "story-a")


if __name__ == "__main__":
    unittest.main()
