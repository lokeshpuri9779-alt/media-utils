import tempfile
import unittest
from pathlib import Path

from astra_v2.adaptive_artifact_store import ArtifactStore
from astra_v2.reviewed_art_receipt_index import lookup, publish_index
from astra_v2.remote_reviewed_art import SCHEMA


class ArtReceiptIndexTests(unittest.TestCase):
    def test_independent_cache_index_lookup(self):
        with tempfile.TemporaryDirectory() as temp:
            store = ArtifactStore(Path(temp) / "objects")
            bundle = Path(temp) / "bundle"
            bundle.write_bytes(b"example immutable identity")
            receipt = {"schema": SCHEMA, "bundle": store.put(bundle),
                       "publication_triggered": False}
            index = publish_index({"story-001": receipt}, store)
            self.assertEqual(lookup(index, "story-001", store), receipt)
            self.assertIsNone(lookup(index, "story-002", store))
            self.assertFalse(index["publication_triggered"])

    def test_invalid_approval_or_content_id_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            store = ArtifactStore(Path(temp) / "objects")
            with self.assertRaises(ValueError):
                publish_index({"../unsafe": {}}, store)
            with self.assertRaises(ValueError):
                publish_index({"story": {"schema": SCHEMA, "publication_triggered": True}}, store)


if __name__ == "__main__":
    unittest.main()
