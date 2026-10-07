import os
import subprocess
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

import numpy as np
from imageio_ffmpeg import get_ffmpeg_exe

import character_audio
from character_stories import pilot_story
from character_video_compositor import compose_character_short


class CharacterSyncTests(unittest.TestCase):
    def test_speakers_keep_distinct_voices_and_sample_timing(self):
        calls = []
        class Voice:
            def create(self, text, **kwargs):
                calls.append((text, kwargs['voice']))
                return np.full(12000, .2, dtype=np.float32), 24000
        with patch.dict(os.environ, {'ASTRA_CHARACTER_STORY_ID': 'bear-cub-bakery-v1'}):
            story = pilot_story()
        story.update(target_duration_min=0, target_duration_max=5)
        plan = [{'speech': 'Papa: Hello. Milo: Hi!', 'duration': 2}]
        with tempfile.TemporaryDirectory() as td, patch.object(character_audio, 'voice_engine', return_value=Voice()):
            duration, report = character_audio.prepare_character_audio(story, plan, Path(td)/'voice.wav')
        self.assertEqual(calls, [('Hello.', 'am_adam'), ('Hi!', 'af_heart')])
        first, second = report['scene_reports'][0]['dialogue']
        self.assertAlmostEqual(first['start'], .14)
        self.assertAlmostEqual(first['end'], .64)
        self.assertAlmostEqual(second['start'], .78)
        self.assertAlmostEqual(second['end'], 1.28)
        self.assertEqual(duration, 2)

    def test_unlabelled_line_uses_explicit_scene_speaker(self):
        class Voice:
            def create(self, text, **kwargs):
                self.voice = kwargs['voice']
                return np.full(2400, .2, dtype=np.float32), 24000
        engine = Voice()
        story = {'voice_cast': {'Pip': 'af_heart'}, 'target_duration_min': 0}
        plan = [{'speech': 'Hello.', 'speaker': 'Pip', 'voice_name': 'am_adam'}]
        with tempfile.TemporaryDirectory() as td, patch.object(character_audio, 'voice_engine', return_value=engine):
            character_audio.prepare_character_audio(story, plan, Path(td)/'voice.wav')
        self.assertEqual(engine.voice, 'af_heart')
        self.assertEqual(plan[0]['dialogue_segments'][0]['speaker'], 'Pip')

    def test_real_mux_preserves_master_and_does_not_accumulate_cut_drift(self):
        ffmpeg = get_ffmpeg_exe()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            clip, master, output = root/'clip.mp4', root/'master.wav', root/'out.mp4'
            subprocess.run([
                ffmpeg, '-v', 'error', '-y', '-f', 'lavfi', '-i',
                'color=c=red:s=64x96:r=30:d=0.2', '-f', 'lavfi', '-i',
                'sine=frequency=1500:sample_rate=48000:duration=0.2',
                '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', str(clip),
            ], check=True)
            durations = [.217] * 7
            samples = np.sin(2*np.pi*440*np.arange(round(sum(durations)*48000))/48000)*.3
            with wave.open(str(master), 'wb') as wav:
                wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(48000)
                wav.writeframes((samples*32767).astype('<i2').tobytes())
            report = compose_character_short([clip]*7, durations, master, output, width=64, height=96)
            self.assertEqual(report['frame_count'], round(sum(durations)*30))
            self.assertLessEqual(abs(report['duration']-sum(durations)), 1/60)
            self.assertEqual(report['validation'], 'decoded-streams')
            self.assertEqual(report['resolution'], [64, 96])
            pcm = subprocess.run([ffmpeg, '-v', 'error', '-i', str(output), '-vn',
                                  '-ac', '1', '-ar', '48000', '-f', 's16le', 'pipe:1'],
                                 check=True, capture_output=True).stdout
            decoded = np.frombuffer(pcm, dtype='<i2').astype(float)
            spectrum = abs(np.fft.rfft(decoded))
            freq = np.fft.rfftfreq(len(decoded), 1/48000)[np.argmax(spectrum)]
            self.assertAlmostEqual(freq, 440, delta=2)
            self.assertLess(abs(report['audio_duration']-sum(durations)), .08)

    def test_mismatched_master_rejected_before_composition(self):
        with tempfile.TemporaryDirectory() as td:
            master=Path(td)/'master.wav'
            with wave.open(str(master), 'wb') as wav:
                wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(24000)
                wav.writeframes(b'\0\0'*24000)
            with self.assertRaisesRegex(RuntimeError, 'master does not match'):
                compose_character_short([Path('unused.mp4')], [2.0], master, Path(td)/'out.mp4')


if __name__ == '__main__':
    unittest.main()
