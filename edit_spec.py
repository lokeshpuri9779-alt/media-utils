from __future__ import annotations

"""Renderer-neutral edit specification.

The creative brain describes a film as structured data first. Renderers are
replaceable backends; story logic, provenance and QA are not renderer-specific.
"""

SCHEMA = "astra-edit-v1"
SUPPORTED_PROCEDURAL = {
    "tidal_lock", "iss_orbit", "planet", "orbit", "compare", "pitch",
    "screen", "keys", "ship", "signal", "door", "robot", "forest",
}


def build_edit_spec(story: dict) -> dict:
    scenes = []
    for index, beat in enumerate(story.get("story_beats") or [], start=1):
        visual = str(beat.get("visual") or "").strip()
        scenes.append({
            "id": f"s{index:02d}",
            "beat": str(beat.get("story_beat") or "").strip(),
            "headline": str(beat.get("headline") or "").strip(),
            "narration": str(beat.get("speech") or "").strip(),
            "visual": {
                "type": visual,
                "exact_media": str(beat.get("media_file") or "").strip(),
                "query": str(beat.get("media_query") or "").strip(),
                "fit": str(beat.get("media_fit") or "cover").strip(),
                "motion": str(beat.get("media_motion") or "still").strip(),
            },
        })
    return {
        "schema": SCHEMA,
        "content_id": story.get("content_id"),
        "title": story.get("title"),
        "genre": story.get("genre"),
        "source": story.get("source"),
        "voice": {
            "profile": story.get("voice_profile", "af_heart"),
            "speed": float(story.get("voice_speed") or 1.09),
        },
        "format": {"width": 1080, "height": 1920, "fps": 30},
        "scenes": scenes,
    }


def preflight(spec: dict) -> dict:
    failures = []
    notes = []
    scenes = spec.get("scenes") or []
    if spec.get("schema") != SCHEMA:
        failures.append("unknown edit schema")
    if not (3 <= len(scenes) <= 8):
        failures.append("premium short needs 3-8 purposeful scenes")
    narration_words = 0
    previous = None
    for scene in scenes:
        narration = scene.get("narration") or ""
        narration_words += len(narration.split())
        visual = (scene.get("visual") or {}).get("type")
        exact = (scene.get("visual") or {}).get("exact_media")
        if not narration:
            failures.append(f"{scene.get('id')}: missing narration")
        if visual == "media" and not exact:
            failures.append(f"{scene.get('id')}: editorial media is not exact-pinned")
        if visual != "media" and visual not in SUPPORTED_PROCEDURAL:
            failures.append(f"{scene.get('id')}: unsupported semantic visual {visual!r}")
        if visual == previous:
            notes.append(f"{scene.get('id')}: repeated visual grammar")
        previous = visual
    if narration_words > 90:
        failures.append("narration is too dense for a premium Short")
    if narration_words < 18:
        failures.append("narration is too thin to deliver a complete payoff")
    return {
        "pass": not failures,
        "failures": failures,
        "notes": notes,
        "narration_words": narration_words,
        "scene_count": len(scenes),
    }
