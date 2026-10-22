import unittest
from unittest.mock import Mock
from astra_v2.event_parallel_dispatch import dispatch_batch


class DispatchTests(unittest.TestCase):
    def test_parallel_story_worker(self):
        ledger=Mock()
        ledger.claim.return_value={"lease_token":"0"*32}
        outcome=dispatch_batch(ledger, {"sample":{}},
                               {"story":lambda cid,key:"s3://bucket/story"},
                               max_workers=2)
        self.assertEqual(outcome[0].status,"succeeded")
        ledger.finish.assert_called_once()

    def test_protected_handlers_rejected(self):
        with self.assertRaises(ValueError):
            dispatch_batch(Mock(),{},{"publish":lambda *_:"unsafe"})

    def test_failed_worker_quarantined(self):
        ledger=Mock()
        ledger.claim.return_value={"lease_token":"0"*32}
        def fail(*_):
            raise RuntimeError("failed")
        outcome=dispatch_batch(ledger,{"sample":{}},{"story":fail})
        self.assertEqual(outcome[0].status,"quarantined")
        self.assertEqual(ledger.finish.call_args.kwargs["status"],"quarantined")


if __name__=="__main__":
    unittest.main()
