import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import hashlib
from PIL import Image
from astra_v2.story_art_direction import illustration_requests, bind_reviewed_scenes
from astra.asset_library import draw_asset_for_scene
from astra_v2.reviewed_art_bridge import build_approved_manifest


class ReviewedArtBridgeTests(unittest.TestCase):
    def test_empty_decisions_never_approve(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            queue, images, decisions = [root / x for x in ("queue.json", "images.json", "decisions.json")]
            queue.write_text(json.dumps({"rewrites": [{"status": "awaiting_independent_editorial_approval",
                "story": {"content_id": "test", "story_beats": [{"speech": "A fox searches."}]}}]}))
            images.write_text(json.dumps({"assets": []}))
            decisions.write_text(json.dumps({"schema_version": 1, "approved_scenes": []}))
            self.assertEqual(build_approved_manifest(queue, images, decisions, root, root), {"assets": []})

    def test_approved_real_png_binds_and_draws_exact_scene(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            art = root / "assets"
            art.mkdir()
            scene = art / "scene.png"
            Image.new("RGB", (540, 960), (90, 140, 180)).save(scene)
            digest = hashlib.sha256(scene.read_bytes()).hexdigest()
            story = {"content_id": "fox-story", "story_beats": [{"speech": "A fox finds a bell."}]}
            request = illustration_requests(story)[0]
            queue, images, decisions = [root / x for x in ("queue.json", "images.json", "decisions.json")]
            queue.write_text(json.dumps({"rewrites": [{"status": "awaiting_independent_editorial_approval",
                "story": story}]}))
            images.write_text(json.dumps({"assets": [{
                "story_content_id": "fox-story", "scene_id": "001",
                "story_visual_sha256": request["story_visual_sha256"],
                "status": "review_only", "sha256": digest, "path": "scene.png"}]}))
            decisions.write_text(json.dumps({"schema_version": 1, "approved_scenes": [{
                "decision": "approved", "story_content_id": "fox-story",
                "scene_id": "001", "sha256": digest}]}))
            with patch("astra_v2.omniroute_image_assets.image_quality_report",
                       return_value={"passed": True}):
                manifest = build_approved_manifest(queue, images, decisions, art, root)
            path = root / "art" / "manifest.json"
            path.write_text(json.dumps(manifest))
            plan = bind_reviewed_scenes([{"speech": "A fox finds a bell."}], "fox-story", path)
            frame = Image.new("RGB", (540, 960), (0, 0, 0))
            self.assertTrue(draw_asset_for_scene(frame, plan[0], manifest_path=path))
            self.assertEqual(frame.getpixel((270, 480)), (90, 140, 180))

    def test_unknown_approval_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            queue, images, decisions = [root / x for x in ("queue.json", "images.json", "decisions.json")]
            queue.write_text('{"rewrites":[]}')
            images.write_text('{"assets":[]}')
            decisions.write_text(json.dumps({"schema_version": 1, "approved_scenes": [{
                "decision": "approved", "story_content_id": "unknown",
                "scene_id": "001", "sha256": "a" * 64}]}))
            with self.assertRaises(ValueError):
                build_approved_manifest(queue, images, decisions, root, root)


if __name__ == "__main__":
    unittest.main()
