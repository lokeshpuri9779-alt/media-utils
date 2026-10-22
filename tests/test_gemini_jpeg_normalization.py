import base64
import io
import json
import unittest
from unittest.mock import patch
from PIL import Image
from astra_v2.omniroute_image_assets import generate_image, validate_png


class GeminiJpegNormalizationTests(unittest.TestCase):
    def test_native_jpeg_is_normalized_to_png(self):
        buffer = io.BytesIO()
        Image.new("RGB", (640, 960), (80, 120, 170)).save(buffer, format="JPEG")
        response = json.dumps({"candidates": [{"content": {"parts": [{
            "inlineData": {"mimeType": "image/jpeg", "data": base64.b64encode(buffer.getvalue()).decode()}
        }]}}]}).encode()
        env = {"ASTRA_OMNI_IMAGE_ENDPOINT": "https://generativelanguage.googleapis.com/v1beta/models/test:generateContent",
               "ASTRA_OMNI_IMAGE_MODEL": "test", "ASTRA_OMNI_IMAGE_FREE_CONFIRMED": "1"}
        with patch.dict("os.environ", env, clear=True):
            result = generate_image("portrait scene", requester=lambda req: response)
        self.assertEqual(validate_png(result, "scene"), {"width": 640, "height": 960})


if __name__ == "__main__":
    unittest.main()
