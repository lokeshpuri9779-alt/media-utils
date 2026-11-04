"""Conservative lexical negative controls for one ASTRA lighthouse CPU benchmark.

Never interprets a pass as semantic truth or editorial approval. These checks
can reject known weak patterns, but cannot recognize all incoherent stories.
Only the explicitly named lighthouse-repair experimental profile is supported.
"""
from __future__ import annotations
import re

PROFILE = "lighthouse_warning_repair_v1"

ACTOR = re.compile(r"\brobot\b", re.I)
SETTING = re.compile(r"\blighthouse\b", re.I)
GOAL = re.compile(r"\b(?:warning|signal|beacon|lamp|light)\b", re.I)
PHYSICAL_ACTION = re.compile(
    r"\b(?:climbs?|opens?|inspects?|traces?|removes?|tests?|pulls?|"
    r"turns?|solders?|splices?|reconnects?|replaces?|repairs?|"
    r"restores?|fixes?|connects?|lifts?|installs?|tightens?)\b", re.I
)
OBSTACLE = re.compile(
    r"\b(?:storm|lightning|drops?|breaks?|fails?|damaged|"
    r"corroded|cracked|dark|smashed|lost|blocked|jammed|"
    r"disconnected|snaps?|slips?)\b", re.I
)
COMPLETED_ACTION = re.compile(
    r"\b(?:reconnected|reconnects|repaired|repairs|fixed|fixes|"
    r"restored|restores|replaced|replaces|spliced|splices|"
    r"soldered|solders|activated|activates|"
    r"restarted|restarts|powered|powers)\b", re.I
)
VISIBLE_RESULT = re.compile(
    r"\b(?:beam|beacon|signal|warning|lamp|light)\b.*"
    r"\b(?:returns?|shines?|glows?|flashes?|bright|lit|illuminates?|"
    r"works?|resumes?|restored|restarts?|active|warns?)\b|"
    r"\b(?:returns?|shines?|glows?|flashes?|bright|lit|illuminates?|"
    r"works?|resumes?|restored|restarts?|active)\b.*"
    r"\b(?:beam|beacon|signal|warning|lamp|light)\b", re.I
)
NEGATED_COMPLETION = re.compile(
    r"\b(?:never|not|cannot|can't|couldn't|failed to|still trying to)\b"
    r"(?:\W+\w+){0,4}\W+"
    r"(?:repair(?:ed|s)?|fix(?:ed|es)?|restore(?:d|s)?|reconnect(?:ed|s)?|activate(?:d|s)?|restart(?:ed|s)?|power(?:ed|s)?)\b", re.I
)
NAVIGATION = re.compile(r"\b(?:navigates?|navigating|navigate|wanders?|searches?)\b", re.I)


def audit_lighthouse_repair(beats: list[str], *, profile: str = PROFILE) -> dict:
    """Check observable causal cues; pass is never proof of narrative quality."""
    if profile != PROFILE:
        raise ValueError("Unrecognized experimental causality profile")
    if not isinstance(beats, list) or len(beats) != 4 or any(
        not isinstance(beat, str) for beat in beats
    ):
        raise ValueError("Expected exactly four string beats")
    setup, attempt, consequence, payoff = beats
    text = " ".join(beats)
    checks = {
        "subject_continuity_cue": bool(ACTOR.search(setup) and
                                       ACTOR.search(" ".join(beats[1:]))),
        "setting_and_goal_cue": bool(SETTING.search(text) and GOAL.search(text)),
        "attempt_has_physical_action_cue": bool(PHYSICAL_ACTION.search(attempt)),
        "consequence_has_obstacle_cue": bool(OBSTACLE.search(consequence)),
        "payoff_has_completed_repair_cue": bool(COMPLETED_ACTION.search(payoff)
                                                and not NEGATED_COMPLETION.search(payoff)),
        "payoff_has_visible_restoration_cue": bool(VISIBLE_RESULT.search(payoff)),
        "not_repeated_navigation_cue": sum(bool(NAVIGATION.search(b)) for b in
                                           beats[1:]) < 2,
    }
    failures = sorted(key for key, passed in checks.items() if not passed)
    return {
        "profile": profile,
        "check_type": "lexical_negative_controls_only",
        "checks": checks,
        "passed": not failures,
        "failures": failures,
        "semantic_quality": "not_verified",
        "manual_editorial_review_required": True,
        "approved": False,
        "production_ready": False,
        "published": False,
    }
