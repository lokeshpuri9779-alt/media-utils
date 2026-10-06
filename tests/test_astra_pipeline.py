import unittest

from astra_pipeline import MASTER_PIPELINE, NON_BYPASSABLE, architecture_contract


class AstraPipelineTests(unittest.TestCase):
    def test_master_loop_order_is_locked(self):
        self.assertLess(MASTER_PIPELINE.index("creative_engine"), MASTER_PIPELINE.index("ffmpeg_composition"))
        self.assertLess(MASTER_PIPELINE.index("astra_quality_director"), MASTER_PIPELINE.index("publish"))
        self.assertLess(MASTER_PIPELINE.index("analytics"), MASTER_PIPELINE.index("next_generation"))

    def test_quality_and_creative_gates_are_non_bypassable(self):
        contract=architecture_contract()
        self.assertEqual(set(contract["non_bypassable"]), NON_BYPASSABLE)
        self.assertIn("pass_gate", NON_BYPASSABLE)


if __name__=="__main__":
    unittest.main()
