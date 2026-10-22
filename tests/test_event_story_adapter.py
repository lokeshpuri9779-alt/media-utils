import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from astra_v2.event_story_adapter import make_story_handler, run_story_event


class EventStoryAdapterTests(unittest.TestCase):
    def test_identity_mismatch_does_not_generate(self):
        with tempfile.TemporaryDirectory() as root:
            handler=make_story_handler("batch-1",Path(root)/"out",
                                       start_index=0,worker_index=0)
            with self.assertRaises(ValueError):
                handler("other","other:story")

    def test_existing_output_not_overwritten(self):
        with tempfile.TemporaryDirectory() as root:
            handler=make_story_handler("batch-1",root,start_index=0,worker_index=0)
            with self.assertRaises(FileExistsError):
                handler("batch-1","batch-1:story")

    @patch("astra_v2.event_story_adapter.dispatch_batch")
    def test_uses_existing_dispatcher(self, dispatcher):
        ledger=Mock()
        ledger.states.return_value={}
        run_story_event(ledger,"batch-1","/tmp/nonexistent-story-worker",
                        start_index=0)
        self.assertEqual(dispatcher.call_args.args[1],{"batch-1":{}})
        self.assertIn("story",dispatcher.call_args.args[2])


if __name__=="__main__":
    unittest.main()
