import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from astra_v2.github_release_store import GitHubReleaseStore


class GitHubReleaseStoreTests(unittest.TestCase):
    def setUp(self):
        self.store = GitHubReleaseStore("example/repo", token="test-token")

    def test_put_reuses_and_verifies_existing_asset(self):
        data = b"original media"
        digest = hashlib.sha256(data).hexdigest()
        asset = {"id": 123, "name": "sha256-" + digest, "size": len(data)}
        release = {"id": 7, "assets": [asset], "upload_url": "https://uploads.github.com/test{?name}"}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "video.mp4"
            path.write_bytes(data)
            with patch.object(self.store, "_release", return_value=release):
                with patch.object(self.store, "_request", side_effect=lambda method, url, *args, **kwargs: [asset] if "/assets?per_page=" in url else data) as req:
                    record = self.store.put(path)
            self.assertEqual(record["sha256"], digest)
            self.assertEqual(record["bytes"], len(data))
            self.assertEqual(req.call_count, 3)

    def test_rejects_corruption(self):
        data = b"original media"
        digest = hashlib.sha256(data).hexdigest()
        asset = {"id": 1, "name": "sha256-" + digest, "size": len(data)}
        with patch.object(self.store, "_release", return_value={"id": 7, "assets": [asset]}):
            with patch.object(self.store, "_request", side_effect=lambda method, url, *args, **kwargs: [asset] if "/assets?per_page=" in url else b"wrong payload!!"):
                with self.assertRaisesRegex(ValueError, "corrupted"):
                    self.store.verify_bytes({"sha256": digest, "bytes": len(data), "uri": "github-release://example/repo/astra-media-v1/sha256-" + digest})

    def test_missing_asset_fails_closed(self):
        with patch.object(self.store, "_release", return_value={"id": 7, "assets": []}):
            with self.assertRaises(ValueError):
                self.store.verify_bytes({"sha256": "a" * 64, "bytes": 5, "uri": "github-release://example/repo/astra-media-v1/sha256-" + "a" * 64})

    def test_rejects_cross_repository_record_before_download(self):
        digest = "a" * 64
        with patch.object(self.store, "_release") as remote:
            with self.assertRaisesRegex(ValueError, "origin_mismatch"):
                self.store.verify_bytes({
                    "sha256": digest, "bytes": 5,
                    "uri": "github-release://other/repo/astra-media-v1/sha256-" + digest,
                })
            remote.assert_not_called()

    def test_find_asset_on_second_page(self):
        name = "sha256-" + "a" * 64
        target = {"id": 88, "name": name, "size": 4}
        calls = []
        def fetch(method, url, *args, **kwargs):
            calls.append(url)
            return [{"name": "other-" + str(i)} for i in range(100)] if "page=1" in url else [target]
        with patch.object(self.store, "_request", side_effect=fetch):
            self.assertEqual(self.store._find({"id": 7}, name), target)
        self.assertEqual(len(calls), 2)

    def test_find_fails_closed_at_page_limit(self):
        with patch.object(self.store, "_request", return_value=[{"name": "other"}] * 100):
            with self.assertRaisesRegex(RuntimeError, "page_limit"):
                self.store._find({"id": 7}, "sha256-" + "a" * 64)

    def test_incomplete_inventory_fails_closed(self):
        name = "sha256-" + "a" * 64
        with patch.object(self.store, "_request", return_value=[]):
            with self.assertRaisesRegex(RuntimeError, "incomplete_release_asset_inventory"):
                self.store._find({"id": 7, "assets_count": 1}, name)

    def test_complete_inventory_with_count(self):
        name = "sha256-" + "a" * 64
        asset = {"id": 42, "name": name, "size": 4}
        with patch.object(self.store, "_request", return_value=[asset]):
            self.assertEqual(self.store._find({"id": 7, "assets_count": 1}, name), asset)

    def test_invalid_tag_and_digest(self):
        with self.assertRaises(ValueError):
            GitHubReleaseStore("example/repo", token="x", tag="general")
        with self.assertRaises(ValueError):
            self.store._asset_name("../bad")


if __name__ == "__main__":
    unittest.main()
