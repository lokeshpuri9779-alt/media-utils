import unittest

from astra_v2.event_task_graph import blocked_stages, ready_events


class EventTaskGraphTests(unittest.TestCase):
    def test_only_root_ready_initially(self):
        tasks = ready_events("video-1", {})
        self.assertEqual([task.stage for task in tasks], ["story"])
        self.assertEqual(tasks[0].idempotency_key, "video-1:story")

    def test_editorial_gate_required(self):
        self.assertEqual([t.stage for t in ready_events("video-1", {"story": "succeeded"})], ["editorial"])
        self.assertEqual(ready_events("video-1", {"story": "succeeded", "editorial": "running"}), [])
        self.assertEqual(ready_events("video-1", {"story": "succeeded", "editorial": "quarantined"}), [])

    def test_publish_requires_all_upstream(self):
        states = {stage: "succeeded" for stage in
                  ("story", "editorial", "assets", "render", "media_qa")}
        self.assertEqual([t.stage for t in ready_events("video-1", states)], ["archive"])
        states["archive"] = "succeeded"
        self.assertEqual([t.stage for t in ready_events("video-1", states)], ["publish"])

    def test_failed_dependencies_block_downstream(self):
        self.assertIn("publish", blocked_stages({"editorial": "failed"}))
        self.assertNotIn("story", blocked_stages({"editorial": "failed"}))

    def test_invalid_state_rejected(self):
        with self.assertRaises(ValueError):
            ready_events("video-1", {"editorial": "approved_without_evidence"})


if __name__ == "__main__":
    unittest.main()
