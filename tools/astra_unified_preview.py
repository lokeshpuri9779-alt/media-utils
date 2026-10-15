"""Offline unified Studio engine smoke preview; NEVER uploads to YouTube."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from PIL import Image
from imageio_ffmpeg import get_ffmpeg_exe
from astra_v2.unified_story_engine import draw_story_frame

FRAMES_PER_SCENE = 18
FPS = 15
MODES = ("solo", "duo", "ensemble", "directed")


def scenes():
    common = {"genre": "fiction", "duration": FRAMES_PER_SCENE / FPS,
              "story_beat": "build", "story_visual_seed": "unified-preview"}
    return [
        {**common, "speech": "The owl opened the old lantern.",
         "story_cast": ("owl",), "story_action": "open",
         "story_environment": "forest", "scene_style": "clue"},
        {**common, "speech": "The fox and rabbit carried the lantern across the bridge.",
         "story_cast": ("fox", "rabbit"), "story_action": "carry",
         "story_environment": "bridge", "scene_style": "action"},
        {**common, "speech": "The fox, rabbit, owl, otter and mouse ran toward the festival.",
         "story_cast": ("fox", "rabbit", "owl", "otter", "mouse"),
         "story_action": "run", "story_environment": "festival",
         "scene_style": "action",
         "acting_notes": {"fox": "run", "rabbit": "jump", "owl": "wave",
                          "otter": "carry", "mouse": "look"}},
        {**common, "speech": "A new planet emerged from the darkness of space.",
         "visual": "planet", "label": "THE NEW WORLD",
         "sub": "The journey begins", "story_action": "look"},
    ]


def main():
    from studio_renderer import draw_visual
    output = Path("preview")
    output.mkdir(exist_ok=True)
    mp4 = output / "astra-unified-engine-preview.mp4"
    command = [get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y",
               "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "540x960",
               "-r", str(FPS), "-i", "-", "-c:v", "libx264",
               "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
               "-movflags", "+faststart", str(mp4)]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    successful = False
    observed = []
    try:
        for index, shot in enumerate(scenes()):
            for frame in range(FRAMES_PER_SCENE):
                t = frame / FPS
                image = Image.new("RGB", (1080, 1920), (15, 23, 43))
                mode = draw_story_frame(image, shot, t,
                                        draw_directed=draw_visual,
                                        global_time=index * FRAMES_PER_SCENE / FPS + t,
                                        accent=(180, 218, 247))
                if frame == 0:
                    observed.append(mode)
                    image.resize((540, 960), Image.Resampling.LANCZOS).save(
                        output / f"astra-unified-{mode}.png")
                process.stdin.write(image.resize(
                    (540, 960), Image.Resampling.BILINEAR).tobytes())
        successful = True
    finally:
        if process.stdin:
            process.stdin.close()
        code = process.wait()
        if code or not successful:
            raise RuntimeError("Unified story preview failed to encode")
    if tuple(observed) != MODES or mp4.stat().st_size < 30000:
        raise RuntimeError("Unified renderer failed to produce all story grammars")
    manifest = {
        "renderer": "studio-unified-preview",
        "modes": observed,
        "frames": len(scenes()) * FRAMES_PER_SCENE,
        "fps": FPS,
        "width": 540,
        "height": 960,
        "has_audio": False,
        "production_ready": False,
        "published_to_youtube": False,
    }
    (output / "astra-unified-engine-preview.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("ASTRA_UNIFIED_PREVIEW=" + json.dumps(manifest))


if __name__ == "__main__":
    main()
