import tempfile
import unittest
import wave
from pathlib import Path
from experimental.pillow_2d_engine import render_mp4
from astra_v2.pillow_shadow_assembly import assemble
from astra_v2.pillow_av_qa import inspect

class NarratedShadowTests(unittest.TestCase):
    def test_requires_real_narration(self):
        with self.assertRaises(FileNotFoundError):
            assemble("/missing/video.mp4","/missing/voice.wav","/tmp/missing-out.mp4")

    def test_mux_supplied_wav_and_subtitles(self):
        with tempfile.TemporaryDirectory() as root:
            root=Path(root)
            video=root/"video.mp4";voice=root/"voice.wav";sub=root/"captions.srt";out=root/"combined.mp4"
            render_mp4(str(video),duration=1,fps=8)
            with wave.open(str(voice),"wb") as f:
                f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000)
                f.writeframes(b"\\x00\\x00"*16000)
            sub.write_text("1\\n00:00:00,000 --> 00:00:00,900\\nTest caption\\n",encoding="utf-8")
            report=assemble(video,voice,out,sub)
            self.assertEqual(report["caption_source"],"provided_srt")
            self.assertFalse(report["publication_eligible"])
            self.assertTrue(inspect(out)["video_decodes"])

if __name__=="__main__":
    unittest.main()
