import unittest
from quality_lab import director_input_from_render

class GenreRoutingTests(unittest.TestCase):
    def test_genre_routing(self):
        render = {"duration": 57, "scenes": [{"duration": 57, "speech": "Narration"}],
                  "creative_quality": {"score": 90}, "audio": {"peak_dbfs": -3}}
        expected = {"fiction": "fiction", "microfiction": "fiction",
                    "suspense": "suspense", "thriller": "suspense",
                    "education": "education"}
        for incoming, mapped in expected.items():
            with self.subTest(incoming=incoming):
                result = director_input_from_render({"genre": incoming, "hook": "A mystery"}, render)
                self.assertEqual(result["genre"], mapped)

if __name__ == "__main__":
    unittest.main()
