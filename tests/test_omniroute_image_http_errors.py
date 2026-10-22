import io
import unittest
import urllib.error
from unittest.mock import patch

from astra_v2.omniroute_image_assets import generate_image


class OmniImageHttpErrorTests(unittest.TestCase):
    def test_404_is_actionable_without_exposing_secret(self):
        env = {
            "ASTRA_OMNI_IMAGE_ENDPOINT": "https://example.invalid/v1/images/generations",
            "ASTRA_OMNI_IMAGE_MODEL": "free-test-model",
            "ASTRA_OMNI_IMAGE_FREE_CONFIRMED": "1",
            "ASTRA_OMNI_IMAGE_API_KEY": "never-print-this-key",
        }
        def failing_request(request):
            raise urllib.error.HTTPError(request.full_url, 404, "Not Found", {}, io.BytesIO(b""))
        with patch.dict("os.environ", env, clear=True):
            with self.assertRaisesRegex(ValueError, "HTTP 404") as caught:
                generate_image("scene", requester=failing_request)
        self.assertNotIn("never-print-this-key", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
