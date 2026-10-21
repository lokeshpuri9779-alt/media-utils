import tempfile
import unittest
from pathlib import Path
from astra_v2.adaptive_intake import register_reviewed
from astra_v2.adaptive_warehouse import Warehouse


class AdaptiveIntakeTests(unittest.TestCase):
    def test_requires_complete_history(self):
        with tempfile.TemporaryDirectory() as folder:
            warehouse = Warehouse(Path(folder) / "warehouse.json")
            with self.assertRaises(ValueError):
                register_reviewed([], [], None, warehouse)

    def test_never_invents_approval(self):
        with tempfile.TemporaryDirectory() as folder:
            warehouse = Warehouse(Path(folder) / "warehouse.json")
            result = register_reviewed([], [], [], warehouse)
            self.assertEqual(result["registered"], [])
            self.assertFalse(result["publication_triggered"])


if __name__ == "__main__":
    unittest.main()
