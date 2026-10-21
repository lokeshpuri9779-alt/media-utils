import unittest
from astra_v2.story_factory_premises import NEW_MECHANISMS
from astra_v2.story_expansion_2000 import MECHANISMS


class NewCausalPremisesTests(unittest.TestCase):
    def test_unique_keys_and_complete_causal_arcs(self):
        all_mechanisms = list(MECHANISMS) + list(NEW_MECHANISMS)
        keys = [item[0] for item in all_mechanisms]
        self.assertEqual(len(keys), len(set(keys)))
        for item in all_mechanisms:
            self.assertEqual(len(item), 6)
            self.assertTrue(all(isinstance(value, str) and len(value.strip()) >= 8 for value in item[1:]))

    def test_eight_new_mechanisms_present(self):
        keys = {item[0] for item in NEW_MECHANISMS}
        self.assertTrue({"archive-ink", "tidal-pool", "seed-clock", "glass-hum",
                         "lantern-code", "floating-bridge", "music-map", "ice-lens"} <= keys)


if __name__ == "__main__":
    unittest.main()
