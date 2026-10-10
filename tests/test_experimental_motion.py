"""CPU-only regression tests: reject static video, accept actual motion."""
import shutil,subprocess,tempfile,unittest
from pathlib import Path
from tools.verify_experimental_motion import probe_video

@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'FFmpeg unavailable')
class MotionTests(unittest.TestCase):
    def encode(self,output,source):
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','lavfi','-i',source,
                        '-t','4','-c:v','libx264','-pix_fmt','yuv420p',str(output)],check=True,timeout=45)
    def test_static_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'still.mp4';self.encode(p,'color=c=black:s=480x854:r=12')
            self.assertFalse(probe_video(p)['pass'])
    def test_moving_frames_pass(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'motion.mp4';self.encode(p,'testsrc2=s=480x854:r=12')
            self.assertTrue(probe_video(p)['pass'])

if __name__=='__main__':unittest.main()
