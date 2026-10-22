"""Regression: bridge CLI must preserve existing manifest and validate output first."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from astra_v2.reviewed_art_bridge import main


class BridgeCliSafetyTests(unittest.TestCase):
    def test_existing_assets_are_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "art" / "manifest.json"
            manifest.parent.mkdir()
            original = {"assets": [{"id": "licensed-original", "status": "approved"}]}
            manifest.write_text(json.dumps(original))
            args = ["bridge", "--queue", str(root / "queue.json"),
                    "--images", str(root / "images.json"),
                    "--decisions", str(root / "decisions.json"),
                    "--asset-root", str(root), "--output-root", str(root),
                    "--output", str(manifest)]
            approved = {"id": "reviewed-new-001", "story_content_id": "story",
                        "scene_id": "001", "status": "approved"}
            with patch("sys.argv", args), patch(
                    "astra_v2.reviewed_art_preload.build_approved_manifest",
                    return_value={"assets": [approved]}):
                main()
            result = json.loads(manifest.read_text())
            self.assertEqual(result["assets"], original["assets"] + [approved])

    def test_invalid_output_does_not_stage_artwork(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = ["bridge", "--queue", "missing", "--images", "missing",
                    "--decisions", "missing", "--asset-root", str(root),
                    "--output-root", str(root), "--output", str(root / "wrong.json")]
            with patch("sys.argv", args), patch(
                    "astra_v2.reviewed_art_preload.prepare_artwork") as stage:
                with self.assertRaisesRegex(ValueError, "Renderer manifest"):
                    main()
                stage.assert_not_called()


if __name__ == "__main__":
    unittest.main()
