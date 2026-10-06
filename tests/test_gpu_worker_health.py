import unittest
from unittest.mock import patch

import gpu_worker_health as gwh


class GPUWorkerHealthTests(unittest.TestCase):
    def test_no_gpu_reports_not_ready(self):
        with patch("gpu_worker_health.gpu_info", return_value={"available":False,"reason":"none"}),              patch("gpu_worker_health.provider_status", return_value={"ready":False}):
            h=gwh.worker_health()
            self.assertFalse(h["ltx_candidate"])
            self.assertFalse(h["wan22_ti2v5b_candidate"])
            self.assertTrue(h["paid_fallback_required"])

    def test_vram_thresholds(self):
        with patch("gpu_worker_health.gpu_info", return_value={
            "available":True,"gpus":[{"name":"GPU","memory_mb":24576,"driver":"x"}]}),              patch("gpu_worker_health.provider_status", return_value={"ready":True}):
            h=gwh.worker_health()
            self.assertTrue(h["ltx_candidate"])
            self.assertTrue(h["wan22_ti2v5b_candidate"])
            self.assertFalse(h["paid_fallback_required"])


if __name__=="__main__":
    unittest.main()
