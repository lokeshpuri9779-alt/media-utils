"""Regression checks for immutable story image storage and cache integrity."""
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw
from astra_v2.omniroute_image_assets import preproduce, store_asset


def picture():
    im = Image.new("RGB", (512, 768))
    draw = ImageDraw.Draw(im)
    for y in range(768):
        draw.line((0, y, 511, y), fill=(y % 230 + 10, (y * 3) % 230 + 10, (y * 7) % 230 + 10))
    out = io.BytesIO()
    im.save(out, format="PNG")
    return out.getvalue()


class AssetCacheIntegrityTests(unittest.TestCase):
    def test_content_addressed_store_deduplicates_and_rejects_corruption(self):
        data = picture()
        with tempfile.TemporaryDirectory() as temp:
            a = store_asset(data, temp, kind="scene", prompt="scene A")
            b = store_asset(data, temp, kind="scene", prompt="scene B")
            self.assertEqual(a["path"], b["path"])
            self.assertEqual(len(list(Path(temp).rglob("*.png"))), 1)
            location = Path(temp) / a["path"]
            location.write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "corruption"):
                store_asset(data, temp, kind="scene", prompt="scene A")

    def test_cache_does_not_inherit_untrusted_approval_or_prompt(self):
        data = picture()
        story = {"content_id": "ci-image-identity", "title": "An unusual bridge",
                 "story_beats": [{"speech": "A fox crosses the bridge."}]}
        queue = {"rewrites": [{"status": "awaiting_independent_editorial_approval", "story": story}]}
        with tempfile.TemporaryDirectory() as temp:
            generated = preproduce(queue, temp, generator=lambda _: data, limit=1)
            self.assertEqual(generated["assets"][0]["status"], "review_only")
            record = next((Path(temp) / "requests").glob("*.json"))
            saved = json.loads(record.read_text())
            saved.update(approved=True, production_ready=True, status="approved")
            record.write_text(json.dumps(saved))
            cached = preproduce(queue, temp, generator=lambda _: self.fail("unexpected generation"), limit=1)
            self.assertEqual(cached["assets"][0]["status"], "cached_review_only")
            self.assertFalse(cached["assets"][0]["approved"])
            self.assertFalse(cached["assets"][0]["production_ready"])
            saved["prompt_sha256"] = hashlib.sha256(b"different prompt").hexdigest()
            record.write_text(json.dumps(saved))
            rejected = preproduce(queue, temp, generator=lambda _: self.fail("unexpected generation"), limit=1)
            self.assertEqual(rejected["assets"][0]["status"], "generation_failed")


if __name__ == "__main__":
    unittest.main()
