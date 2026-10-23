import base64
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from astra_v2.omniroute_image_assets import store_asset, preproduce, image_endpoint, generate_image, generate_free_image_with_failover


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

    def test_native_gemini_requests_portrait_aspect_ratio(self):
        import json
        env = {"ASTRA_OMNI_IMAGE_ENDPOINT":
               "https://generativelanguage.googleapis.com/v1beta/models/gemini-test:generateContent",
               "ASTRA_OMNI_IMAGE_MODEL": "gemini-test",
               "ASTRA_OMNI_IMAGE_FREE_CONFIRMED": "1"}
        def requester(request):
            payload = json.loads(request.data)
            self.assertEqual(payload["generationConfig"]["imageConfig"]["aspectRatio"], "9:16")
            self.assertEqual(payload["generationConfig"]["responseModalities"], ["IMAGE"])
            return json.dumps({"candidates": [{"content": {"parts": [
                {"inlineData": {"mimeType": "image/png",
                                "data": base64.b64encode(png()).decode()}}]}}]}).encode()
        with patch.dict("os.environ", env, clear=True):
            self.assertEqual(generate_image("portrait scene", requester=requester), png())

    def test_cloudflare_flux_image_contract(self):
        import base64
        import json
        env = {"ASTRA_OMNI_IMAGE_ENDPOINT": "https://api.cloudflare.com/client/v4/accounts/example/ai/run/@cf/black-forest-labs/flux-1-schnell",
               "ASTRA_OMNI_IMAGE_MODEL": "@cf/black-forest-labs/flux-1-schnell",
               "ASTRA_OMNI_IMAGE_FREE_CONFIRMED": "1"}
        def requester(request):
            payload = json.loads(request.data)
            self.assertEqual(payload["steps"], 4)
            self.assertNotIn("width", payload)
            self.assertNotIn("height", payload)
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

    def test_http_429_stops_subsequent_provider_calls(self):
        queue = {"rewrites": [{"status": "awaiting_independent_editorial_approval",
                  "story": {"title": "New story", "content_id": "quota-test",
                            "story_beats": [
                                {"speech": "A first event occurs."},
                                {"speech": "A second event occurs."},
                                {"speech": "A third event occurs."}]}}]}
        calls = []
        def quota_limited(prompt):
            calls.append(prompt)
            raise ValueError("Image provider HTTP 429 Cloudflare code=4006")
        with tempfile.TemporaryDirectory() as root:
            result = preproduce(queue, root, generator=quota_limited, limit=10)
        self.assertEqual(len(calls), 1)
        self.assertEqual(result["provider_calls"], 1)
        self.assertEqual(result["status"], "provider_quota_exhausted")
        self.assertEqual(result["assets"][0]["status"], "generation_failed")
        self.assertTrue(all(asset["status"] == "provider_quota_exhausted"
                            for asset in result["assets"][1:]))
        self.assertTrue(all(not asset["production_ready"] for asset in result["assets"]))

    def test_free_fallback_only_after_429(self):
        import urllib.error
        env = {"ASTRA_OMNI_IMAGE_ENDPOINT": "https://primary.example/images",
               "ASTRA_OMNI_IMAGE_MODEL": "free-primary",
               "ASTRA_OMNI_IMAGE_FREE_CONFIRMED": "1",
               "ASTRA_OMNI_IMAGE_FALLBACK_ENDPOINT": "https://secondary.example/images",
               "ASTRA_OMNI_IMAGE_FALLBACK_MODEL": "free-secondary",
               "ASTRA_OMNI_IMAGE_FALLBACK_FREE_CONFIRMED": "1"}
        attempts = []
        def requester(request):
            attempts.append(request.full_url)
            if "primary" in request.full_url:
                raise urllib.error.HTTPError(request.full_url, 429, "quota", {}, io.BytesIO(b""))
            return png()
        with patch.dict("os.environ", env, clear=True):
            self.assertEqual(generate_free_image_with_failover("scene", requester=requester), png())
        self.assertEqual(attempts, ["https://primary.example/images", "https://secondary.example/images"])

    def test_fallback_requires_explicit_free_confirmation(self):
        env = {"ASTRA_OMNI_IMAGE_ENDPOINT": "https://primary.example/images",
               "ASTRA_OMNI_IMAGE_MODEL": "free-primary",
               "ASTRA_OMNI_IMAGE_FREE_CONFIRMED": "1",
               "ASTRA_OMNI_IMAGE_FALLBACK_ENDPOINT": "https://secondary.example/images",
               "ASTRA_OMNI_IMAGE_FALLBACK_MODEL": "free-secondary"}
        with patch.dict("os.environ", env, clear=True):
            with self.assertRaisesRegex(ValueError, "Fallback free-tier confirmation required"):
                generate_free_image_with_failover("scene", requester=lambda req: png())

    def test_non_quota_failure_never_triggers_fallback(self):
        import urllib.error
        env = {"ASTRA_OMNI_IMAGE_ENDPOINT": "https://primary.example/images",
               "ASTRA_OMNI_IMAGE_MODEL": "free-primary",
               "ASTRA_OMNI_IMAGE_FREE_CONFIRMED": "1",
               "ASTRA_OMNI_IMAGE_FALLBACK_ENDPOINT": "https://secondary.example/images",
               "ASTRA_OMNI_IMAGE_FALLBACK_MODEL": "free-secondary",
               "ASTRA_OMNI_IMAGE_FALLBACK_FREE_CONFIRMED": "1"}
        attempts = []
        def requester(request):
            attempts.append(request.full_url)
            raise urllib.error.HTTPError(request.full_url, 403, "denied", {}, io.BytesIO(b""))
        with patch.dict("os.environ", env, clear=True):
            with self.assertRaisesRegex(ValueError, "Image provider HTTP 403"):
                generate_free_image_with_failover("scene", requester=requester)
        self.assertEqual(attempts, ["https://primary.example/images"])

    def test_both_free_providers_quota_exhausted(self):
        import urllib.error
        env = {"ASTRA_OMNI_IMAGE_ENDPOINT": "https://primary.example/images",
               "ASTRA_OMNI_IMAGE_MODEL": "free-primary",
               "ASTRA_OMNI_IMAGE_FREE_CONFIRMED": "1",
               "ASTRA_OMNI_IMAGE_FALLBACK_ENDPOINT": "https://secondary.example/images",
               "ASTRA_OMNI_IMAGE_FALLBACK_MODEL": "free-secondary",
               "ASTRA_OMNI_IMAGE_FALLBACK_FREE_CONFIRMED": "1"}
        attempts = []
        def requester(request):
            attempts.append(request.full_url)
            raise urllib.error.HTTPError(request.full_url, 429, "quota", {}, io.BytesIO(b""))
        with patch.dict("os.environ", env, clear=True):
            with self.assertRaisesRegex(ValueError, "Image provider HTTP 429"):
                generate_free_image_with_failover("scene", requester=requester)
        self.assertEqual(attempts, ["https://primary.example/images", "https://secondary.example/images"])

    def test_fallback_only_can_run_without_primary(self):
        env = {"ASTRA_OMNI_IMAGE_FALLBACK_ENDPOINT": "https://secondary.example/images",
               "ASTRA_OMNI_IMAGE_FALLBACK_MODEL": "free-secondary",
               "ASTRA_OMNI_IMAGE_FALLBACK_FREE_CONFIRMED": "1"}
        with patch.dict("os.environ", env, clear=True):
            self.assertEqual(generate_free_image_with_failover("scene", requester=lambda req: png()), png())

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
