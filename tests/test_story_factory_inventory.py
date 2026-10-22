import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from astra_v2.story_factory_inventory import count_ready


class ReadyInventoryTests(unittest.TestCase):
    def test_missing_inventory_never_blocks_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(count_ready(Path(tmp) / "missing.json", tmp), 0)

    def test_only_hash_verified_unpublished_mp4_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            video = root / "ready.mp4"
            video.write_bytes(b"synthetic fixture only")
            digest = hashlib.sha256(video.read_bytes()).hexdigest()
            rows = [
                {"path": "ready.mp4", "sha256": digest, "status": "production_ready", "published": False},
                {"path": "ready.mp4", "sha256": digest, "status": "production_ready", "published": False},
                {"path": "ready.mp4", "sha256": digest, "status": "production_ready", "published": True},
                {"path": "../outside.mp4", "sha256": digest, "status": "production_ready", "published": False},
                {"path": "ready.mp4", "sha256": "0" * 64, "status": "production_ready", "published": False},
                {"path": "missing.mp4", "sha256": digest, "status": "production_ready", "published": False},
            ]
            manifest = root / "inventory.json"
            manifest.write_text(json.dumps({"schema_version": 1, "videos": rows}))
            self.assertEqual(count_ready(manifest, root), 1)

    def test_untrusted_inventory_fails_open_for_replenishment(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "inventory.json"
            for value in ("invalid json", "[]", '{"schema_version": 2, "videos": []}'):
                manifest.write_text(value)
                self.assertEqual(count_ready(manifest, root), 0)


if __name__ == "__main__":
    unittest.main()
