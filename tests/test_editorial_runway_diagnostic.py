import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from astra_v2.editorial_runway_diagnostic import editorial_runway


class EditorialRunwayTests(unittest.TestCase):
    def test_eligible_and_blocked_are_reported_without_approval(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            paths = [root / name for name in ("stories.json", "reviews.json", "state.json", "history.json")]
            paths[0].write_text(json.dumps({"stories": [{"content_id": "a"}, {"content_id": "b"}]}))
            paths[1].write_text(json.dumps({"reviews": []}))
            paths[2].write_text("{}")
            paths[3].write_text("{}")
            audit = {"results": [
                {"content_id": "a", "approved": True, "issues": []},
                {"content_id": "b", "approved": False, "issues": ["already_published"]}],
                "approved_count": 1}
            with patch("astra_v2.editorial_runway_diagnostic.load_history", return_value=[]), patch(
                "astra_v2.editorial_runway_diagnostic.validate_manifest", return_value=audit
            ):
                result = editorial_runway(*paths)
            self.assertEqual(result["eligible_ids"], ["a"])
            self.assertEqual(result["reasons"], {"already_published": 1})
            self.assertFalse(result["publication_triggered"])
            self.assertFalse(result["automatic_approval"])

    def test_missing_history_fails_closed(self):
        with tempfile.TemporaryDirectory() as root:
            paths = [Path(root) / name for name in ("stories", "reviews", "publisher", "history")]
            for path in paths[:-1]:
                path.write_text("{}")
            with self.assertRaises(FileNotFoundError):
                editorial_runway(*paths)


if __name__ == "__main__":
    unittest.main()
