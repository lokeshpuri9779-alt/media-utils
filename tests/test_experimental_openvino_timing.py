"""Offline timing checks for the experimental CPU benchmark; no model downloads."""
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import experimental_openvino_benchmark as benchmark


class FakeImage:
    width = 512
    height = 768

    def save(self, path, format=None):
        Path(path).write_bytes(b"fake-image")


class FakePipeline:
    @classmethod
    def from_pretrained(cls, *args, **kwargs):
        return cls()

    def reshape(self, **kwargs):
        pass

    def compile(self):
        pass

    def __call__(self, *args, **kwargs):
        return types.SimpleNamespace(images=[FakeImage()])


class CpuBenchmarkTimingTests(unittest.TestCase):
    def test_successful_timing_report_stays_unapproved(self):
        optimum = types.ModuleType("optimum")
        optimum.__path__ = []
        intel = types.ModuleType("optimum.intel")
        intel.OVStableDiffusionPipeline = FakePipeline
        pillow = types.ModuleType("PIL")
        pillow.Image = types.SimpleNamespace(Image=FakeImage)
        assets = types.ModuleType("astra_v2.omniroute_image_assets")
        assets.image_quality_report = lambda data, kind: {"passed": True}
        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            sys.modules, {"optimum": optimum, "optimum.intel": intel,
                          "PIL": pillow, "astra_v2.omniroute_image_assets": assets}
        ):
            output = Path(tmp) / "keyframe.png"
            report = benchmark.run(output=output)
            persisted = json.loads(output.with_suffix(".json").read_text())
            for key in ("model_load_seconds", "reshape_compile_seconds",
                        "inference_seconds", "elapsed_seconds", "peak_rss_kib"):
                self.assertIn(key, report)
                self.assertGreaterEqual(report[key], 0)
                self.assertEqual(report[key], persisted[key])
            self.assertTrue(report["render_completed"])
            self.assertFalse(report["approved"])
            self.assertFalse(report["production_ready"])
            self.assertFalse(report["published"])
            self.assertTrue(report["manual_visual_review_required"])

    def test_inference_failure_records_elapsed_time_without_approval(self):
        class BrokenPipeline(FakePipeline):
            def __call__(self, *args, **kwargs):
                raise RuntimeError("synthetic inference failure")

        optimum = types.ModuleType("optimum")
        optimum.__path__ = []
        intel = types.ModuleType("optimum.intel")
        intel.OVStableDiffusionPipeline = BrokenPipeline
        pillow = types.ModuleType("PIL")
        pillow.Image = types.SimpleNamespace(Image=FakeImage)
        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            sys.modules, {"optimum": optimum, "optimum.intel": intel, "PIL": pillow}
        ):
            report = benchmark.run(output=Path(tmp) / "keyframe.png")
            self.assertEqual(report["error_type"], "RuntimeError")
            self.assertEqual(report["error_stage"], "inference")
            self.assertTrue(report["error_frames"])
            self.assertTrue(all(set(frame) == {"module_file", "function", "line"} for frame in report["error_frames"]))
            self.assertEqual(report["error_frames"], json.loads((Path(tmp) / "keyframe.json").read_text())["error_frames"])
            self.assertIn("inference_seconds", report)
            self.assertFalse(report["success"])
            self.assertFalse(report["production_ready"])


    def test_model_load_attribute_error_reports_stage_and_name(self):
        class BrokenLoad(FakePipeline):
            @classmethod
            def from_pretrained(cls, *args, **kwargs):
                obj = types.SimpleNamespace()
                return obj.nonexistent_component

        optimum = types.ModuleType("optimum")
        optimum.__path__ = []
        intel = types.ModuleType("optimum.intel")
        intel.OVStableDiffusionPipeline = BrokenLoad
        pillow = types.ModuleType("PIL")
        pillow.Image = types.SimpleNamespace(Image=FakeImage)
        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            sys.modules, {"optimum": optimum, "optimum.intel": intel, "PIL": pillow}
        ):
            output = Path(tmp) / "keyframe.png"
            report = benchmark.run(output=output)
            self.assertEqual(report["error_type"], "AttributeError")
            self.assertEqual(report["error_stage"], "model_load")
            self.assertEqual(report["missing_attribute"], "nonexistent_component")
            self.assertTrue(report["error_frames"])
            self.assertFalse(report["render_completed"])
            self.assertFalse(report["approved"])
            self.assertFalse(report["production_ready"])
            self.assertFalse(report["published"])
            self.assertEqual(report["error_stage"], json.loads(output.with_suffix(".json").read_text())["error_stage"])


if __name__ == "__main__":
    unittest.main()
