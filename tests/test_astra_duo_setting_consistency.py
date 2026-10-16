import unittest
from unittest.mock import patch

class DuoSettingConsistencyTests(unittest.TestCase):
    def test_explicit_setting_is_respected_by_scene_direction(self):
        from astra_v2.pillow_scene_direction import story_setting
        self.assertEqual(story_setting({'speech':'The fox carried a book.',
                                        'story_environment':'harbor'}),'harbor')
        self.assertEqual(story_setting({'speech':'They arrived at the library.',
                                        'story_environment':'harbor'}),'library')

if __name__ == '__main__': unittest.main()
