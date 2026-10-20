import unittest

from astra_v2.story_batch_checkpoint import checkpoint_record
from astra_v2.parallel_story_workers import combine_workers, worker_allocation


def workers(batch="batch"):
    result = []
    cursor = 0
    for i, size in enumerate(worker_allocation()):
        stories = [{"content_id": f"id-{cursor+j}", "production_ready": False}
                   for j in range(size)]
        cursor += size
        result.append({"checkpoint": checkpoint_record(
            f"{batch}-worker-{i}", "generated",
            [x["content_id"] for x in stories], complete=True),
            "stories": stories})
    return result


class ParallelStoryWorkersTests(unittest.TestCase):
    def test_256_stories_eight_workers(self):
        self.assertEqual(worker_allocation(), [32] * 8)
        result = combine_workers("batch", workers())
        self.assertEqual(result["count"], 256)
        self.assertEqual(result["approved_count"], 0)
        self.assertFalse(result["publication_triggered"])

    def test_missing_worker_fails_closed(self):
        with self.assertRaises(ValueError):
            combine_workers("batch", workers()[:-1])

    def test_duplicate_across_workers_fails_closed(self):
        data = workers()
        data[1]["stories"][0]["content_id"] = data[0]["stories"][0]["content_id"]
        data[1]["checkpoint"]["story_ids"][0] = data[0]["stories"][0]["content_id"]
        with self.assertRaises(ValueError):
            combine_workers("batch", data)

    def test_unreviewed_story_cannot_be_marked_ready(self):
        data = workers()
        data[0]["stories"][0]["production_ready"] = True
        with self.assertRaises(ValueError):
            combine_workers("batch", data)

    def test_checkpoint_tampering_rejected(self):
        data = workers()
        data[0]["checkpoint"]["approved_count"] = 1
        with self.assertRaises(ValueError):
            combine_workers("batch", data)

    def test_story_order_mismatch_rejected(self):
        data = workers()
        data[0]["stories"].reverse()
        with self.assertRaises(ValueError):
            combine_workers("batch", data)


if __name__ == "__main__":
    unittest.main()
