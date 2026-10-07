from __future__ import annotations

"""Reference-derived character animation direction for Astra.

This module encodes the visual grammar seen in the user-supplied reference
videos without copying their characters, logos, text, or exact shots.
"""

REFERENCE_PROFILES = {
    "stylized_3d_story": {
        "render_style": "stylized 3D animated film",
        "character_design": "rounded expressive human characters, simplified anatomy, readable silhouettes",
        "lighting": "warm natural sunlight with soft rim light",
        "lens": "portrait-to-normal lens with shallow depth of field",
        "camera": ["slow push-in", "gentle tracking", "medium close-up", "full-body establishing"],
        "framing": "character dominant, full-frame vertical composition",
        "environment": "rich but softly defocused background",
        "motion": "clear body acting, hand gestures, head turns, facial reaction",
        "shot_seconds": [1.8, 3.2],
        "text_policy": "minimal; story should remain understandable without card-style text",
        "transition": "mostly hard cuts motivated by action",
        "continuity": "same character wardrobe, face, age, body proportions and environment across shots",
    },
    "semi_real_character_comedy": {
        "render_style": "semi-photoreal cinematic AI character video",
        "character_design": "realistic textures with exaggerated readable expression and body language",
        "lighting": "bright natural street/daylight with cinematic contrast",
        "lens": "normal-to-wide environmental portrait",
        "camera": ["handheld-like track", "medium two-shot", "reaction close-up", "push-in"],
        "framing": "characters and physical action fill the image",
        "environment": "recognizable real-world setting with depth and practical detail",
        "motion": "fast reaction acting, object interaction, comedic timing",
        "shot_seconds": [1.3, 2.8],
        "text_policy": "minimal overlays only; avoid explainer-card layout",
        "transition": "hard cuts on reaction/action",
        "continuity": "preserve character identity, clothing, location and prop continuity",
    },
    "family_3d_animal_comedy": {
        "render_style": "polished family-friendly stylized 3D animation",
        "character_design": "anthropomorphic animals with rounded proportions, large expressive eyes, readable paws and exaggerated facial acting",
        "lighting": "bright warm sunlight with volumetric rays, soft bounce light and saturated natural color",
        "lens": "normal portrait lens with shallow depth of field for reactions",
        "camera": ["wide establishing", "medium action shot", "reaction close-up", "group payoff"],
        "framing": "full-frame character staging with clear foreground action and layered environment depth",
        "environment": "lush colorful environment with soft background detail and strong depth separation",
        "motion": "clear pose-to-pose acting, squash-and-stretch facial reactions, paw/hand gestures, fast comedic anticipation and payoff",
        "shot_seconds": [1.2, 2.6],
        "text_policy": "no explainer cards; optional tiny captions only",
        "transition": "hard cuts on action or reaction",
        "continuity": "preserve species, fur markings, wardrobe, scale, props and environment across every shot",
    },
}


def choose_character_variant(story: dict) -> str:
    genre=str(story.get("genre") or "").lower()
    tone=" ".join(str(story.get(k) or "") for k in ("tone","hook","question","answer","title")).lower()
    if any(x in tone for x in ("lion","rabbit","cub","jungle","animal family","cartoon animal")):
        return "family_3d_animal_comedy"
    if any(x in tone for x in ("funny","comedy","monkey","reaction","prank","chaos")):
        return "semi_real_character_comedy"
    if genre == "fiction" or any(x in tone for x in ("story","grandfather","village","emotional","moral")):
        return "stylized_3d_story"
    return "stylized_3d_story"


def build_character_shot_prompt(story: dict, shot: dict, index: int, total: int) -> dict:
    variant=choose_character_variant(story)
    profile=REFERENCE_PROFILES[variant]
    subject=str(shot.get("speech") or shot.get("headline") or "").strip()
    action=str(shot.get("character_action") or subject)
    continuity=str(story.get("character_bible") or "Maintain the same established characters and wardrobe.")
    prompt=(
        f"{profile['render_style']}. Vertical 9:16. {profile['character_design']}. "
        f"Scene {index+1} of {total}: {action}. "
        f"{profile['lighting']}. {profile['framing']}. "
        f"Camera: {profile['camera'][index % len(profile['camera'])]}. "
        f"Motion: {profile['motion']}. {profile['environment']}. "
        f"Continuity: {continuity} No card UI, no infographic layout, no copied logos or watermarks."
    )
    return {
        "engine_role": "character-video-generation",
        "variant": variant,
        "prompt": prompt,
        "negative": "static slideshow, presentation card, infographic panel, deformed hands, identity drift, text-heavy frame, watermark",
        "target_seconds": profile["shot_seconds"],
        "continuity_required": True,
        "full_frame": True,
    }


def character_storyboard(story: dict, scenes: list[dict]) -> list[dict]:
    return [build_character_shot_prompt(story, shot, i, len(scenes)) for i,shot in enumerate(scenes)]
