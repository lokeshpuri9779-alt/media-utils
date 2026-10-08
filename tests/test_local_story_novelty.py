import unittest
from astra_v2.omniroute_local import catalog

class LocalStoryNoveltyTests(unittest.TestCase):
    def test_previously_used_setting_is_excluded(self):
        stories = catalog(excluded_titles=["Mara and A Message From Tomorrow at the Abandoned Observatory"])
        self.assertTrue(stories)
        self.assertTrue(all("abandoned observatory" not in story["title"].lower() for story in stories))
    def test_previously_used_discovery_is_excluded(self):
        stories = catalog(excluded_titles=["Mara and A Machine That Remembers Rain at the Silent Orbital Station"])
        self.assertTrue(stories)
        self.assertTrue(all("machine that remembers rain" not in story["title"].lower() for story in stories))
    def test_empty_catalog_when_every_setting_used(self):
        stories = catalog(excluded_titles=[setting[0] for setting in __import__("astra_v2.omniroute_local", fromlist=["SETTINGS"]).SETTINGS])
        self.assertEqual(stories, [])

if __name__ == "__main__":
    unittest.main()
