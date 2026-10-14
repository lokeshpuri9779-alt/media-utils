import unittest
from experimental.episode_timeline import build_timeline

class EpisodeTimelineTests(unittest.TestCase):
    def test_contiguous_scenes(self):
        t=build_timeline([{"image":"a.png","narration":"Hello","frames":90},
                          {"image":"b.png","narration":"Goodbye","frames":60}])
        self.assertEqual(t["frames"],150)
        self.assertEqual(t["scenes"][0]["end_frame"],t["scenes"][1]["start_frame"])
        self.assertEqual(t["duration_seconds"],5)
        self.assertFalse(t["narration_ready"])
        self.assertFalse(t["publish"])
    def test_reject_missing_narration(self):
        with self.assertRaises(ValueError):
            build_timeline([{"image":"a.png","frames":30}])
    def test_reject_invalid_frames(self):
        with self.assertRaises(ValueError):
            build_timeline([{"image":"a.png","narration":"Test","frames":0}])
if __name__=="__main__":unittest.main()
