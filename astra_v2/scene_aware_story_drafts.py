"""Produce explicit scene-aware *draft* story beats from concept briefs.

Template output is for editorial development, not automatic publishing.
"""
import hashlib
from astra_v2.visual_artifact_backdrop import SCENE_TERMS


def draft_story(concept):
    required = ("family", "setting", "protagonist", "goal", "conflict", "twist", "beat_roles")
    if any(not concept.get(k) for k in required):
        raise ValueError("incomplete story concept")
    setting = str(concept["setting"]).strip().lower()
    if setting not in SCENE_TERMS:
        raise ValueError("setting not supported by verified background taxonomy")
    roles = concept["beat_roles"]
    if not isinstance(roles, (list, tuple)) or len(roles) < 3:
        raise ValueError("at least three narrative beats required")
    protagonist = str(concept["protagonist"]).strip()
    goal = str(concept["goal"]).strip()
    conflict = str(concept["conflict"]).strip()
    twist = str(concept["twist"]).strip()
    story_id = hashlib.sha256(repr((protagonist, goal, conflict, twist, setting, tuple(roles))).encode()).hexdigest()[:16]
    beats = []
    for index, role in enumerate(roles):
        if index == 0:
            speech = f"In the {setting}, {protagonist} wanted to {goal}."
            action = f"{protagonist} begins searching for a way to {goal}"
        elif index == len(roles) - 1:
            speech = f"In the end, {twist} changed everything for {protagonist}."
            action = f"{protagonist} reacts as {twist}"
        elif index == 1:
            speech = f"But {conflict} stood in the way."
            action = f"{protagonist} confronts {conflict}"
        else:
            speech = f"The situation shifted when {twist} came into view."
            action = f"{protagonist} discovers {twist}"
        beats.append({
            "story_beat": str(role),
            "headline": str(role).replace("_", " ").upper(),
            "speech": speech,
            "visual": f"{setting} scene: {action}",
            "story_environment": setting,
            "visual_intent": action,
        })
    return {
        "content_id": "story-draft-" + story_id,
        "title": f"{protagonist} and the {twist}",
        "genre": "fiction",
        "story_environment": setting,
        "plot_family": concept["family"],
        "story_beats": beats,
        "editorial_approved": False,
        "asset_verified": False,
        "draft_only": True,
    }
