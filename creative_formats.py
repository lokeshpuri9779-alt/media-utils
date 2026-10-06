from __future__ import annotations

"""Creative Engine v7 format router.

Chooses a visual grammar for each story. Formats change shot composition,
caption treatment, transition rhythm, and audio pacing; they are not merely
different labels on the same Studio template.
"""

import hashlib

FORMATS = {
    "cinematic_mini_doc": {
        "headline": "minimal",
        "caption": "lower-third",
        "transition": "cinematic",
        "motion": "slow",
        "brand": "minimal",
    },
    "documentary_montage": {
        "headline": "burst",
        "caption": "phrase",
        "transition": "hard-cut",
        "motion": "fast",
        "brand": "minimal",
    },
    "animated_infographic": {
        "headline": "data-led",
        "caption": "keyword",
        "transition": "wipe",
        "motion": "guided",
        "brand": "corner",
    },
    "mixed_media_story": {
        "headline": "editorial",
        "caption": "phrase",
        "transition": "collage",
        "motion": "mixed",
        "brand": "minimal",
    },
    "screen_explainer": {
        "headline": "instruction",
        "caption": "keyword",
        "transition": "snap",
        "motion": "guided",
        "brand": "corner",
    },
    "microfiction_cinematic": {
        "headline": "minimal",
        "caption": "lower-third",
        "transition": "cinematic",
        "motion": "slow",
        "brand": "none",
    },
    "ai_character_cinematic": {
        "headline": "none",
        "caption": "minimal",
        "transition": "hard-cut",
        "motion": "character-driven",
        "brand": "none",
        "full_frame": True,
        "target_shot_seconds": [1.8, 3.2],
        "look": "stylized-3d-cinematic",
        "depth_of_field": "shallow",
        "lighting": "warm-cinematic",
    },
    "family_3d_animal_comedy": {
        "headline": "none",
        "caption": "minimal",
        "transition": "hard-cut",
        "motion": "pose-to-pose-comedy",
        "brand": "none",
        "full_frame": True,
        "target_shot_seconds": [1.2, 2.6],
        "look": "polished-family-3d",
        "depth_of_field": "shallow",
        "lighting": "bright-warm-volumetric",
    },
}


def choose_format(story: dict, recent_formats: list[str] | None = None) -> dict:
    recent = [str(x) for x in (recent_formats or []) if x]
    genre = str(story.get("genre") or "")
    beats = story.get("story_beats") or []
    visuals = [str(x.get("visual") or "") for x in beats]

    if story.get("animal_character_story"):
        preferred = ["family_3d_animal_comedy", "ai_character_cinematic", "mixed_media_story"]
    elif story.get("character_story"):
        preferred = ["ai_character_cinematic", "cinematic_mini_doc", "mixed_media_story"]
    elif genre == "fiction":
        preferred = ["ai_character_cinematic", "microfiction_cinematic", "mixed_media_story"]
    elif genre == "tech":
        preferred = ["screen_explainer", "animated_infographic"]
    elif genre in {"football", "current"}:
        preferred = ["documentary_montage", "mixed_media_story", "animated_infographic"]
    elif visuals.count("media") >= 2:
        preferred = ["cinematic_mini_doc", "documentary_montage", "mixed_media_story"]
    else:
        preferred = ["animated_infographic", "mixed_media_story", "cinematic_mini_doc"]

    available = [x for x in preferred if x not in recent[:2]] or preferred
    key = str(story.get("content_id") or story.get("title") or "astra")
    idx = int(hashlib.sha256(key.encode()).hexdigest()[:8], 16) % len(available)
    name = available[idx]
    return {"name": name, **FORMATS[name]}


def apply_format(plan: list[dict], fmt: dict) -> list[dict]:
    name = fmt["name"]
    for i, shot in enumerate(plan):
        shot["creative_format"] = name
        shot["format_transition"] = fmt["transition"]
        shot["format_brand"] = fmt["brand"]
        shot["format_headline"] = fmt["headline"]
        shot["director_caption_mode"] = (
            "keyword" if fmt["caption"] == "keyword"
            else shot.get("director_caption_mode", "phrase")
        )

        if name == "cinematic_mini_doc":
            shot["director_camera"] = ["push","drift","push","track"][i % 4]
            shot["director_energy"] = 0.92 if i == 0 else 0.48
            shot["director_layout"] = ["center","focus-left","focus-right","center"][i % 4]
        elif name == "documentary_montage":
            shot["director_camera"] = ["track","push","reveal","track"][i % 4]
            shot["director_energy"] = 1.0 if i == 0 else 0.84
            shot["director_layout"] = ["focus-left","focus-right","split","center"][i % 4]
        elif name == "animated_infographic":
            shot["director_camera"] = "reveal"
            shot["director_motion"] = ["scan","arc","pulse","scan"][i % 4]
            shot["director_layout"] = ["split","center","focus-left","focus-right"][i % 4]
        elif name == "mixed_media_story":
            shot["director_camera"] = ["drift","track","push","reveal"][i % 4]
            shot["director_style"] = ["mixed-media","stop-motion","vector-motion","mixed-media"][i % 4]
        elif name == "screen_explainer":
            shot["director_camera"] = "reveal"
            shot["director_layout"] = "center"
            shot["director_energy"] = 0.9
        elif name == "microfiction_cinematic":
            shot["director_camera"] = ["drift","push","drift","push"][i % 4]
            shot["director_energy"] = 0.72 if i == 0 else 0.42
            shot["director_layout"] = "center"
        elif name == "ai_character_cinematic":
            shot["director_camera"] = ["push","track","drift","push"][i % 4]
            shot["director_energy"] = 0.90 if i == 0 else 0.76
            shot["director_layout"] = "center"
            shot["director_style"] = "stylized-3d-cinematic"
            shot["director_asset"] = "character-scene"
            shot["director_caption_mode"] = "minimal"
            shot["character_animation"] = True
            shot["full_frame_visual"] = True
            shot["depth_of_field"] = "shallow"
            shot["lighting"] = "warm-cinematic"
            shot["target_shot_seconds"] = 2.4
        elif name == "family_3d_animal_comedy":
            shot["director_camera"] = ["reveal","track","push","reveal"][i % 4]
            shot["director_energy"] = 1.0 if i in {0,2} else 0.82
            shot["director_layout"] = "center"
            shot["director_style"] = "polished-family-3d"
            shot["director_asset"] = "character-scene"
            shot["director_caption_mode"] = "minimal"
            shot["character_animation"] = True
            shot["full_frame_visual"] = True
            shot["depth_of_field"] = "shallow"
            shot["lighting"] = "bright-warm-volumetric"
            shot["target_shot_seconds"] = 1.9
    return plan
