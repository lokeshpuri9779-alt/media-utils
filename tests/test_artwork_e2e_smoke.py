import unittest
from astra.artwork_e2e_smoke import smoke


class EndToEndArtworkSmokeTest(unittest.TestCase):
    def test_archive_restore_render_without_production_approval(self):
        result = smoke()
        self.assertEqual(result["generated"], 12)
        self.assertEqual(result["restored"], 12)
        self.assertTrue(result["rendered_frame"])
        self.assertEqual(result["production_approved"], 0)


if __name__ == "__main__":
    unittest.main()
