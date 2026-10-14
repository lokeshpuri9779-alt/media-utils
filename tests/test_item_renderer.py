"""Specific item rendering coverage."""
import unittest
from experimental.item_renderer import SUPPORTED,render_item

class ItemRendererTests(unittest.TestCase):
    def test_supported_items_are_nonuniform(self):
        for kind in SUPPORTED:
            image=render_item(kind,"products",size=64)
            self.assertEqual(image.size,(64,64))
            self.assertGreater(len(image.getcolors(4096) or []),1)
    def test_repeatable(self):
        self.assertEqual(render_item("apple","food").tobytes(),
                         render_item("apple","food").tobytes())
    def test_fallback(self):
        image=render_item("unknown","flora",size=64)
        self.assertEqual(image.size,(64,64))
    def test_minimum_size(self):
        with self.assertRaises(ValueError):
            render_item("sun","nature",size=8)

if __name__=="__main__":
    unittest.main()
