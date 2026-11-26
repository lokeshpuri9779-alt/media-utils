"""Release gate: distinguish improved 7.2.1 frames from older 7.2.0 artifacts."""
import unittest
from pathlib import Path
from studio_renderer import VERSION
from astra_v2.preload_queue import _studio_meets_floor

class Studio721ReleaseTests(unittest.TestCase):
    def test_main_renderer_and_publisher_floor_are_consistent(self):
        self.assertEqual(VERSION,"studio-7.3.1")
        workflow=Path(".github/workflows/astra-v2-publish.yml").read_text()
        self.assertIn("ASTRA_MIN_STUDIO_VERSION: '7.3.1'",workflow)
        self.assertFalse(_studio_meets_floor("studio-7.2.1","7.3.1"))
        self.assertTrue(_studio_meets_floor(VERSION,"7.3.1"))

    def test_production_source_edits_trigger_the_parallel_preloader(self):
        workflow=Path(".github/workflows/astra-v2-preload.yml").read_text()
        # Push trigger intentionally has no path filter: every production source,
        # workflow, and editorial change re-enters the autonomous pipeline.
        self.assertIn("push:",workflow)
        self.assertIn("branches: [main]",workflow)
        self.assertNotIn("paths:",workflow)
        self.assertIn("matrix:",workflow)
        self.assertIn("lane: [0, 1, 2, 3]",workflow)
        self.assertIn("cancel-in-progress: false",workflow)

if __name__=="__main__":
    unittest.main()
