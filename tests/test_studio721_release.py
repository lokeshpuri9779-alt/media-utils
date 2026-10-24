"""Release gate: distinguish improved 7.2.1 frames from older 7.2.0 artifacts."""
import unittest
from pathlib import Path
from studio_renderer import VERSION
from astra_v2.preload_queue import _studio_meets_floor

class Studio721ReleaseTests(unittest.TestCase):
    def test_main_renderer_and_publisher_floor_are_consistent(self):
        self.assertEqual(VERSION,"studio-7.3.1")
        workflow=Path(".github/workflows/astra-v2-publish.yml").read_text()
        self.assertIn("ASTRA_MIN_STUDIO_VERSION: '7.3.0'",workflow)
        self.assertFalse(_studio_meets_floor("studio-7.2.1","7.3.0"))
        self.assertTrue(_studio_meets_floor(VERSION,"7.3.0"))

    def test_actual_pillow_source_edits_trigger_the_parallel_preloader(self):
        workflow=Path(".github/workflows/astra-v2-preload.yml").read_text()
        for path in ("astra_v2/pillow_duo_scene.py",
                     "astra_v2/pillow_scene_direction.py",
                     "astra_v2/pillow_duo_stories.py"):
            self.assertIn(path,workflow)
        self.assertIn("matrix:",workflow)
        self.assertIn("lane: [0, 1, 2, 3]",workflow)
        self.assertIn("cancel-in-progress: false",workflow)

if __name__=="__main__":
    unittest.main()
