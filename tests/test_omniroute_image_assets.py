import base64
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from astra_v2.omniroute_image_assets import store_asset, preproduce, image_endpoint


def png(alpha=False, portrait=True):
    image = Image.new("RGBA" if alpha else "RGB", (512, 768 if portrait else 512),
                      (50, 80, 120, 0 if alpha else 255))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class ImageAssetsTests(unittest.TestCase):
    def test_unconfigured_does_not_call_paid_provider(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertIsNone(image_endpoint())

    def test_immutable_deduplication_and_corruption(self):
        with tempfile.TemporaryDirectory() as root:
            a = store_asset(png(), root, kind="scene", prompt="first")
            b = store_asset(png(), root, kind="scene", prompt="second")
            self.assertEqual(a["path"], b["path"])
            path = Path(root) / a["path"]
            path.write_bytes(b"corrupt")
            with self.assertRaises(ValueError):
                store_asset(png(), root, kind="scene", prompt="first")

    def test_transparency_and_portrait_rules(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):
                store_asset(png(), root, kind="character", prompt="x")
            with self.assertRaises(ValueError):
                store_asset(png(portrait=False), root, kind="scene", prompt="x")
            self.assertFalse(store_asset(png(alpha=True), root, kind="prop", prompt="x")["approved"])

    def test_preproduced_assets_remain_review_only(self):
        queue = {"rewrites": [{"status": "awaiting_independent_editorial_approval",
                  "story": {"title": "New story", "content_id": "abc",
                            "story_beats": [{"speech": "A new visual event occurs."}]}}]}
        with tempfile.TemporaryDirectory() as root:
            result = preproduce(queue, root, generator=lambda prompt: png())
            self.assertEqual(len(result["assets"]), 1)
            self.assertFalse(result["assets"][0]["production_ready"])


if __name__ == "__main__":
    unittest.main()
