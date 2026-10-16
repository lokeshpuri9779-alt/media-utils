"""Guard fingerprint metadata across Shorts selection and publication stages."""
import unittest
from pathlib import Path
from astra_v2.original_stories import catalog


class ShortsFingerprintLifecycleTests(unittest.TestCase):
    def test_original_stories_provide_stable_fingerprints(self):
        first = catalog()
        second = catalog()
        self.assertEqual([s["plot_fingerprint"] for s in first],
                         [s["plot_fingerprint"] for s in second])
        self.assertTrue(all(len(s["plot_fingerprint"]) == 64 for s in first))

    def test_metadata_carried_through_selection_and_publisher(self):
        root = Path(__file__).resolve().parents[1]
        creative = (root / "astra_v2" / "creative.py").read_text(encoding="utf-8")
        publisher = (root / "astra_v2" / "run.py").read_text(encoding="utf-8")
        self.assertIn('"plot_fingerprint": story.get("plot_fingerprint", "")', creative)
        self.assertIn('"plot_fingerprint": str(meta.get("plot_fingerprint") or "")', creative)
        self.assertIn('"plot_fingerprint": candidate.get("plot_fingerprint", "")', publisher)
        self.assertIn('"plot_fingerprint": item.get("plot_fingerprint", "")', publisher)


if __name__ == "__main__":
    unittest.main()
