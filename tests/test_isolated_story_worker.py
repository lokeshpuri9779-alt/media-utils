import tempfile
import unittest
from pathlib import Path

from astra_v2.isolated_story_worker import generate_worker, worker_indices
from astra_v2.parallel_story_workers import combine_workers, read_worker_payload


class IsolatedStoryWorkerTests(unittest.TestCase):
    def test_all_eight_workers_have_disjoint_indices(self):
        stripes = [worker_indices(1000, i) for i in range(8)]
        indices = [index for stripe in stripes for index in stripe]
        self.assertEqual(len(indices), 256)
        self.assertEqual(len(set(indices)), 256)
        self.assertEqual(set(indices), set(range(1000, 1256)))

    def test_generated_workers_round_trip_into_coordinator(self):
        with tempfile.TemporaryDirectory() as root:
            workers = []
            for i in range(8):
                directory = Path(root) / str(i)
                generate_worker("batch", i, 1000, directory)
                workers.append(read_worker_payload(
                    directory / "checkpoint.json", directory / "stories.json",
                    batch_id="batch", worker_index=i))
            merged = combine_workers("batch", workers)
            self.assertEqual(merged["count"], 256)
            self.assertEqual(merged["approved_count"], 0)
            self.assertFalse(merged["publication_triggered"])

    def test_reusing_output_fails_closed(self):
        with tempfile.TemporaryDirectory() as root:
            generate_worker("batch", 0, 1000, root)
            with self.assertRaises(FileExistsError):
                generate_worker("batch", 0, 1000, root)

    def test_invalid_worker_rejected(self):
        with self.assertRaises(ValueError):
            worker_indices(0, 8)


if __name__ == "__main__":
    unittest.main()
