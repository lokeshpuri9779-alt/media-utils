import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from astra_v2.story_factory_inventory import count_ready, count_trusted_preloads


class ReadyInventoryTests(unittest.TestCase):
    def test_trusted_remote_preloads_exclude_published_pending_reserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "state.json"
            state.write_text(json.dumps({"published": {"old": {}}, "reserved": {"held": {}},
                                         "pending": {"slot": {"content_id": "inflight"}}}))
            with patch.dict("os.environ", {"GH_TOKEN": "offline", "GITHUB_REPOSITORY": "owner/repo"}):
                with patch("astra_v2.preload_queue.package_integrity_snapshot", return_value={"integrity_passed": 4}) as snapshot:
                    self.assertEqual(count_trusted_preloads(state, 7), 4)
            args, kwargs = snapshot.call_args
            self.assertEqual(kwargs["format_filter"], "short")
            self.assertEqual(kwargs["max_packages"], 14)
            self.assertTrue({"old", "held", "inflight"}.issubset(kwargs["excluded_ids"]))

    def test_invalid_publisher_state_never_suppresses_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "state.json"
            state.write_text('{"published": [], "pending": {}, "reserved": {}}')
            with patch.dict("os.environ", {"GH_TOKEN": "offline", "GITHUB_REPOSITORY": "owner/repo"}):
                with patch("astra_v2.preload_queue.package_integrity_snapshot") as snapshot:
                    self.assertEqual(count_trusted_preloads(state, 7), 0)
                    snapshot.assert_not_called()

    def test_remote_failure_cannot_suppress_replenishment(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "state.json"
            state.write_text(json.dumps({"published": {}, "pending": {}, "reserved": {}}))
            with patch.dict("os.environ", {"GH_TOKEN": "offline", "GITHUB_REPOSITORY": "owner/repo"}):
                with patch("astra_v2.preload_queue.package_integrity_snapshot", side_effect=OSError("offline")):
                    self.assertEqual(count_trusted_preloads(state, 7), 0)

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
