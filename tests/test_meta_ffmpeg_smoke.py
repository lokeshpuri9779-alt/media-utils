"""Offline end-to-end Meta lane smoke test. No publishing or network.
Run: python -m unittest discover -s tests -p test_meta_ffmpeg_smoke.py -v
Requires FFmpeg and FFprobe with PNG and H.264 support.
"""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from tools.image_motion import render
from tools.assemble_scenes import assemble
from tools.meta_media_qa import probe
from integrations.meta_publish_gate import validate

@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg required')
class MetaFFmpegSmokeTest(unittest.TestCase):
    def test_two_images_animated_and_assembled(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            scenes = []
            for index, color in enumerate(('blue', 'red')):
                source = root / f'frame{index}.png'
                subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y',
                    '-f', 'lavfi', '-i', f'color=c={color}:s=64x96',
                    '-frames:v', '1', '-update', '1', str(source)], check=True, timeout=30)
                clip = root / f'scene{index}.mp4'
                render(source, clip, 1, 720, 1280, 12)
                self.assertTrue(probe(clip)['passed'])
                scenes.append({'path': clip.name, 'license': 'synthetic-test'})
            manifest = root / 'manifest.json'
            manifest.write_text(json.dumps({'width': 720, 'height': 1280, 'scenes': scenes}))
            output = assemble(manifest, root / 'final.mp4')
            report = probe(output)
            self.assertTrue(report['passed'])
            self.assertAlmostEqual(report['duration_seconds'], 2.0, delta=0.2)
            self.assertEqual((report['width'], report['height']), (720, 1280))
            # Processing QA is not permission to publish: stricter gate rejects
            # this intentionally short, silent, 720p synthetic fixture.
            gate = validate(output, require_audio=True, min_duration=10)
            self.assertFalse(gate['ready'])
            self.assertTrue(gate['errors'])

if __name__ == '__main__':
    unittest.main()
