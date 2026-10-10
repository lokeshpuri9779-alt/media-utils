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

    def test_low_resolution_cannot_approve_hd_render(self):
        report={"engine":"CYCLES","median_warm_seconds":1,"resolution_x":360,"resolution_y":202,"samples":16}
        result=select_renderer(report,120,600,2,1280,720,32)
        self.assertEqual(result["reason"],"benchmark_not_representative")

    def test_matching_hd_benchmark_can_approve(self):
        report={"engine":"CYCLES","median_warm_seconds":1,"resolution_x":1280,"resolution_y":720,"samples":32}
        result=select_renderer(report,120,600,2,1280,720,32)
        self.assertEqual(result["engine"],"CYCLES")

    def test_invalid_budget_fails_closed(self):
        report={"engine":"CYCLES","median_warm_seconds":1}
        for frames, budget, factor in ((0,600,2),(-1,600,2),(120,0,2),(120,-1,2),(120,600,0.5)):
            with self.subTest(frames=frames,budget=budget,factor=factor):
                result=select_renderer(report,frames,budget,factor)
                self.assertEqual(result["reason"],"invalid_render_budget")

    def test_invalid_measurements(self):
        for value in (0, -1, None, "slow"):
            with self.subTest(value=value):
                result=select_renderer({"engine":"CYCLES","median_warm_seconds":value},120,600)
                self.assertEqual(result["engine"],"BLENDER_EEVEE")

if __name__ == "__main__":
    unittest.main()
