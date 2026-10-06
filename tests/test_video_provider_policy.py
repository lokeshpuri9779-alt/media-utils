import unittest

from video_provider_policy import capability, autonomous_provider_allowed, choose_autonomous_provider


class VideoProviderPolicyTests(unittest.TestCase):
    def test_self_hosted_backends_are_autonomous(self):
        self.assertTrue(autonomous_provider_allowed("ltx-local"))
        self.assertTrue(autonomous_provider_allowed("wan2.2-local"))
        self.assertTrue(autonomous_provider_allowed("remote-open-source-gpu"))

    def test_paid_and_unknown_are_fail_closed(self):
        self.assertFalse(autonomous_provider_allowed("replicate"))
        self.assertFalse(autonomous_provider_allowed("mystery-provider"))
        self.assertEqual(capability("replicate")["cost_class"],"paid")
        self.assertEqual(capability("mystery-provider")["cost_class"],"unknown")

    def test_selection_skips_paid_provider(self):
        self.assertEqual(
            choose_autonomous_provider(["replicate","remote-open-source-gpu"]),
            "remote-open-source-gpu",
        )
        self.assertIsNone(choose_autonomous_provider(["replicate","unknown"]))


if __name__=="__main__":
    unittest.main()
