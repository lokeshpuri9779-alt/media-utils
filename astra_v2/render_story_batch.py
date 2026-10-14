"""Render one offline story per worker; intentionally never publishes."""
import argparse
import json
from pathlib import Path
from astra_v2.story_batch import build_story_batch
from astra_v2.coordinated_development import render


def render_one(index, output, seed="astra-story-rehearsal", fps=8, seconds_per_scene=2, episode=1, composed=False):
    batch = build_story_batch(seed, episode=episode, composed=composed)
    if not isinstance(index, int) or not 0 <= index < batch["story_count"]:
        raise ValueError("story index outside batch")
    plan = batch["stories"][index]
    if plan.get("publication_allowed") is not False:
        raise ValueError("publishing must remain disabled")
    report = render(plan, Path(output), fps=fps,
                    seconds_per_scene=seconds_per_scene, video=True)
    report["title"] = plan["title"]
    report["episode"] = plan["episode"]
    from astra_v2.story_subtitles import write_srt
    write_srt(plan, Path(output) / "captions.srt", seconds_per_scene=seconds_per_scene)
    from astra_v2.story_batch_audio import soundtrack, add_audio
    output = Path(output)
    soundtrack(plan, output / "soundtrack.wav", seconds_per_scene=seconds_per_scene)
    add_audio(output / "preview.mp4", output / "soundtrack.wav",
              output / "preview-with-audio.mp4")
    (output / "preview-with-audio.mp4").replace(output / "preview.mp4")
    report["video_has_audio"] = True
    report["audio_origin"] = "original-procedural-sound-effects"
    report["spoken_narration"] = False
    report["publication_allowed"] = False
    (Path(output) / "batch-result.json").write_text(json.dumps(report, indent=2))
    from astra_v2.story_production_manifest import create_manifest
    create_manifest(plan, output, seconds_per_scene=seconds_per_scene)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=int, required=True)
    parser.add_argument("--seed", default="astra-story-rehearsal")
    parser.add_argument("--episode", type=int, default=1)
    parser.add_argument("--composed", action="store_true")
    parser.add_argument("--output", required=True)
    parser.add_argument("--fps", type=int, default=8)
    parser.add_argument("--seconds-per-scene", type=int, default=2)
    args = parser.parse_args()
    print(json.dumps(render_one(args.index, args.output, args.seed,
                                args.fps, args.seconds_per_scene, args.episode, args.composed), indent=2))
