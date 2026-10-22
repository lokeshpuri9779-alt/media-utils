import base64
import json
import unittest
from unittest.mock import patch

from astra_v2.omniroute_image_assets import generate_image


class GeminiImageContractTests(unittest.TestCase):
    def test_native_gemini_request_and_response(self):
        png = b"example-png-bytes"
        env = {
            "ASTRA_OMNI_IMAGE_ENDPOINT": "https://generativelanguage.googleapis.com/v1beta/models/gemini-image-test:generateContent",
            "ASTRA_OMNI_IMAGE_MODEL": "gemini-image-test",
            "ASTRA_OMNI_IMAGE_FREE_CONFIRMED": "1",
            "ASTRA_OMNI_IMAGE_API_KEY": "secret",
        }
        def requester(req):
            self.assertEqual(req.get_header("X-goog-api-key"), "secret")
            self.assertIsNone(req.get_header("Authorization"))
            body = json.loads(req.data)
            self.assertEqual(body["contents"][0]["parts"][0]["text"], "scene")
            self.assertEqual(body["generationConfig"]["responseModalities"], ["IMAGE"])
            return json.dumps({"candidates": [{"content": {"parts": [{
                "inlineData": {"mimeType": "image/png", "data": base64.b64encode(png).decode()}
            }]}}]}).encode()
        with patch.dict("os.environ", env, clear=True):
            self.assertEqual(generate_image("scene", requester=requester), png)

    def test_missing_gemini_image_fails_closed(self):
        env = {
            "ASTRA_OMNI_IMAGE_ENDPOINT": "https://generativelanguage.googleapis.com/v1beta/models/test:generateContent",
            "ASTRA_OMNI_IMAGE_MODEL": "test",
            "ASTRA_OMNI_IMAGE_FREE_CONFIRMED": "1",
        }
        with patch.dict("os.environ", env, clear=True):
            with self.assertRaisesRegex(ValueError, "exactly one supported image"):
                generate_image("scene", requester=lambda req: b'{"candidates": []}')


if __name__ == "__main__":
    unittest.main()
