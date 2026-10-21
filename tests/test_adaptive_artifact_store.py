import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from astra_v2.adaptive_artifact_store import ArtifactStore


class ArtifactStoreTests(unittest.TestCase):
    def test_content_addressed_and_corruption(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "video.mp4"
            source.write_bytes(b"pre-rendered-video")
            store = ArtifactStore(base / "objects")
            a = store.put(source)
            b = store.put(source)
            self.assertEqual(a, b)
            stored = store.verify(a)
            stored.write_bytes(b"corrupt")
            with self.assertRaises(ValueError):
                store.verify(a)
            with self.assertRaises(ValueError):
                store.put(source)

    def test_rejects_nonfile(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                ArtifactStore(Path(directory) / "objects").put(Path(directory) / "missing")

    def test_relative_root_and_size_binding(self):
        with tempfile.TemporaryDirectory(dir=".") as directory:
            source = Path(directory) / "source"
            source.write_bytes(b"video")
            store = ArtifactStore(Path(directory) / "relative")
            record = store.put(source)
            self.assertTrue(record["uri"].startswith("file:///"))
            for size in (True, -1, 6, None):
                with self.subTest(size=size), self.assertRaises(ValueError):
                    store.verify(dict(record, bytes=size))

    def test_concurrent_puts_are_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source"
            source.write_bytes(b"same video" * 1000)
            store = ArtifactStore(Path(directory) / "objects")
            with ThreadPoolExecutor(max_workers=8) as workers:
                records = list(workers.map(lambda _: store.put(source), range(16)))
            self.assertTrue(all(record == records[0] for record in records))
            self.assertEqual(store.verify(records[0]).read_bytes(), source.read_bytes())
            self.assertEqual(list(store.root.rglob(".upload-*")), [])

    def test_missing_stored_file_and_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source"
            source.write_bytes(b"video")
            store = ArtifactStore(Path(directory) / "objects")
            record = store.put(source)
            target = store.verify(record)
            target.unlink()
            with self.assertRaises(ValueError):
                store.verify(record)
            target.symlink_to(source)
            with self.assertRaises(ValueError):
                store.verify(record)
            with self.assertRaises(ValueError):
                store.put(source)

    def test_oversize_and_copy_mutation_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source"
            source.write_bytes(b"video")
            store = ArtifactStore(Path(directory) / "objects", max_bytes=4)
            with self.assertRaises(ValueError):
                store.put(source)
            store = ArtifactStore(Path(directory) / "objects")
            with patch.object(store, "digest", side_effect=["a" * 64, "b" * 64]):
                with self.assertRaisesRegex(ValueError, "artifact_changed_during_copy"):
                    store.put(source)
            self.assertEqual(list(store.root.rglob(".upload-*")), [])


if __name__ == "__main__":
    unittest.main()
