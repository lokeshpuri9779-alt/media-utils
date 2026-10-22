import unittest
from astra_v2.event_recovery_policy import recovery_decision, adaptive_worker_limit


class RecoveryPolicyTests(unittest.TestCase):
    def test_publishing_never_automatically_retries(self):
        self.assertEqual(recovery_decision("publish","rate_limited",1,
                         no_external_effect_verified=True).action,"reconcile")

    def test_ambiguous_effect_requires_reconciliation(self):
        self.assertEqual(recovery_decision("render","provider_unavailable",1).action,"reconcile")

    def test_verified_transient_backoff(self):
        first=recovery_decision("story","rate_limited",1,no_external_effect_verified=True)
        second=recovery_decision("story","rate_limited",2,no_external_effect_verified=True)
        self.assertEqual((first.delay_seconds,second.delay_seconds),(15,30))
        self.assertEqual(second.action,"retry_after_reconciliation")

    def test_exhausted_and_permanent_errors_quarantine(self):
        self.assertEqual(recovery_decision("assets","rate_limited",3,
                         no_external_effect_verified=True).action,"quarantine")
        self.assertEqual(recovery_decision("assets","invalid_output",1,
                         no_external_effect_verified=True).action,"quarantine")

    def test_adaptive_capacity(self):
        self.assertEqual(adaptive_worker_limit(ready_tasks=20,available_slots=6,
                         provider_remaining=3),3)
        self.assertEqual(adaptive_worker_limit(ready_tasks=10,available_slots=10,
                         provider_remaining=0),0)


if __name__=="__main__":
    unittest.main()
