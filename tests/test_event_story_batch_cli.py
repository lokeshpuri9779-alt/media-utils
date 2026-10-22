import unittest
from unittest.mock import patch, Mock
from astra_v2.event_story_batch_cli import run_batch


class StoryBatchCliTests(unittest.TestCase):
    def test_requires_database_url(self):
        with self.assertRaises(ValueError):
            run_batch(database_url="",batch_id="batch",output_root="/tmp/out",start_index=0)

    def test_rejects_invalid_start_index(self):
        with self.assertRaises(ValueError):
            run_batch(database_url="postgres://example",batch_id="batch",
                      output_root="/tmp/out",start_index=-1)

    def test_rejects_unsafe_batch_id(self):
        with self.assertRaises(ValueError):
            run_batch(database_url="postgres://example",batch_id="../escape",
                      output_root="/tmp/out",start_index=0)


if __name__ == "__main__":
    unittest.main()
