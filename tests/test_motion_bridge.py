import json
import tempfile
import unittest
from pathlib import Path

from motion_renderer.bridge import export_motion_job
from premium_stories import catalog


class MotionBridgeTests(unittest.TestCase):
    def test_ready_story_exports_motion_job(self):
        story = next(x for x in catalog() if x.get("production_ready"))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "job.json"
            job = export_motion_job(story, path)
            self.assertEqual(job["engine"], "motion-canvas")
            self.assertTrue(path.exists())
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["content_id"], story["content_id"])
            self.assertTrue(saved["scenes"])


if __name__ == "__main__":
    unittest.main()
