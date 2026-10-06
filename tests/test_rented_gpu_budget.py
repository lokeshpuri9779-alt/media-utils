import os
import unittest
from unittest.mock import patch

from rented_gpu_budget import rented_compute_policy, assert_rented_compute_allowed


class RentedGPUBudgetTests(unittest.TestCase):
    def test_disabled_by_default(self):
        with patch.dict(os.environ,{},clear=True):
            self.assertFalse(rented_compute_policy()["approved"])

    def test_requires_nonzero_budget(self):
        with patch.dict(os.environ,{"ASTRA_ALLOW_RENTED_GPU":"1"},clear=True):
            self.assertFalse(rented_compute_policy()["approved"])

    def test_estimate_must_fit_budget(self):
        env={
            "ASTRA_ALLOW_RENTED_GPU":"1",
            "ASTRA_GPU_BUDGET_USD":"1.00",
            "ASTRA_GPU_RENTAL_PROVIDER":"runpod",
        }
        with patch.dict(os.environ,env,clear=True):
            report=assert_rented_compute_allowed(.75)
            self.assertEqual(report["remaining_usd"],.25)
            with self.assertRaises(RuntimeError):
                assert_rented_compute_allowed(1.25)


if __name__=="__main__":
    unittest.main()
