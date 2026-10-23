import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw
from astra.asset_library import draw_asset_for_scene, load_assets
from astra_v2.omniroute_image_assets import store_asset, export_reviewed_render_manifest
from astra_v2.story_art_direction import bind_reviewed_scenes


def artwork():
    image = Image.new("RGB", (540, 960), (30, 70, 100))
    draw = ImageDraw.Draw(image)
    draw.rectangle((70, 120, 430, 850), fill=(170, 110, 60))
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


class OmniRouteReviewRenderRegression(unittest.TestCase):
    @patch.dict("os.environ", {"ASTRA_ART_REVIEW_HMAC_KEY": "test-only-review-secret-0123456789abcdef"})
    def test_approved_scene_is_bound_and_drawn_only_with_matching_review(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            raw = artwork()
            asset = store_asset(raw, root / "warehouse", kind="scene",
                                prompt="Original story illustration")
            request_id = hashlib.sha256(b"scene-request").hexdigest()
            preproduction = {"assets": [{
                **asset, "request_sha256": request_id, "status": "review_only",
                "story_content_id": "story-001", "scene_id": "001",
            }]}
            decision = {"approved": True, "sha256": asset["sha256"],
                        "semantic_match": True, "character_continuity": True}
            manifest = root / "art" / "manifest.json"
            with self.assertRaisesRegex(ValueError, "No independently approved"):
                export_reviewed_render_manifest(preproduction, root / "warehouse",
                                               {}, manifest)
            export_reviewed_render_manifest(preproduction, root / "warehouse",
                                            {request_id: decision}, manifest)
            assets = load_assets(manifest)
            self.assertEqual(len(assets), 1)
            tampered = json.loads(manifest.read_text())
            tampered["assets"][0]["review_decision"]["semantic_match"] = False
            manifest.write_text(json.dumps(tampered))
            self.assertEqual(load_assets(manifest), [])
            export_reviewed_render_manifest(preproduction, root / "warehouse",
                                            {request_id: decision}, manifest)
            with patch.dict("os.environ", {"ASTRA_ART_REVIEW_HMAC_KEY": "different-review-secret-0123456789abcdef"}):
                self.assertEqual(load_assets(manifest), [])
            self.assertEqual(assets[0]["review_status"], "approved")
            bound = bind_reviewed_scenes([{"speech": "An action occurs"}],
                                         "story-001", manifest)
            frame = Image.new("RGB", (1080, 1920), (0, 0, 0))
            self.assertTrue(draw_asset_for_scene(frame, bound[0], manifest_path=manifest))
            self.assertEqual(frame.getpixel((500, 500)), (170, 110, 60))
            self.assertFalse(draw_asset_for_scene(
                Image.new("RGB", (1080, 1920)), {**bound[0], "story_content_id": "other"},
                manifest_path=manifest))
            image_path = root / assets[0]["path"]
            image_path.write_bytes(b"tampered")
            self.assertEqual(load_assets(manifest), [])

    def test_unsigned_approval_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            asset = store_asset(artwork(), root / "warehouse", kind="scene", prompt="scene")
            request_id = hashlib.sha256(b"request").hexdigest()
            preproduction = {"assets": [{**asset, "request_sha256": request_id,
                                         "status": "review_only", "story_content_id": "story",
                                         "scene_id": "001"}]}
            decision = {request_id: {"approved": True, "sha256": asset["sha256"],
                                     "semantic_match": True, "character_continuity": True}}
            with patch.dict("os.environ", {"ASTRA_ART_REVIEW_HMAC_KEY": ""}):
                with self.assertRaisesRegex(ValueError, "signing key"):
                    export_reviewed_render_manifest(preproduction, root / "warehouse",
                                                    decision, root / "art" / "manifest.json")

    def test_fake_approval_metadata_does_not_replace_reviewed_image(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image_path = root / "art" / "image.png"
            image_path.parent.mkdir(parents=True)
            image_path.write_bytes(artwork())
            manifest = root / "art" / "manifest.json"
            manifest.write_text(json.dumps({"assets": [{
                "id": "image", "path": "art/image.png", "category": "background",
                "status": "approved", "source": "omniroute",
                "sha256": hashlib.sha256(image_path.read_bytes()).hexdigest(),
            }]}))
            self.assertEqual(load_assets(manifest), [])


if __name__ == "__main__":
    unittest.main()
