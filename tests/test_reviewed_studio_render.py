"""Isolated Studio renderer proof using a real reviewed PNG, no publication."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image
from astra_v2.story_art_direction import bind_reviewed_scenes


class ReviewedStudioRenderTests(unittest.TestCase):
    def test_studio_draw_visual_uses_exact_reviewed_scene(self):
        from studio_renderer import draw_visual
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            png = root / "art" / "assets" / "reviewed" / "scene.png"
            png.parent.mkdir(parents=True)
            Image.new("RGB", (540, 960), (91, 142, 183)).save(png)
            digest = hashlib.sha256(png.read_bytes()).hexdigest()
            manifest = root / "art" / "manifest.json"
            manifest.write_text(json.dumps({"assets": [{
                "id": "reviewed-proof-001", "status": "approved",
                "category": "background", "story_content_id": "proof",
                "scene_id": "001", "sha256": digest,
                "path": "art/assets/reviewed/scene.png", "tags": []
            }]}))
            shot = {"speech": "A fox finds a bell.", "visual": "scene"}
            bound = bind_reviewed_scenes([shot], "proof", manifest)[0]
            frame = Image.new("RGB", (1080, 1920), (0, 0, 0))
            draw_visual(frame, bound, 0.0, 0.0, (240, 180, 120))
            self.assertEqual(frame.getpixel((540, 960)), (91, 142, 183))

    def test_corrupt_reviewed_scene_cannot_fallback(self):
        from studio_renderer import draw_visual, CreativeReject
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            png = root / "art" / "assets" / "reviewed" / "scene.png"
            png.parent.mkdir(parents=True)
            Image.new("RGB", (540, 960), (91, 142, 183)).save(png)
            digest = hashlib.sha256(png.read_bytes()).hexdigest()
            manifest = root / "art" / "manifest.json"
            manifest.write_text(json.dumps({"assets": [{
                "id": "reviewed-proof-001", "status": "approved",
                "category": "background", "story_content_id": "proof",
                "scene_id": "001", "sha256": digest,
                "path": "art/assets/reviewed/scene.png", "tags": []
            }]}))
            bound = bind_reviewed_scenes([{"speech": "Fox.", "visual": "scene"}], "proof", manifest)[0]
            Image.new("RGB", (540, 960), (200, 10, 10)).save(png)
            with self.assertRaises(CreativeReject):
                draw_visual(Image.new("RGB", (1080, 1920)), bound, 0.0, 0.0, (1, 2, 3))


if __name__ == "__main__":
    unittest.main()
