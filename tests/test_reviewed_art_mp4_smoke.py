"""Offline two-scene Studio artwork-to-MP4 integration smoke (never publishes)."""
import hashlib
import json
import math
import subprocess
import tempfile
import unittest
import wave
from pathlib import Path

from PIL import Image
from imageio_ffmpeg import get_ffmpeg_exe
from astra_v2.story_art_direction import bind_reviewed_scenes


class ReviewedArtworkMp4Smoke(unittest.TestCase):
    def test_two_reviewed_scenes_encode_video_with_audio(self):
        from studio_renderer import draw_visual
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "art" / "assets" / "reviewed"
            folder.mkdir(parents=True)
            entries = []
            colors = [(91, 142, 183), (181, 112, 76)]
            for index, color in enumerate(colors, 1):
                png = folder / f"{index:03d}.png"
                Image.new("RGB", (540, 960), color).save(png)
                entries.append({"id": f"reviewed-proof-{index:03d}",
                                "status": "approved", "category": "background",
                                "story_content_id": "proof",
                                "scene_id": f"{index:03d}",
                                "sha256": hashlib.sha256(png.read_bytes()).hexdigest(),
                                "path": f"art/assets/reviewed/{index:03d}.png", "tags": []})
            manifest = root / "art" / "manifest.json"
            manifest.write_text(json.dumps({"assets": entries}))
            plan = bind_reviewed_scenes([
                {"visual": "scene", "speech": "A fox searches."},
                {"visual": "scene", "speech": "The fox finds a bell."},
            ], "proof", manifest)
            audio = root / "tone.wav"
            rate = 16000
            with wave.open(str(audio), "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(rate)
                samples = bytearray()
                for i in range(rate * 2):
                    v = int(3000 * math.sin(2 * math.pi * 440 * i / rate))
                    samples.extend(v.to_bytes(2, "little", signed=True))
                wav.writeframes(samples)
            output = root / "reviewed.mp4"
            cmd = [get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y",
                   "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "540x960",
                   "-r", "8", "-i", "pipe:0", "-i", str(audio),
                   "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264",
                   "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                   "-c:a", "aac", "-shortest", str(output)]
            with subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE) as proc:
                for i in range(16):
                    scene = plan[i // 8]
                    frame = Image.new("RGB", (540, 960))
                    draw_visual(frame, scene, i / 8, 0, (240, 180, 120))
                    self.assertEqual(frame.getpixel((270, 480)), colors[i // 8])
                    proc.stdin.write(frame.tobytes())
                proc.stdin.close()
                error = proc.stderr.read()
                self.assertEqual(proc.wait(timeout=30), 0, error.decode(errors="replace"))
            self.assertGreater(output.stat().st_size, 1000)
            # Decode every frame and verify the encoded media has an audio stream.
            probe = subprocess.run([get_ffmpeg_exe(), "-hide_banner", "-i", str(output),
                                    "-f", "null", "-"], capture_output=True, timeout=30)
            self.assertEqual(probe.returncode, 0, probe.stderr.decode(errors="replace"))
            self.assertIn(b"Video:", probe.stderr)
            self.assertIn(b"Audio:", probe.stderr)


if __name__ == "__main__":
    unittest.main()
