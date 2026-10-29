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
        self.assertIn("toy fire engine", sdxl.ONE_IMAGE_PROMPT)
        self.assertIn("one vehicle only", sdxl.ONE_IMAGE_PROMPT)
        self.assertEqual(sdxl.MODEL, "OpenVINO/stable-diffusion-xl-base-1.0-int8-ov")

    def test_cpu_probe_is_small_and_review_only(self):
        source = inspect.getsource(sdxl.worker)
        self.assertIn("height=1024, width=1024, num_inference_steps=ONE_IMAGE_STEPS", source)
        self.assertIn("torch.randn((1, 4, 128, 128)", source)
        self.assertIn("height=1024, width=1024", source)
        self.assertIn("Expected exactly one 1024x1024 diagnostic image", source)

    def test_size_conditioning_is_explicit_and_recorded(self):
        source = inspect.getsource(sdxl.worker)
        self.assertIn("save('conditioning.json'", source)
        self.assertIn("original_size=size, target_size=size, crops_coords_top_left=crop", source)
        self.assertIn("negative_original_size=size, negative_target_size=size", source)
        self.assertIn("time_ids.tolist() != [[1024, 1024, 0, 0, 1024, 1024]]", source)

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
