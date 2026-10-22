import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from astra_v2.event_story_stripes import combine_completed_stripes
from astra_v2.story_batch_checkpoint import checkpoint_record


class StripeCombineTests(unittest.TestCase):
    @patch("astra_v2.event_story_stripes.read_worker_payload")
    def test_combines_validated_stripes_as_unreviewed(self, read):
        def payload(*args, **kwargs):
            i=kwargs["worker_index"]
            return {"checkpoint":checkpoint_record(
                f"batch-stripe-{i}-worker-{i}", "generated", [f"id-{i}"], complete=True),
                "stories":[{"content_id":f"id-{i}","production_ready":False}]}
        read.side_effect=payload
        result=combine_completed_stripes("batch","/tmp/unused",workers=2,total=2)
        self.assertEqual(result["count"],2)
        self.assertEqual(result["approved_count"],0)
        self.assertFalse(result["publication_triggered"])

    @patch("astra_v2.event_story_stripes.read_worker_payload")
    def test_rejects_global_duplicate(self, read):
        def payload(*args, **kwargs):
            i=kwargs["worker_index"]
            return {"checkpoint":checkpoint_record(
                f"batch-stripe-{i}-worker-{i}","generated",["duplicate"],complete=True),
                "stories":[{"content_id":"duplicate","production_ready":False}]}
        read.side_effect=payload
        with self.assertRaises(ValueError):
            combine_completed_stripes("batch","/tmp/unused",workers=2,total=2)


if __name__=="__main__":
    unittest.main()
