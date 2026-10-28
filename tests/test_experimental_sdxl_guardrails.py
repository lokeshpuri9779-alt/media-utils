"""Offline safety checks for optional SDXL CPU diagnostic; no model downloads."""
import inspect
import unittest

from tools import experimental_sdxl_load as sdxl


class SDXLOneImageGuardrailTests(unittest.TestCase):
    def test_inference_is_explicitly_opt_in(self):
        self.assertIs(inspect.signature(sdxl.worker).parameters["one_image"].default, False)
        self.assertIs(inspect.signature(sdxl.supervise).parameters["one_image"].default, False)

    def test_single_fixed_image_configuration(self):
        self.assertEqual(sdxl.ONE_IMAGE_SEED, 42)
        self.assertEqual(sdxl.ONE_IMAGE_STEPS, 20)
        self.assertIn("toy fire truck", sdxl.ONE_IMAGE_PROMPT)
        self.assertIn("no text", sdxl.ONE_IMAGE_PROMPT)
        self.assertEqual(sdxl.MODEL, "OpenVINO/stable-diffusion-xl-base-1.0-int8-ov")

    def test_existing_memory_and_time_limits_remain(self):
        gib = sdxl.GIB
        self.assertEqual(sdxl.limit_reason(12 * gib, 5 * gib, 1, 1), "rss_limit")
        self.assertEqual(sdxl.limit_reason(1 * gib, 1 * gib, 1, 1), "available_ram_limit")
        self.assertEqual(sdxl.limit_reason(1 * gib, 5 * gib, 1, 600), "load_compile_timeout")
        self.assertEqual(sdxl.limit_reason(1 * gib, 5 * gib, 1, None, 900), "inference_timeout")
        self.assertEqual(sdxl.limit_reason(1 * gib, 5 * gib, 1200, None, None), "overall_timeout")
        self.assertIsNone(sdxl.limit_reason(1 * gib, 5 * gib, 899, None, 899))

    def test_review_metadata_never_implies_approval(self):
        source = inspect.getsource(sdxl.worker)
        self.assertIn("'approved': False", source)
        self.assertIn("'production_ready': False", source)
        self.assertIn("'published': False", source)
        self.assertIn("'semantic_quality': 'not_verified'", source)
        self.assertIn("'manual_visual_review_required': True", source)


if __name__ == "__main__":
    unittest.main()
