import unittest
from integrations.experimental_engine_registry import ENGINES, eligible_for_production, summarize

class ExperimentalEngineTests(unittest.TestCase):
    def test_unverified_engine_never_production(self):
        for name in ENGINES:
            self.assertFalse(eligible_for_production(name, {'success':True,'quality_pass':True}))
    def test_unknown_engine_rejected(self):
        with self.assertRaises(ValueError): eligible_for_production('unlisted')
    def test_report_does_not_imply_promotion(self):
        self.assertFalse(summarize('blender_cpu',{'success':True})['production_eligible'])

if __name__=='__main__': unittest.main()
