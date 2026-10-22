import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw
from astra_v2.restore_reviewed_artwork import restore_reviewed_artwork
from astra.asset_library import load_assets


class Store:
    def __init__(self, path):
        self.path = path
    def verify(self, record):
        return self.path


class RestoreArtworkTests(unittest.TestCase):
    def test_requires_independent_review_and_restores_exact_scene(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image = Image.new("RGB", (540, 960))
            draw = ImageDraw.Draw(image)
            for y in range(960):
                draw.line((0, y, 539, y), fill=(y % 220 + 15, (y * 3) % 220 + 15, (y * 5) % 220 + 15))
            source = root / "source.png"
            image.save(source)
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            receipt = root / "receipt.json"
            receipt.write_text(json.dumps({"schema": "astra.artwork.archive.v1", "assets": [
                {"id": "scene-001", "category": "background", "story_content_id": "story-a",
                 "scene_id": "001", "artifact": {"sha256": digest, "uri": "test://art"}}]}))
            decisions = root / "decisions.json"
            decisions.write_text("{}")
            with self.assertRaisesRegex(ValueError, "no_independently_reviewed_artwork"):
                restore_reviewed_artwork(receipt, decisions, root / "render", Store(source))
            decisions.write_text(json.dumps({"scene-001": {"approved": True, "sha256": digest,
                "semantic_match": True, "character_continuity": True}}))
            result = restore_reviewed_artwork(receipt, decisions, root / "render", Store(source))
            self.assertEqual(result["restored"], 1)
            assets = load_assets(result["manifest"])
            self.assertEqual(assets[0]["story_content_id"], "story-a")
            self.assertEqual(assets[0]["scene_id"], "001")
            self.assertEqual(assets[0]["sha256"], digest)
            decisions.write_text(json.dumps({"scene-001": {"approved": True, "sha256": "0" * 64,
                "semantic_match": True, "character_continuity": True}}))
            with self.assertRaisesRegex(ValueError, "artwork_review_identity_mismatch"):
                restore_reviewed_artwork(receipt, decisions, root / "render", Store(source))


if __name__ == "__main__":
    unittest.main()
