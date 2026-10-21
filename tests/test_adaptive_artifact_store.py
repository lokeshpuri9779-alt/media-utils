import tempfile
import unittest
from pathlib import Path
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


if __name__ == "__main__":
    unittest.main()
