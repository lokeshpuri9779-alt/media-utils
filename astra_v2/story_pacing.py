"""Offline story pacing and suspense diagnostics.

Advisory only: this module never rewrites, approves, renders, or publishes stories.
"""
from __future__ import annotations

import re

_TENSION = {
    "danger": ("danger", "trapped", "fall", "fire", "flood", "storm", "attack",
               "chase", "crash", "injured", "vanish", "disappear", "explode"),
    "urgency": ("before", "deadline", "seconds", "minute", "midnight", "last",
                "countdown", "too late", "running out", "hurry"),
    "uncertainty": ("unknown", "mystery", "secret", "impossible", "missing",
                    "strange", "shadow", "silence", "why", "who", "where"),
    "reversal": ("but", "however", "instead", "wrong", "except", "revealed",
                 "actually", "turned out", "not what", "betray"),
}
_HOOK_CUES = ("?", "!", "until", "before", "when", "nobody", "never", "suddenly",
              "missing", "vanished", "secret", "trapped", "last", "why", "how")
_ROLE_ARCS = ("cold_open", "goal_and_stakes", "first_obstacle", "escalation",
              "reversal_or_reveal", "payoff_and_emotional_button")


def _words(text):
    return re.findall(r"[a-z0-9']+", str(text).casefold())


def review_pacing(story: dict, format_name: str = "shorts") -> dict:
    """Return measurable pacing signals and practical rewrite prompts."""
    if not isinstance(story, dict):
        raise TypeError("story must be a mapping")
    if format_name not in ("shorts", "longform"):
        raise ValueError("unsupported format")
    beats = story.get("story_beats") or []
    if not isinstance(beats, list):
        return {"status": "invalid_beats", "approval": False}
    speeches = [str(b.get("speech") or "").strip()
                for b in beats if isinstance(b, dict)]
    counts = [len(_words(s)) for s in speeches]
    total = sum(counts)
    first = speeches[0].casefold() if speeches else ""
    full = " ".join(speeches).casefold()
    lower_target, upper_target = ((95, 155) if format_name == "shorts"
                                  else (900, 1800))
    issues = []
    if not speeches:
        issues.append("add_narration")
    if counts and counts[0] < (12 if format_name == "shorts" else 25):
        issues.append("open_with_a_specific_disruption_or_question")
    if total < lower_target:
        issues.append("add_story_content_not_filler")
    if total > upper_target:
        issues.append("tighten_or_split_for_breathing_room")
    if len(beats) < (6 if format_name == "shorts" else 10):
        issues.append("expand_into_more_visual_story_turns")
    if not any(cue in first for cue in _HOOK_CUES):
        issues.append("make_the_first_line_create_an_open_loop")
    tension_counts = {
        category: sum(1 for cue in cues if cue in full)
        for category, cues in _TENSION.items()
    }
    if tension_counts["danger"] + tension_counts["urgency"] == 0:
        issues.append("raise_concrete_stakes_or_a_visible_deadline")
    if tension_counts["reversal"] == 0:
        issues.append("add_a_genuine_mid_story_reversal")
    if tension_counts["uncertainty"] == 0:
        issues.append("plant_a_question_or_clue_early")
    if len(set(s.casefold() for s in speeches if s)) < len([s for s in speeches if s]):
        issues.append("remove_repeated_beats")
    dialogue_lines = sum(1 for s in speeches if re.search(r'["“].+?["”]', s))
    return {
        "status": "needs_story_development" if issues else "pacing_signals_present",
        "format": format_name,
        "word_count": total,
        "estimated_seconds_at_150_wpm": round(total / 150 * 60),
        "beat_count": len(speeches),
        "beat_word_counts": counts,
        "dialogue_beat_count": dialogue_lines,
        "tension_signals": tension_counts,
        "recommended_arc": list(_ROLE_ARCS),
        "issues": issues,
        "approval": False,
    }
