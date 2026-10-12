"""Regression tests for deterministic, shot-specific studio backgrounds."""
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image
import studio_renderer as studio


class BackgroundVariationTests(unittest.TestCase):
    def test_same_variant_is_reproducible(self):
        a = studio.background("fiction", 0)
        b = studio.background("fiction", 0)
        self.assertEqual(a.getpixel((220, 600)), b.getpixel((220, 600)))

    def test_different_variants_change_lighting(self):
        a = studio.background("fiction", 0)
        b = studio.background("fiction", 3)
        self.assertNotEqual(a.getpixel((220, 600)), b.getpixel((220, 600)))

    def test_variant_wraps_safely(self):
        self.assertEqual(
            studio.background("fiction", 1).getpixel((700, 800)),
            studio.background("fiction", 7).getpixel((700, 800)),
        )


if __name__ == "__main__":
    unittest.main()
