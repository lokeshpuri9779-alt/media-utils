"""StoryWriter-inspired causal planning checks for original Shorts.

This is a local planning/validation layer, not an external model, and never
approves or publishes drafts. Existing quality and novelty gates remain active.
"""
ROLES = ("reveal", "build", "twist", "payoff")


def planning_issues(story):
    beats = story.get("story_beats") or []
    if not isinstance(beats, list) or len(beats) != 4:
        return ["four_beats_required"]
    issues = []
    roles = []
    narrations = []
    for beat in beats:
        if not isinstance(beat, dict):
            return ["invalid_beat"]
        role = str(beat.get("story_beat") or "").strip()
        roles.append(role)
        speech = str(beat.get("speech") or "").strip()
        narrations.append(speech.casefold())
        if len(speech.split()) < 6:
            issues.append("short_or_empty_narration")
        if not str(beat.get("visual") or "").strip():
            issues.append("missing_visual_direction")
    if tuple(roles) != ROLES:
        issues.append("missing_causal_story_progression")
    if len(set(narrations)) != 4:
        issues.append("repeated_narration")
    return sorted(set(issues))


def is_planned_story(story):
    return not planning_issues(story)
