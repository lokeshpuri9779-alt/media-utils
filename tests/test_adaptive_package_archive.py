from concurrent.futures import ThreadPoolExecutor
from contextlib import chdir
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from astra_v2.adaptive_artifact_store import ArtifactStore
from astra_v2.adaptive_package_archive import PackageArchive, SCHEMA, archive_preload_if_enabled
from astra_v2.adaptive_remote_store import S3ArtifactStore
from test_adaptive_remote_store import MemoryS3


class PackageArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.package = self.root / "preload-package"
        self.package.mkdir()
        self.video = b"test-video-payload"
        (self.package / "video.mp4").write_bytes(self.video)
        self.candidate = {"content_id": "reviewed-short-001", "title": "A New Signal", "description": "Original story",
                          "genre": "mystery", "format": "short", "renderer": "studio-7.3.0", "synthetic": True,
                          "made_for_kids": False, "sha256": hashlib.sha256(self.video).hexdigest(), "media": {"duration": 30}}
        self.write_candidate()
        self.client = MemoryS3()
        self.store = self.worker("producer")
        self.inspections = []
        self.archive = PackageArchive(self.store, inspector=self.inspect)

    def tearDown(self):
        self.temp.cleanup()

    def worker(self, name):
        return S3ArtifactStore(self.client, "astra-test-bucket", self.root / name)

    def inspect(self, path, fmt):
        self.assertEqual(path.read_bytes(), self.video)
        self.inspections.append(fmt)
        return {"duration": 30}

    def write_candidate(self):
        (self.package / "candidate.json").write_text(json.dumps(self.candidate), encoding="utf-8")

    def test_cross_worker_round_trip_all_members_and_dedup(self):
        for name in ("cover.jpg", "cover_wide.jpg"):
            (self.package / name).write_bytes(b"cover bytes " + name.encode())
        receipt = self.archive.put(self.package, provenance={"GITHUB_RUN_ID": "123"})
        self.assertEqual(receipt, self.archive.put(self.package, provenance={"GITHUB_RUN_ID": "123"}))
        self.assertEqual(self.client.writes, 5)  # Four files plus final manifest.
        destination = self.root / "restored"
        result = PackageArchive(self.worker("consumer"), inspector=self.inspect).restore(receipt, destination)
        self.assertFalse(result["publication_triggered"])
        self.assertEqual({p.name for p in destination.iterdir()}, {p.name for p in self.package.iterdir()})
        for path in self.package.iterdir():
            self.assertEqual(path.read_bytes(), (destination / path.name).read_bytes())
        self.assertEqual(self.inspections, ["short", "short", "short"])

    def test_local_backend_accepts_existing_legacy_package(self):
        store = ArtifactStore(self.root / "local")
        archive = PackageArchive(store, inspector=self.inspect)
        receipt = archive.put(self.package)
        result = archive.restore(receipt, self.root / "legacy-restored")
        self.assertEqual(result["content_id"], self.candidate["content_id"])

    def test_rejects_video_mismatch_policy_and_invalid_metadata_before_upload(self):
        cases = [{"sha256": "0" * 64}, {"content_id": "rayvan-procedural-unreviewed"},
                 {"format": "invalid"}, {"renderer": "unknown"}, {"made_for_kids": "false"},
                 {"content_id": "../escape"}, {"synthetic": "true"}, {"production_ready": False}]
        original = dict(self.candidate)
        for changes in cases:
            self.candidate = dict(original, **changes)
            self.write_candidate()
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.archive.put(self.package)
            self.assertEqual(self.client.writes, 0)

    def test_unexpected_files_symlinks_and_media_fail_before_upload(self):
        extra = self.package / "unexpected.txt"
        extra.write_text("x")
        with self.assertRaises(ValueError):
            self.archive.put(self.package)
        extra.unlink()
        cover = self.package / "cover.jpg"
        cover.symlink_to(self.package / "video.mp4")
        with self.assertRaises(ValueError):
            self.archive.put(self.package)
        cover.unlink()
        def reject(*args):
            raise ValueError("media_qa_failed")
        with self.assertRaisesRegex(ValueError, "media_qa_failed"):
            PackageArchive(self.store, inspector=reject).put(self.package)
        self.assertEqual(self.client.writes, 0)

    def test_metadata_and_cover_corruption_never_create_partial_destination(self):
        (self.package / "cover.jpg").write_bytes(b"cover")
        receipt = self.archive.put(self.package)
        manifest = json.loads(self.store.verify(receipt["manifest"]).read_text())
        for name in ("candidate.json", "cover.jpg", "video.mp4"):
            key = (self.store.bucket, self.store._key(manifest["files"][name]["sha256"]))
            original = self.client.objects[key]
            self.client.objects[key] = b"x" * len(original)
            target = self.root / (name + "-restored")
            with self.subTest(name=name), self.assertRaises(ValueError):
                PackageArchive(self.worker(name), inspector=self.inspect).restore(receipt, target)
            self.assertFalse(target.exists())
            self.assertEqual(list(self.root.glob(".astra-restore-*")), [])
            self.client.objects[key] = original

    def test_corrupt_manifest_and_traversal_are_rejected(self):
        receipt = self.archive.put(self.package)
        key = (self.store.bucket, self.store._key(receipt["manifest"]["sha256"]))
        original = self.client.objects[key]
        self.client.objects[key] = b"x" * len(original)
        with self.assertRaises(ValueError):
            PackageArchive(self.worker("fresh"), inspector=self.inspect).restore(receipt, self.root / "bad-manifest")
        self.client.objects[key] = original
        manifest = json.loads(original)
        manifest["files"]["../escape"] = manifest["files"]["video.mp4"]
        malicious = self.root / "manifest.json"
        malicious.write_text(json.dumps(manifest))
        changed = dict(receipt, manifest=self.store.put(malicious))
        with self.assertRaisesRegex(ValueError, "invalid_archive_members"):
            self.archive.restore(changed, self.root / "bad-members")
        self.assertFalse((self.root / "escape").exists())

    def test_restore_rechecks_current_policy_and_media(self):
        receipt = self.archive.put(self.package)
        with patch("astra_v2.adaptive_package_archive.publication_rejection", return_value="policy_changed"):
            with self.assertRaisesRegex(ValueError, "policy_changed"):
                self.archive.restore(receipt, self.root / "rejected-policy")
        def reject(*args):
            raise ValueError("media_changed")
        with self.assertRaisesRegex(ValueError, "media_changed"):
            PackageArchive(self.store, inspector=reject).restore(receipt, self.root / "rejected-media")
        self.assertFalse((self.root / "rejected-policy").exists())
        self.assertFalse((self.root / "rejected-media").exists())

    def test_existing_and_concurrent_restore_never_overwrite(self):
        receipt = self.archive.put(self.package)
        target = self.root / "restore"
        def restore(_):
            try:
                return self.archive.restore(receipt, target)
            except (ValueError, FileExistsError):
                return None
        with ThreadPoolExecutor(max_workers=2) as workers:
            results = list(workers.map(restore, range(2)))
        self.assertEqual(sum(result is not None for result in results), 1)
        marker = target / "marker"
        marker.write_text("keep")
        with self.assertRaises(ValueError):
            self.archive.restore(receipt, target)
        self.assertEqual(marker.read_text(), "keep")

    def test_partial_upload_never_commits_manifest(self):
        original = self.store.put
        calls = []
        def interrupted(path):
            calls.append(Path(path).name)
            if len(calls) == 2:
                raise OSError("connection_interrupted")
            return original(path)
        with patch.object(self.store, "put", side_effect=interrupted):
            with self.assertRaises(OSError):
                self.archive.put(self.package)
        self.assertNotIn("manifest.json", calls)
        self.assertEqual(self.client.writes, 1)
        receipt = self.archive.put(self.package)
        self.assertEqual(self.client.writes, 3)
        self.assertEqual(receipt["schema"], SCHEMA)

    def test_producer_opt_in_and_receipt_outside_package(self):
        with patch.dict(os.environ, {}, clear=True), patch("astra_v2.adaptive_remote_store.store_from_environment") as factory:
            self.assertIsNone(archive_preload_if_enabled(self.package))
            factory.assert_not_called()
        with chdir(self.root), patch.dict(os.environ, {"ASTRA_REMOTE_ARCHIVE": "1"}, clear=True), \
                patch("astra_v2.adaptive_remote_store.store_from_environment", return_value=self.store), \
                patch("astra_v2.adaptive_package_archive.PackageArchive", return_value=self.archive):
            receipt = archive_preload_if_enabled(self.package)
            self.assertEqual(json.loads(Path("preload-archive-receipt.json").read_text()), receipt)
        self.assertEqual({p.name for p in self.package.iterdir()}, {"video.mp4", "candidate.json"})


if __name__ == "__main__":
    unittest.main()
