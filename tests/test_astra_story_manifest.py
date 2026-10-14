import tempfile
import unittest
from pathlib import Path
from astra_v2.story_batch import build_story_batch
from astra_v2.story_production_manifest import create_manifest


class ManifestTests(unittest.TestCase):
    def test_rejects_cast_change(self):
        plan = build_story_batch()["stories"][0]
        plan["scenes"][1]["actors"] = []
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "inconsistent cast"):
                create_manifest(plan, Path(directory))

    def test_rejects_location_change(self):
        plan = build_story_batch()["stories"][0]
        plan["scenes"][1]["location"] = "different-location"
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "inconsistent location"):
                create_manifest(plan, Path(directory))


if __name__ == "__main__":
    unittest.main()
