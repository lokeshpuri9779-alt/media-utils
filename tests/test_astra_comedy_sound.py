"""Tests for original offline comedic Foley and non-silent soundtrack."""
import hashlib
import json
import math
import struct
import unittest
import wave
from pathlib import Path
from tempfile import TemporaryDirectory

from astra_v2.comedy_sound import (
    SAMPLE_RATE, ACTION_EVENTS, action_cues, write_soundtrack
)
from astra_v2.coordinated_development import build_comedy_demo, build_plan


class OfflineComedySoundTests(unittest.TestCase):
    def test_cues_cover_each_scene_and_pickup(self):
        plan = build_comedy_demo()
        cues = action_cues(plan, seconds_per_scene=3)
        actions = {cue["action"] for cue in cues}
        self.assertEqual(actions, {s["action"] for s in plan["scenes"]})
        self.assertEqual(len(cues), sum(len(v) for v in ACTION_EVENTS.values()))
        self.assertEqual(
            [cue["event"] for cue in cues if cue["action"] == "carry"],
            ["soft_footstep", "lift", "pop"],
        )
        self.assertTrue(all(0 <= cue["at_seconds"] < 15 for cue in cues))

    def test_15_second_soundtrack_has_audible_dynamic_range_and_is_reproducible(self):
        with TemporaryDirectory() as d:
            first = Path(d) / "soundtrack.wav"
            manifest = write_soundtrack(build_comedy_demo(), first, seconds_per_scene=3)
            self.assertTrue((Path(d) / "sound-cues.json").is_file())
            self.assertFalse(manifest["publication_allowed"])
            self.assertFalse(manifest["licensed_audio_assets_used"])
            self.assertEqual(manifest["origin"], "deterministic-original-synthesis")
            with wave.open(str(first), "rb") as track:
                self.assertEqual(track.getframerate(), SAMPLE_RATE)
                self.assertEqual(track.getnchannels(), 1)
                self.assertEqual(track.getsampwidth(), 2)
                self.assertEqual(track.getnframes(), SAMPLE_RATE * 15)
                pcm = track.readframes(track.getnframes())
            samples = struct.unpack("<" + "h" * (len(pcm) // 2), pcm)
            self.assertGreater(max(abs(v) for v in samples), 2000)
            self.assertLess(max(abs(v) for v in samples), 30000)
            block = SAMPLE_RATE
            rms = []
            for start in range(0, len(samples), block):
                section = samples[start:start + block]
                rms.append(math.sqrt(sum(v * v for v in section) / len(section)))
            self.assertEqual(len(rms), 15)
            self.assertGreater(min(rms), 100)
            self.assertGreater(max(rms), min(rms) * 1.25)
            second = Path(d) / "other.wav"
            write_soundtrack(build_comedy_demo(), second, seconds_per_scene=3)
            self.assertEqual(hashlib.sha256(first.read_bytes()).digest(),
                             hashlib.sha256(second.read_bytes()).digest())

    def test_safeguards_reject_non_comedy_and_invalid_input(self):
        with TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                write_soundtrack(build_plan("non-comedy", 2),
                                 Path(d) / "not-allowed.wav")
            with self.assertRaises(ValueError):
                write_soundtrack(build_comedy_demo(),
                                 Path(d) / "bad.wav", sample_rate=44100)
            with self.assertRaises(ValueError):
                action_cues(build_comedy_demo(), seconds_per_scene=0)


if __name__ == "__main__":
    unittest.main()
