"""Real, offline Meta controller integration smoke test. No publishing.
Run: python -m unittest discover -s tests -p test_meta_controller_ffmpeg.py -v
Requires ffmpeg with libx264, AAC and libass subtitle support.
"""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from integrations.meta_pipeline import run

@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg required')
class MetaControllerFFmpegTest(unittest.TestCase):
    def test_real_assembly_soundtrack_captions_and_gate(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            clips = root / 'clips'
            clips.mkdir()
            for i, color in enumerate(('blue', 'red'), 1):
                subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y',
                    '-f', 'lavfi', '-i', f'color=c={color}:s=360x640:r=12:d=5.5',
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(clips / f'scene_{i:03d}.mp4')],
                    check=True, timeout=90)
            manifest = root / 'story.json'
            manifest.write_text(json.dumps({'scenes': [{'prompt':'synthetic test 1'}, {'prompt':'synthetic test 2'}]}))
            soundtrack = root / 'sound.wav'
            subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-f', 'lavfi',
                '-i', 'sine=frequency=440:duration=12', str(soundtrack)], check=True, timeout=30)
            captions = root / 'captions.srt'
            captions.write_text('1\\n00:00:00,000 --> 00:00:04,000\\nSynthetic test\\n')
            result = run(manifest, clips, root / 'output', soundtrack, captions)
            self.assertTrue(result['ready'], result.get('errors'))
            self.assertFalse(result['published'])
            self.assertTrue((root / 'output' / 'final.mp4').is_file())
            self.assertGreaterEqual(result['duration_seconds'], 10)
            self.assertTrue(result['audio_present'])

if __name__ == '__main__':
    unittest.main()
