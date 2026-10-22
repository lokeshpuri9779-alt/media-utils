import base64
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from astra_v2.gemini_art_staging import generate_staged_art


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, *args):
        return json.dumps(self.payload).encode()


class GeminiArtStagingTests(unittest.TestCase):
    def story(self):
        return {"content_id": "test_story", "story_beats": [
            {"scene_id": "scene-1", "visual_prompt": "A little fox standing beside a river at sunrise."}]}

    def test_stages_image_without_approval(self):
        buf = io.BytesIO()
        Image.new("RGB", (360, 640), (20, 50, 80)).save(buf, "PNG")
        payload = {"candidates": [{"content": {"parts": [{"inlineData": {
            "mimeType": "image/png", "data": base64.b64encode(buf.getvalue()).decode()}}]}}]}
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"ASTRA_GEMINI_ART_ENABLED": "1",
                                         "GEMINI_API_KEY": "test", "ASTRA_GEMINI_IMAGE_MODEL": "test-image"}):
                manifest = generate_staged_art(self.story(), Path(temp) / "staged",
                    opener=lambda *args, **kwargs: FakeResponse(payload))
            data = json.loads(manifest.read_text())
            self.assertFalse(data["publication_triggered"])
            self.assertEqual(data["assets"][0]["status"], "pending_review")
            self.assertTrue((manifest.parent / "scene-1.png").is_file())

    def test_disabled_fails_closed(self):
        with patch.dict(os.environ, {"ASTRA_GEMINI_ART_ENABLED": "0"}):
            with self.assertRaisesRegex(ValueError, "not_enabled"):
                generate_staged_art(self.story(), "unused")


if __name__ == "__main__":
    unittest.main()
