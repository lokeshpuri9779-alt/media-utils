"""End-to-end signed AI scene artwork export, binding and rendering checks."""
import hashlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from astra_v2.omniroute_image_assets import preproduce, export_reviewed_render_manifest
from astra_v2.story_art_direction import bind_reviewed_scenes
from astra.asset_library import draw_asset_for_scene, load_assets


def image_bytes():
    image = Image.new("RGB", (540, 960), (90, 140, 180))
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


class SignedArtEndToEndTests(unittest.TestCase):
    def test_approved_ai_image_exports_binds_and_renders_with_valid_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            story = {"content_id": "signed-fox", "story_beats": [
                {"speech": "The fox finds a bell."}]}
            queue = {"rewrites": [{"status": "awaiting_independent_editorial_approval",
                                    "story": story}]}
            with patch.dict(os.environ, {"ASTRA_ART_REVIEW_HMAC_KEY": "r" * 40}):
                with patch("astra_v2.omniroute_image_assets.image_quality_report",
                           return_value={"passed": True}):
                    produced = preproduce(queue, root, generator=lambda prompt: image_bytes())
                    asset = produced["assets"][0]
                    decision = {"approved": True, "sha256": asset["sha256"],
                                "semantic_match": True, "character_continuity": True}
                    manifest = root / "art" / "manifest.json"
                    result = export_reviewed_render_manifest(
                        produced, root, {asset["request_sha256"]: decision}, manifest)
                    self.assertEqual(result["assets"], 1)
                plan = bind_reviewed_scenes(
                    [{"speech": "The fox finds a bell."}], "signed-fox", manifest)
                frame = Image.new("RGB", (540, 960), (0, 0, 0))
                self.assertTrue(draw_asset_for_scene(frame, plan[0], manifest_path=manifest))
                self.assertEqual(frame.getpixel((270, 480)), (90, 140, 180))
                record = json.loads(manifest.read_text())["assets"][0]
                record["review_decision"]["character_continuity"] = False
                manifest.write_text(json.dumps({"assets": [record]}))
                self.assertEqual(load_assets(manifest), [])
                with self.assertRaises(ValueError):
                    bind_reviewed_scenes(plan, "signed-fox", manifest)

    def test_unsigned_or_wrong_key_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            story = {"content_id": "fox", "story_beats": [{"speech": "The bell rings."}]}
            queue = {"rewrites": [{"status": "awaiting_independent_editorial_approval",
                                    "story": story}]}
            with patch("astra_v2.omniroute_image_assets.image_quality_report",
                       return_value={"passed": True}):
                produced = preproduce(queue, root, generator=lambda prompt: image_bytes())
                asset = produced["assets"][0]
                decisions = {asset["request_sha256"]: {
                    "approved": True, "sha256": asset["sha256"],
                    "semantic_match": True, "character_continuity": True}}
                manifest = root / "art" / "manifest.json"
                with patch.dict(os.environ, {"ASTRA_ART_REVIEW_HMAC_KEY": ""}):
                    with self.assertRaises(ValueError):
                        export_reviewed_render_manifest(produced, root, decisions, manifest)
                with patch.dict(os.environ, {"ASTRA_ART_REVIEW_HMAC_KEY": "a" * 40}):
                    export_reviewed_render_manifest(produced, root, decisions, manifest)
                with patch.dict(os.environ, {"ASTRA_ART_REVIEW_HMAC_KEY": "b" * 40}):
                    self.assertEqual(load_assets(manifest), [])


if __name__ == "__main__":
    unittest.main()
