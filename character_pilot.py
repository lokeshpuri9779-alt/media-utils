from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from character_animation import character_storyboard
from character_stories import pilot_story
from character_video_engine import provider_status, generate_storyboard
from studio_renderer import make_plan, voice_plan, score_audio
from character_video_compositor import compose_character_short


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
    storyboard=character_storyboard(story,plan)
    duration=voice_plan(
        plan,story["genre"],max_duration=float(story.get("target_duration_max",36)),
        voice_name=str(story.get("voice_profile") or "af_heart"),
        voice_speed=float(story.get("voice_speed") or 1.03),
    )
    for shot_spec,scene_spec in zip(storyboard,plan):
        shot_spec["target_seconds"]=max(1.0,float(scene_spec.get("duration") or 0))

    with tempfile.TemporaryDirectory(prefix="astra_character_pilot_") as td:
        root=Path(td)
        audio=root/"mix.wav"
        audio_info=score_audio(plan,duration,story["genre"],audio)
        clips,generation=generate_storyboard(storyboard,root/"generated")
        composition=compose_character_short(
            clips,[float(x.get("duration") or 0) for x in plan],audio,output
        )
    return {
        "content_id":story["content_id"],
        "title":story["title"],
        "provider":provider_status(),
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
    if args.render:
        result=render(args.render)
    else:
        result=dry_run()
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    main()
