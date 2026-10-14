import unittest
from experimental.episode_timeline import build_timeline
from experimental.episode_captions import captions,timestamp
from experimental.episode_audio_gate import narration_report

class EpisodeAVTests(unittest.TestCase):
    def test_srt_timecodes(self):
        t=build_timeline([{"image":"a.png","narration":"First","frames":30},
                          {"image":"b.png","narration":"Second","frames":60}])
        s=captions(t)
        self.assertIn("00:00:00,000 --> 00:00:01,000",s)
        self.assertIn("00:00:01,000 --> 00:00:03,000",s)
        self.assertIn("Second",s)
    def test_missing_audio_fails_gate(self):
        t=build_timeline([{"image":"a.png","narration":"First","frames":30}])
        self.assertFalse(narration_report(t)["ready"])
    def test_timestamp_rollover(self):
        self.assertEqual(timestamp(61.25),"00:01:01,250")
if __name__=="__main__":unittest.main()
