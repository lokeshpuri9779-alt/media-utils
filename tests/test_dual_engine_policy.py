import unittest
from experimental.dual_engine_policy import ENGINE_MAIN,ENGINE_CINEMATIC,routing_policy,select_engine

class DualEnginePolicyTests(unittest.TestCase):
    def test_both_engines_always_listed(self):
        p=routing_policy()
        self.assertEqual(set(p["available_engines"]),{ENGINE_MAIN,ENGINE_CINEMATIC})
        self.assertIsNone(p["retire_engine"])
        self.assertFalse(p["auto_replace_main"])
    def test_main_remains_default(self):
        self.assertEqual(select_engine(),ENGINE_MAIN)
        self.assertEqual(select_engine(ENGINE_CINEMATIC),ENGINE_CINEMATIC)
    def test_unknown_engine_rejected(self):
        with self.assertRaises(ValueError):select_engine("replacement")
if __name__=="__main__":unittest.main()
