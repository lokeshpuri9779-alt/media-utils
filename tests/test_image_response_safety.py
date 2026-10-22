import base64
import json
import unittest
from unittest.mock import patch
from astra_v2.omniroute_image_assets import generate_image, MAX_BYTES


class ImageResponseSafetyTests(unittest.TestCase):
    def setUp(self):
        self.env = {
            "ASTRA_OMNI_IMAGE_ENDPOINT": "https://example.com/v1/images/generations",
            "ASTRA_OMNI_IMAGE_MODEL": "test",
            "ASTRA_OMNI_IMAGE_FREE_CONFIRMED": "1",
        }

    def test_invalid_base64_is_rejected_without_raw_payload(self):
        with patch.dict("os.environ", self.env, clear=True):
            with self.assertRaisesRegex(ValueError, "invalid base64"):
                generate_image("scene", requester=lambda req: json.dumps({"data": [{"b64_json": "not-base64!"}]}).encode())

    def test_valid_payload_remains_supported(self):
        with patch.dict("os.environ", self.env, clear=True):
            raw = b"small-test-image"
            response = json.dumps({"data": [{"b64_json": base64.b64encode(raw).decode()}]}).encode()
            self.assertEqual(generate_image("scene", requester=lambda req: response), raw)


if __name__ == "__main__":
    unittest.main()
