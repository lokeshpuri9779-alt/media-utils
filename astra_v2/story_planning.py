"""StoryWriter-inspired causal planning checks for original Shorts.

This is a local planning/validation layer, not an external model, and never
approves or publishes drafts. Existing quality and novelty gates remain active.
"""
ROLES = ("reveal", "build", "twist", "payoff")


def planning_issues(story):
    performance_scenes = story.get("performance_scenes")
    if performance_scenes is not None:
        if not isinstance(performance_scenes, list) or len(performance_scenes) != 7:
            return ["seven_performance_scenes_required"]
        expected = ("hook", "stakes", "attempt", "setback", "discovery", "climax", "payoff")
        issues = []
        speeches = []
        for index, (scene, role) in enumerate(zip(performance_scenes, expected), start=1):
            if not isinstance(scene, dict):
                return ["invalid_performance_scene"]
            if scene.get("role") != role:
                issues.append("invalid_performance_scene_role")
            speech = str(scene.get("speech") or "").strip()
            speeches.append(speech.casefold())
            if len(speech.split()) < 5:
                issues.append("short_or_empty_performance_scene_narration")
            if not str(scene.get("visual") or "").strip():
                issues.append("missing_performance_scene_visual")
            if not str(scene.get("visual_prompt") or "").strip():
                issues.append("missing_performance_scene_visual_prompt")
        if len(set(speeches)) != 7:
            issues.append("repeated_performance_scene_narration")
        renderer_beats = story.get("story_beats") or []
        if not isinstance(renderer_beats, list) or len(renderer_beats) != 7:
            issues.append("seven_renderer_beats_required")
        return sorted(set(issues))

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
    if (roles[0] != "reveal" or roles[-1] != "payoff"
            or any(role not in ("build", "mechanism", "twist") for role in roles[1:-1])):
        issues.append("missing_causal_story_progression")
    if len(set(narrations)) != 4:
        issues.append("repeated_narration")
    return sorted(set(issues))


def is_planned_story(story):
    return not planning_issues(story)
