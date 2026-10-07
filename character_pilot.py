from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from character_animation import character_storyboard
from character_audio import prepare_character_audio
from character_stories import pilot_story
from character_video_engine import provider_status, generate_storyboard
from studio_renderer import make_plan
from character_video_compositor import compose_character_short
from generation_admission import assert_generation_admitted


def dry_run() -> dict:
    story=pilot_story()
    plan=make_plan(story)
    storyboard=character_storyboard(story,plan)
    return {
        "content_id": story["content_id"],
        "title": story["title"],
        "format": next((x.get("creative_format") for x in plan if x.get("creative_format")),""),
        "provider": provider_status(),
        "scene_count": len(plan),
        "character_bible": story["character_bible"],
        "storyboard": storyboard,
        "spend_attempted": False,
    }


def render(output: Path) -> dict:
    story=pilot_story()
    plan=make_plan(story)

    with tempfile.TemporaryDirectory(prefix="astra_character_pilot_") as td:
        root=Path(td)
        audio=root/"mix.wav"

        # Dialogue comes first. Scene lengths are derived from the actual
        # synthesized lines so Agnes animation and final audio share one clock.
        duration,audio_info=prepare_character_audio(story,plan,audio)
        storyboard=character_storyboard(story,plan)

        scene_seconds=[]
        for shot_spec,scene_spec in zip(storyboard,plan):
            sec=max(1.0,float(scene_spec.get("duration") or 0))
            if sec>5.0:
                raise RuntimeError(
                    f"Scene {len(scene_seconds)+1} needs {sec:.2f}s. "
                    "Split the dialogue beat instead of looping a short Agnes clip."
                )
            shot_spec["target_seconds"]=sec
            timing=scene_spec.get("dialogue_segments") or []
            shot_spec["dialogue_timing"]=timing
            timing_text="; ".join(
                f"{float(x['start']):.3f}-{float(x['end']):.3f}s: {x.get('speaker','character')} says {x.get('text','')}"
                for x in timing
            )
            shot_spec["prompt"] += (
                f" Exact scene length: {sec:.2f} seconds. "
                f"Dialogue timing plan: {timing_text}. "
                "Use the supplied visual action as the timing spine. "
                "Only the named speaking character should move their mouth during that line; "
                "listeners react silently with eyes, ears, head and body language. "
                "Finish the spoken mouth action before the final reaction hold. "
                "Do not generate visible text, extra dialogue, or unrelated vocalizations."
            )
            scene_seconds.append(sec)

        admission=assert_generation_admitted(
            provider_status(),
            publish_mode="private",
            scene_count=len(plan),
            requested_scene_seconds=scene_seconds,
        )

        clips,generation=generate_storyboard(storyboard,root/"generated")
        composition=compose_character_short(
            clips,[float(x.get("duration") or 0) for x in plan],audio,output
        )

        target_min=float(story.get("target_duration_min",20))
        target_max=float(story.get("target_duration_max",40))
        actual=float(composition.get("duration") or 0)
        if not (target_min <= actual <= target_max):
            raise RuntimeError(
                f"Character pilot duration {actual:.2f}s outside target range "
                f"{target_min:.2f}-{target_max:.2f}s."
            )
        if abs(actual-float(audio_info.get("duration") or 0))>.08:
            raise RuntimeError(
                f"Audio/video sync gate failed: video={actual:.3f}s "
                f"audio={float(audio_info.get('duration') or 0):.3f}s."
            )
        if composition.get("resolution") != [1080,1920]:
            raise RuntimeError("Character pilot did not normalize to 1080x1920.")
        if int(composition.get("scene_count") or 0) < 6:
            raise RuntimeError("Character pilot needs at least 6 scenes for a complete story arc.")

    return {
        "content_id":story["content_id"],
        "title":story["title"],
        "provider":provider_status(),
        "admission":admission,
        "audio":audio_info,
        "generation":generation,
        "composition":composition,
        "output":str(output),
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--dry-run",action="store_true")
    ap.add_argument("--render",type=Path)
    args=ap.parse_args()
    result=render(args.render) if args.render else dry_run()
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    main()
