"""Original offline action-based audio for silent story rehearsal MP4s.

No speech synthesis or copyrighted samples. Never publishes.
"""
import json
import math
import struct
import subprocess
import wave
from pathlib import Path

RATE = 24000
NOTES = {
    "walk": (210, 2.4), "run": (310, 6.0), "jump": (540, 1.4),
    "dance": (440, 4.0), "approach": (230, 2.0),
    "point": (720, 1.0), "carry": (330, 1.5),
    "react": (580, 1.0), "celebrate": (660, 3.0),
}


def soundtrack(plan, path, seconds_per_scene=2):
    if not plan.get("pilot_type") == "offline_story_batch":
        raise ValueError("offline story batch required")
    if not 1 <= seconds_per_scene <= 10:
        raise ValueError("invalid duration")
    total = len(plan["scenes"]) * seconds_per_scene
    if not 0 < total <= 120:
        raise ValueError("invalid soundtrack length")
    samples = bytearray(total * RATE * 2)
    events = []
    for scene_index, scene in enumerate(plan["scenes"]):
        action = scene["action"]
        freq, beats = NOTES[action]
        for beat in range(max(1, int(seconds_per_scene * beats))):
            start = scene_index * seconds_per_scene + beat / beats
            if start >= (scene_index + 1) * seconds_per_scene:
                break
            duration = min(.15, (scene_index + 1) * seconds_per_scene - start)
            events.append({"action": action, "at_seconds": round(start, 3)})
            for k in range(int(duration * RATE)):
                position = int(start * RATE) + k
                x = k / RATE
                envelope = math.sin(math.pi * k / max(1, duration * RATE))
                value = .16 * envelope * math.sin(2 * math.pi * freq * x)
                struct.pack_into("<h", samples, position * 2, int(value * 32767))
    path = Path(path)
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(RATE)
        out.writeframes(samples)
    manifest = {"origin": "original-procedural-sound-effects",
                "spoken_narration": False, "licensed_samples": False,
                "events": events, "publication_allowed": False}
    path.with_name("story-audio-manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def add_audio(mp4, wav, output):
    import imageio_ffmpeg
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel",
                    "error", "-y", "-i", str(mp4), "-i", str(wav),
                    "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "96k", "-shortest", str(output)],
                   check=True, timeout=120)
    if not Path(output).is_file() or Path(output).stat().st_size < 1000:
        raise RuntimeError("audio muxing failed")
