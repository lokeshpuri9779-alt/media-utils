import base64
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from astra_v2.omniroute_image_assets import store_asset, preproduce, image_endpoint, generate_image


def png(alpha=False, portrait=True):
    image = Image.new("RGBA" if alpha else "RGB", (512, 768 if portrait else 512),
                      (50, 80, 120, 0 if alpha else 255))
    from PIL import ImageDraw
    draw = ImageDraw.Draw(image)
    for y in range(image.height):
        draw.line((0, y, image.width - 1, y), fill=(50 + y // 32, 80 + y // 16, 120 + y // 12, 0 if alpha else 255))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class ImageAssetsTests(unittest.TestCase):
    def test_unconfigured_does_not_call_paid_provider(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertIsNone(image_endpoint())

    def test_direct_png_provider_response(self):
        env = {"ASTRA_OMNI_IMAGE_ENDPOINT": "https://example.org/images",
               "ASTRA_OMNI_IMAGE_MODEL": "free-model",
               "ASTRA_OMNI_IMAGE_FREE_CONFIRMED": "1"}
        with patch.dict("os.environ", env, clear=True):
            self.assertEqual(generate_image("scene", requester=lambda req: png()), png())

    def test_direct_jpeg_provider_response_is_normalized(self):
        image = Image.new("RGB", (512, 768), (80, 120, 160))
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG")
        env = {"ASTRA_OMNI_IMAGE_ENDPOINT": "https://example.org/images",
               "ASTRA_OMNI_IMAGE_MODEL": "free-model",
               "ASTRA_OMNI_IMAGE_FREE_CONFIRMED": "1"}
        with patch.dict("os.environ", env, clear=True):
            output = generate_image("scene", requester=lambda req: buffer.getvalue())
            self.assertTrue(output.startswith(b"\x89PNG\r\n\x1a\n"))

    def test_cloudflare_flux_image_contract(self):
        import base64
        import json
        env = {"ASTRA_OMNI_IMAGE_ENDPOINT": "https://api.cloudflare.com/client/v4/accounts/example/ai/run/@cf/black-forest-labs/flux-1-schnell",
               "ASTRA_OMNI_IMAGE_MODEL": "@cf/black-forest-labs/flux-1-schnell",
               "ASTRA_OMNI_IMAGE_FREE_CONFIRMED": "1"}
        def requester(request):
            payload = json.loads(request.data)
            self.assertEqual(payload["steps"], 4)
            self.assertEqual(payload["prompt"], "scene")
            return json.dumps({"success": True, "result": {"image": base64.b64encode(png()).decode()}}).encode()
        with patch.dict("os.environ", env, clear=True):
            result = generate_image("scene", requester=requester)
            self.assertTrue(result.startswith(bytes.fromhex("89504e470d0a1a0a")))

    def test_cloudflare_http_error_code_is_sanitized(self):
        import json
        import urllib.error
        env = {"ASTRA_OMNI_IMAGE_ENDPOINT": "https://api.cloudflare.com/client/v4/accounts/example/ai/run/@cf/black-forest-labs/flux-1-schnell",
               "ASTRA_OMNI_IMAGE_MODEL": "@cf/black-forest-labs/flux-1-schnell",
               "ASTRA_OMNI_IMAGE_FREE_CONFIRMED": "1"}
        def requester(request):
            raise urllib.error.HTTPError(request.full_url, 403, "secret should not leak", {},
                                         io.BytesIO(json.dumps({"errors": [{"code": 10000, "message": "private"}]}).encode()))
        with patch.dict("os.environ", env, clear=True):
            with self.assertRaisesRegex(ValueError, "Image provider HTTP 403 Cloudflare code=10000") as raised:
                generate_image("private prompt", requester=requester)
            self.assertNotIn("private", str(raised.exception))

    def test_preproduction_failure_detail_is_safe(self):
        queue = {"rewrites": [{"status": "awaiting_independent_editorial_approval",
                  "story": {"title": "New story", "content_id": "abc",
                            "story_beats": [{"speech": "A new visual event occurs."}]}}]}
        with tempfile.TemporaryDirectory() as root:
            def fail(prompt):
                raise ValueError("Image provider HTTP 403 Cloudflare code=10000")
            result = preproduce(queue, root, generator=fail)
            failures = [asset for asset in result["assets"] if asset["status"] == "generation_failed"]
            self.assertEqual(failures[0]["error_detail"], "Image provider HTTP 403 Cloudflare code=10000")

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
