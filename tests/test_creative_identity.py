import unittest

from creative_identity import fingerprint_from_scenes, identity_gate, similarity


class CreativeIdentityTests(unittest.TestCase):
    def sample(self, fmt="cinematic_mini_doc", style="mixed-media"):
        return fingerprint_from_scenes([
            {
                "creative_format":fmt,
                "director_style":style,
                "director_layout":"center",
                "director_camera":"push",
                "format_transition":"cinematic",
                "director_caption_mode":"phrase",
                "director_asset":"editorial-illustration",
                "story_beat":"reveal",
            },
            {
                "creative_format":fmt,
                "director_style":style,
                "director_layout":"focus-left",
                "director_camera":"drift",
                "format_transition":"cinematic",
                "director_caption_mode":"phrase",
                "director_asset":"mechanism-diagram",
                "story_beat":"mechanism",
            },
        ])

    def test_identical_identity_is_blocked(self):
        fp=self.sample()
        result=identity_gate(fp,[fp])
        self.assertFalse(result["pass"])
        self.assertGreaterEqual(result["highest_similarity"],.82)

    def test_distinct_grammar_scores_lower_similarity(self):
        a=self.sample("cinematic_mini_doc","mixed-media")
        b=self.sample("animated_infographic","vector-motion")
        for field in ("director_layout","director_camera","format_transition","director_caption_mode","director_asset","story_beat"):
            b[field]=["split","focus-right"] if field=="director_layout" else ["scan","arc"]
        self.assertLess(similarity(a,b),.82)


if __name__=="__main__":
    unittest.main()
