import base64
import io
import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from astra.gemini_image_preview import generate_preview
from astra.asset_library import load_assets


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload
    def __enter__(self):
        return io.BytesIO(json.dumps(self.payload).encode())
    def __exit__(self, *args):
        return False


class GeminiImagePreviewTests(unittest.TestCase):
    def test_generated_image_remains_unapproved(self):
        image = Image.new("RGB", (600, 1000), "teal")
        out = io.BytesIO()
        image.save(out, format="PNG")
        payload = {"candidates": [{"finishReason": "STOP", "content": {"parts": [
            {"inlineData": {"mimeType": "image/png",
                            "data": base64.b64encode(out.getvalue()).decode()}}
        ]}}]}
        def opener(request, timeout):
            self.assertEqual(timeout, 90)
            self.assertIn(b"responseModalities", request.data)
            return FakeResponse(payload)
        with tempfile.TemporaryDirectory() as tmp:
            result = generate_preview("A fox crossing a rainy bridge", tmp,
                api_key="fixture-key", opener=opener)
            manifest = Path(result["manifest"])
            row = json.loads(manifest.read_text())["assets"][0]
            self.assertEqual(row["status"], "pending_review")
            self.assertEqual(len(row["sha256"]), 64)
            self.assertEqual(load_assets(manifest), [])
            self.assertFalse((Path(tmp) / "art" / "manifest.json").exists())

    def test_rejects_missing_image(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "expected_exactly_one_image"):
                generate_preview("A fox crossing a rainy bridge", tmp,
                    api_key="fixture-key", opener=lambda *a, **kw: FakeResponse(
                        {"candidates": [{"content": {"parts": [{"text": "no image"}]}}]}))


if __name__ == "__main__":
    unittest.main()
