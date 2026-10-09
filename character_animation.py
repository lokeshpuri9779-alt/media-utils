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
    "cinematic_sci_fi": {
        "render_style": "cinematic science fiction animation with volumetric depth",
        "character_design": "distinct silhouettes, consistent suits and expressive faces",
        "lighting": "atmospheric colored practical lights and motivated rim lighting",
        "lens": "wide establishing lenses alternating with intimate close-ups",
        "camera": ["orbital tracking shot", "low-angle dolly in", "parallax reveal", "slow crane rise"],
        "framing": "immersive full-frame vertical action with foreground and background layers",
        "environment": "detailed spaceships, stations, alien landscapes and drifting particles",
        "motion": "purposeful character acting, moving environment layers and physical camera travel",
        "shot_seconds": [2.0, 4.0],
        "text_policy": "no presentation cards; only necessary story captions",
        "transition": "motivated match cuts and cinematic hard cuts",
        "continuity": "keep identical characters, suits, vehicles and location geometry",
    },
    "magical_fantasy": {
        "render_style": "stylized animated fantasy film with painterly materials",
        "character_design": "appealing expressive characters with clear readable gestures",
        "lighting": "soft enchanted glow, warm bounce and luminous particles",
        "lens": "cinematic medium shots with occasional sweeping wide shots",
        "camera": ["floating camera drift", "spiral reveal", "foreground parallax", "gentle push-in"],
        "framing": "character-centered vertical compositions with layered magical environments",
        "environment": "enchanted forests, mysterious doors, floating lights and living landscapes",
        "motion": "expressive body acting, fabric follow-through and environmental magical motion",
        "shot_seconds": [1.8, 3.6],
        "text_policy": "minimal captions; visuals carry the story",
        "transition": "action-led cuts and occasional light-match transitions",
        "continuity": "maintain faces, costumes, props and spatial relationships across shots",
    },
    "stop_motion": {
        "render_style": "handcrafted stop-motion animation",
        "character_design": "tactile clay and miniature puppet characters",
        "lighting": "warm studio lighting",
        "lens": "macro cinematic lens",
        "camera": ["slow tracking", "parallax reveal", "close-up", "wide establishing"],
        "framing": "vertical cinematic composition with clear focal subject",
        "environment": "tabletop miniature set",
        "motion": "pose-to-pose puppet motion",
        "shot_seconds": [1.8, 3.5],
        "text_policy": "minimal text, no explainer cards",
        "transition": "action-motivated cuts",
        "continuity": "preserve characters, materials, wardrobe and environment",
    },
    "anime_action": {
        "render_style": "dynamic hand-drawn anime action",
        "character_design": "expressive inked characters with bold silhouettes",
        "lighting": "dramatic cel-shaded lighting",
        "lens": "energetic tracking camera",
        "camera": ["slow tracking", "parallax reveal", "close-up", "wide establishing"],
        "framing": "vertical cinematic composition with clear focal subject",
        "environment": "layered painted scenery",
        "motion": "impact frames and expressive gestures",
        "shot_seconds": [1.8, 3.5],
        "text_policy": "minimal text, no explainer cards",
        "transition": "action-motivated cuts",
        "continuity": "preserve characters, materials, wardrobe and environment",
    },
    "storybook_watercolor": {
        "render_style": "animated watercolor storybook",
        "character_design": "soft illustrated characters with painterly outlines",
        "lighting": "diffused golden light",
        "lens": "gentle parallax camera",
        "camera": ["slow tracking", "parallax reveal", "close-up", "wide establishing"],
        "framing": "vertical cinematic composition with clear focal subject",
        "environment": "watercolor paper landscapes",
        "motion": "subtle breathing motion and flowing paint",
        "shot_seconds": [1.8, 3.5],
        "text_policy": "minimal text, no explainer cards",
        "transition": "action-motivated cuts",
        "continuity": "preserve characters, materials, wardrobe and environment",
    },
    "neon_noir": {
        "render_style": "neon noir animated thriller",
        "character_design": "graphic silhouettes and cinematic character acting",
        "lighting": "wet neon reflections and strong rim light",
        "lens": "low angle cinematic camera",
        "camera": ["slow tracking", "parallax reveal", "close-up", "wide establishing"],
        "framing": "vertical cinematic composition with clear focal subject",
        "environment": "rainy city streets with deep perspective",
        "motion": "slow suspenseful motion and drifting rain",
        "shot_seconds": [1.8, 3.5],
        "text_policy": "minimal text, no explainer cards",
        "transition": "action-motivated cuts",
        "continuity": "preserve characters, materials, wardrobe and environment",
    },
    "underwater_fantasy": {
        "render_style": "immersive underwater animation",
        "character_design": "expressive marine characters and floating costumes",
        "lighting": "caustic sunlight and bioluminescence",
        "lens": "floating tracking camera",
        "camera": ["slow tracking", "parallax reveal", "close-up", "wide establishing"],
        "framing": "vertical cinematic composition with clear focal subject",
        "environment": "layered coral and deep blue water",
        "motion": "buoyant motion and flowing particles",
        "shot_seconds": [1.8, 3.5],
        "text_policy": "minimal text, no explainer cards",
        "transition": "action-motivated cuts",
        "continuity": "preserve characters, materials, wardrobe and environment",
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
    if any(x in tone for x in ("clay", "puppet", "miniature", "stop motion")):
        return "stop_motion"
    if any(x in tone for x in ("anime", "samurai", "ninja", "battle", "sword")):
        return "anime_action"
    if any(x in tone for x in ("watercolor", "storybook", "fairytale", "picture book")):
        return "storybook_watercolor"
    if any(x in tone for x in ("detective", "cyberpunk", "neon", "noir", "rainy city")):
        return "neon_noir"
    if any(x in tone for x in ("underwater", "ocean", "mermaid", "coral", "submarine")):
        return "underwater_fantasy"
    if any(x in tone for x in ("spaceship", "comet", "mars", "rover", "orbital", "constellation", "starship")):
        return "cinematic_sci_fi"
    if any(x in tone for x in ("magic", "enchanted", "forest", "living tree", "fairy", "mystical")):
        return "magical_fantasy"
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
