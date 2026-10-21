import unittest
from astra_v2.adaptive_orchestrator import AdaptivePlanner, DecisionDirector


class AdaptiveOrchestratorTests(unittest.TestCase):
    def test_adaptive_replenishment(self):
        planner = AdaptivePlanner()
        low = planner.plan({"daily_demand": 5, "ready_inventory": 3})
        high = planner.plan({"daily_demand": 20, "ready_inventory": 3})
        self.assertGreater(high["replenish"], low["replenish"])

    def test_missing_omniroute_is_not_fabricated(self):
        decision = DecisionDirector.safe_default().evaluate({"daily_demand": 10})
        self.assertFalse(decision.accepted)
        self.assertEqual(decision.opinion["verdict"], "unavailable")

    def test_injected_reviewer(self):
        class Reviewer:
            def review(self, proposal, evidence):
                return {"available": True, "verdict": "approve", "source": "test_double"}
        director = DecisionDirector(AdaptivePlanner(), Reviewer())
        decision = director.evaluate({"daily_demand": 10})
        self.assertTrue(decision.accepted)
        self.assertEqual(decision.opinion["source"], "test_double")


if __name__ == "__main__":
    unittest.main()
