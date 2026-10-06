import unittest

from creative_formats import choose_format, apply_format


class CreativeFormatTests(unittest.TestCase):
    def test_space_media_story_can_use_cinematic_format(self):
        story={
            "genre":"space","content_id":"space-a",
            "story_beats":[{"visual":"media"},{"visual":"media"},{"visual":"media"}]
        }
        fmt=choose_format(story,[])
        self.assertIn(fmt["name"],{"cinematic_mini_doc","documentary_montage","mixed_media_story"})

    def test_recent_formats_are_avoided_when_alternative_exists(self):
        story={
            "genre":"space","content_id":"space-b",
            "story_beats":[{"visual":"media"},{"visual":"media"}]
        }
        fmt=choose_format(story,["cinematic_mini_doc","documentary_montage"])
        self.assertEqual(fmt["name"],"mixed_media_story")

    def test_formats_change_shot_grammar(self):
        base=[{"director_camera":"push","director_layout":"center","director_energy":0.5}]
        a=apply_format([dict(base[0])],{"name":"cinematic_mini_doc","transition":"cinematic","brand":"minimal","headline":"minimal","caption":"lower-third"})
        b=apply_format([dict(base[0])],{"name":"animated_infographic","transition":"wipe","brand":"corner","headline":"data-led","caption":"keyword"})
        self.assertNotEqual(
            (a[0]["director_camera"],a[0]["director_layout"],a[0]["format_transition"]),
            (b[0]["director_camera"],b[0]["director_layout"],b[0]["format_transition"])
        )


if __name__=="__main__":
    unittest.main()
