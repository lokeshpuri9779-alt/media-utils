import tempfile
import unittest
from pathlib import Path

from astra.background_factory import SCENES, generate, render
from astra.asset_inventory import inspect


class BackgroundFactoryTests(unittest.TestCase):
    def test_all_backgrounds_have_vertical_renderer_dimensions(self):
        for name in SCENES:
            with self.subTest(name=name):
                self.assertEqual(render(name).size, (540, 960))

    def test_generation_is_deterministic(self):
        self.assertEqual(render("moonlit-valley").tobytes(), render("moonlit-valley").tobytes())

    def test_generated_art_is_unapproved_until_review(self):
        with tempfile.TemporaryDirectory() as folder:
            manifest = generate(folder)
            self.assertEqual(len(list((Path(folder) / "art").glob("*.png"))), len(SCENES))
            report = inspect(manifest)
            self.assertEqual(report["registered"], len(SCENES))
            self.assertEqual(report["approved"], 0)


if __name__ == "__main__":
    unittest.main()
