import unittest
from video_provider_policy import capability, autonomous_provider_allowed

class ZeroGPUBackendTests(unittest.TestCase):
    def test_zerogpu_policy_is_free_quota_but_inactive(self):
        cap=capability("hf-zerogpu")
        self.assertEqual(cap["cost_class"],"free-quota")
        self.assertTrue(autonomous_provider_allowed("hf-zerogpu"))

if __name__=="__main__":
    unittest.main()
