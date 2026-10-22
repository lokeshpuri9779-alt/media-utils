"""Production media verification must run before a preload package is created."""
import ast
import unittest
from pathlib import Path


class ProductionMediaContractTests(unittest.TestCase):
    def test_media_inspection_precedes_package_creation(self):
        source = Path("astra_v2/preload_worker.py").read_text()
        tree = ast.parse(source)
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
        calls = [n for n in ast.walk(fn) if isinstance(n, ast.Call)]
        def offset(name):
            return min(n.lineno for n in calls if isinstance(n.func, ast.Name) and n.func.id == name)
        self.assertLess(offset("inspect_video"), offset("prepare"))
        self.assertLess(offset("prepare"), offset("archive_preload_if_enabled"))


if __name__ == "__main__":
    unittest.main()
