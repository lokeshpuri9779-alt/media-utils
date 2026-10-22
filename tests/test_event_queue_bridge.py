import unittest
from unittest.mock import Mock

from astra_v2.event_queue_bridge import admit_verified_package, dispatch_decisions


class EventQueueBridgeTests(unittest.TestCase):
    def test_publish_requires_independent_evidence(self):
        stages = ("story", "editorial", "assets", "render", "media_qa", "archive")
        states = {stage: "succeeded" for stage in stages}
        self.assertFalse(dispatch_decisions("story-1", states)[0].allowed)
        self.assertTrue(dispatch_decisions(
            "story-1", states, receipt_saved=True,
            approval_verified=True, qa_verified=True)[0].allowed)

    def test_rejected_approval_never_mutates_warehouse(self):
        warehouse = Mock()
        with self.assertRaises(ValueError):
            admit_verified_package(warehouse, {}, approval_digest="a" * 64,
                                   qa_digest="b" * 64,
                                   approval_verified=False, qa_verified=True)
        warehouse.assert_not_called()

    def test_existing_warehouse_methods_are_used(self):
        warehouse = Mock()
        receipt = {"content_id": "story-1",
                   "manifest": {"sha256": "c" * 64},
                   "publication_triggered": False}
        admit_verified_package(warehouse, receipt,
                               approval_digest="a" * 64, qa_digest="b" * 64,
                               approval_verified=True, qa_verified=True)
        warehouse.save_receipt.assert_called_once_with(receipt)
        warehouse.enqueue.assert_called_once_with(
            "story-1", "c" * 64,
            approval_digest="a" * 64, qa_digest="b" * 64)


if __name__ == "__main__":
    unittest.main()
