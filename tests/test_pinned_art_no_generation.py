import ast
import unittest
from pathlib import Path


class PinnedArtNoGenerationTests(unittest.TestCase):
    def test_both_ai_generation_branches_are_disabled_when_art_pinned(self):
        tree = ast.parse(Path("astra_v2/creative.py").read_text())
        make_candidate = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "make_candidate")
        branches = []
        for node in ast.walk(make_candidate):
            if isinstance(node, ast.If):
                condition = ast.unparse(node.test)
                if "omni_enabled()" in condition or "openai_enabled()" in condition:
                    branches.append(condition)
        self.assertEqual(len(branches), 2)
        for condition in branches:
            self.assertIn('not os.getenv(\'ASTRA_PRELOAD_REVIEWED_ART_MANIFEST\')', condition)


if __name__ == "__main__":
    unittest.main()
