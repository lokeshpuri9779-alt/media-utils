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
        release = {"assets": [asset], "upload_url": "https://uploads.github.com/test{?name}"}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "video.mp4"
            path.write_bytes(data)
            with patch.object(self.store, "_release", return_value=release):
                with patch.object(self.store, "_request", return_value=data) as req:
                    record = self.store.put(path)
            self.assertEqual(record["sha256"], digest)
            self.assertEqual(record["bytes"], len(data))
            self.assertEqual(req.call_count, 1)

    def test_rejects_corruption(self):
        data = b"original media"
        digest = hashlib.sha256(data).hexdigest()
        asset = {"id": 1, "name": "sha256-" + digest, "size": len(data)}
        with patch.object(self.store, "_release", return_value={"assets": [asset]}):
            with patch.object(self.store, "_request", return_value=b"wrong payload!!"):
                with self.assertRaisesRegex(ValueError, "corrupted"):
                    self.store.verify_bytes({"sha256": digest, "bytes": len(data), "uri": "github-release://example/repo/astra-media-v1/sha256-" + digest})

    def test_missing_asset_fails_closed(self):
        with patch.object(self.store, "_release", return_value={"assets": []}):
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

    def test_invalid_tag_and_digest(self):
        with self.assertRaises(ValueError):
            GitHubReleaseStore("example/repo", token="x", tag="general")
        with self.assertRaises(ValueError):
            self.store._asset_name("../bad")


if __name__ == "__main__":
    unittest.main()
