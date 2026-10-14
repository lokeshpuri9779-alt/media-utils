"""Render one offline story per worker; intentionally never publishes."""
import argparse
import json
from pathlib import Path
from astra_v2.story_batch import build_story_batch
from astra_v2.coordinated_development import render


def render_one(index, output, seed="astra-story-rehearsal", fps=8, seconds_per_scene=2):
    batch = build_story_batch(seed)
    if not isinstance(index, int) or not 0 <= index < batch["story_count"]:
        raise ValueError("story index outside batch")
    plan = batch["stories"][index]
    if plan.get("publication_allowed") is not False:
        raise ValueError("publishing must remain disabled")
    report = render(plan, Path(output), fps=fps,
                    seconds_per_scene=seconds_per_scene, video=True)
    report["title"] = plan["title"]
    report["video_has_audio"] = False  # Generic story renders are silent today.
    report["publication_allowed"] = False
    (Path(output) / "batch-result.json").write_text(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=int, required=True)
    parser.add_argument("--seed", default="astra-story-rehearsal")
    parser.add_argument("--output", required=True)
    parser.add_argument("--fps", type=int, default=8)
    parser.add_argument("--seconds-per-scene", type=int, default=2)
    args = parser.parse_args()
    print(json.dumps(render_one(args.index, args.output, args.seed,
                                args.fps, args.seconds_per_scene), indent=2))
