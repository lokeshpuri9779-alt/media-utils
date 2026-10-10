"""Unit tests for the separate Blender Cycles budget router."""
import importlib.util
from pathlib import Path
import unittest

MODULE = Path(__file__).resolve().parents[1] / "tools" / "renderer_router.py"
spec = importlib.util.spec_from_file_location("cycles_budget_router", MODULE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
select_renderer = module.select_renderer

class CyclesBudgetTests(unittest.TestCase):
    def test_no_benchmark_defaults_to_eevee(self):
        self.assertEqual(select_renderer(None, 120, 600)["engine"], "BLENDER_EEVEE")

    def test_cycles_within_budget(self):
        result = select_renderer({"engine":"CYCLES","median_warm_seconds":1.5},120,600,2)
        self.assertEqual(result["engine"], "CYCLES")
        self.assertEqual(result["estimated_seconds"], 360)

    def test_cycles_over_budget(self):
        result = select_renderer({"engine":"CYCLES","median_warm_seconds":5},120,600,2)
        self.assertEqual(result["reason"], "cycles_over_budget")

    def test_invalid_measurements(self):
        for value in (0, -1, None, "slow"):
            with self.subTest(value=value):
                result=select_renderer({"engine":"CYCLES","median_warm_seconds":value},120,600)
                self.assertEqual(result["engine"],"BLENDER_EEVEE")

if __name__ == "__main__":
    unittest.main()
