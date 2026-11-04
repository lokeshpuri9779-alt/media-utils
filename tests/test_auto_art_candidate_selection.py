"""Review-only automatic artwork selection must emit clean machine JSON."""
import contextlib
import io
import json
import unittest
from unittest.mock import patch
from astra_v2.select_editorial_art_candidate import main


class ArtCandidateSelectionTests(unittest.TestCase):
    def test_empty_inventory_fails_closed(self):
        out, err = io.StringIO(), io.StringIO()
        with patch("astra_v2.select_editorial_art_candidate.load_editorial_stories", return_value=[]), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(main(), 2)
        self.assertEqual(out.getvalue(), "")
        self.assertIn("no_eligible", err.getvalue())

    def test_diagnostics_do_not_corrupt_json(self):
        out, err = io.StringIO(), io.StringIO()
        def loader():
            print("ASTRA_EDITORIAL_INTAKE_AUDIT={}")
            return [{"content_id": "story-z"}, {"content_id": "story-a", "title": "A"}]
        with patch("astra_v2.select_editorial_art_candidate.load_editorial_stories", side_effect=loader), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(main(), 0)
        self.assertEqual(json.loads(out.getvalue())["content_id"], "story-a")
        self.assertIn("ASTRA_EDITORIAL_INTAKE_AUDIT", err.getvalue())


if __name__ == "__main__":
    unittest.main()
