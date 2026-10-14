"""Regression checks for ASTRA renderer provenance handoff.

These checks use source inspection, without rendering or publishing.
"""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / "astra_v2"


class RendererProvenanceTests(unittest.TestCase):
    def test_fresh_candidate_returns_renderer(self):
        tree = ast.parse((ROOT / "creative.py").read_text(encoding="utf-8"))
        fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "make_candidate")
        returns = [n.value for n in ast.walk(fn) if isinstance(n, ast.Return) and isinstance(n.value, ast.Dict)]
        self.assertTrue(any(any(isinstance(k, ast.Constant) and k.value == "renderer" for k in d.keys) for d in returns))

    def test_preload_package_preserves_renderer(self):
        src = (ROOT / "preload_queue.py").read_text(encoding="utf-8")
        self.assertIn('payload["renderer"] = candidate["renderer"]', src)

    def test_preflight_records_renderer(self):
        src = (ROOT / "preflight.py").read_text(encoding="utf-8")
        self.assertIn('"renderer": item.get("renderer") or entry.get("renderer") or "unknown"', src)
        self.assertIn('"renderer": entry.get("renderer") or "unknown"', src)

    def test_publisher_records_renderer(self):
        src = (ROOT / "run.py").read_text(encoding="utf-8")
        self.assertIn('"renderer": candidate.get("renderer") or "astra-v2"', src)
        self.assertIn('renderer=candidate.get("renderer") or "astra-v2"', src)


if __name__ == "__main__":
    unittest.main()
