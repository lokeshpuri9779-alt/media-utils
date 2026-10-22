import unittest
from unittest.mock import Mock, patch
from astra_v2.event_story_stripes import run_parallel_story_stripes


class StoryStripeTests(unittest.TestCase):
    @patch("astra_v2.event_story_stripes.dispatch_batch")
    def test_parallel_dispatches_distinct_ids(self, dispatch):
        dispatch.return_value=()
        ledger=Mock()
        ledger.states.return_value={}
        run_parallel_story_stripes(ledger,batch_id="batch",output_root="/tmp/astra",
                                   start_index=0,workers=3,total=9,max_workers=2)
        self.assertEqual(ledger.states.call_count,3)
        ids={call.args[0] for call in ledger.states.call_args_list}
        self.assertEqual(ids,{"batch-stripe-0","batch-stripe-1","batch-stripe-2"})

    def test_rejects_invalid_worker_count(self):
        with self.assertRaises(ValueError):
            run_parallel_story_stripes(Mock(),batch_id="batch",output_root="/tmp/astra",
                                       start_index=0,workers=0)


if __name__=="__main__":
    unittest.main()
