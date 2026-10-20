import json
import tempfile
import unittest
from pathlib import Path
from astra_v2.plot_first_inventory import append_plot_first


class PlotFirstInventoryTests(unittest.TestCase):
    def test_append_is_idempotent_and_unreviewed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ledger = root / "ledger.json"
            ledger.write_text(json.dumps({"next_index": 7, "proposals": []}), encoding="utf-8")
            publisher = root / "publisher.json"
            history = root / "history.json"
            self.assertEqual(append_plot_first(ledger, 2, publisher, history), 2)
            first = json.loads(ledger.read_text(encoding="utf-8"))
            self.assertEqual(first["next_index"], 7)
            self.assertTrue(all(not x["production_ready"] for x in first["proposals"]))
            self.assertEqual(append_plot_first(ledger, 2, publisher, history), 2)
            second = json.loads(ledger.read_text(encoding="utf-8"))
            self.assertEqual(len({x["content_id"] for x in second["proposals"]}), 4)
            self.assertEqual(append_plot_first(ledger, 0, publisher, history), 0)

    def test_invalid_ledger_does_not_get_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "ledger.json"
            ledger.write_text('{"proposals":"bad"}', encoding="utf-8")
            with self.assertRaises(ValueError):
                append_plot_first(ledger, 1)
            self.assertEqual(ledger.read_text(encoding="utf-8"), '{"proposals":"bad"}')


if __name__ == "__main__":
    unittest.main()
