"""Deterministic plot-family planning for ASTRA fiction drafts.

This module plans *distinct narrative structures*; it does not claim the
resulting story is editorially approved or ready for publication.
"""
import hashlib

PLOT_FAMILIES = {
    "mystery": ("anomaly", "clue", "false_lead", "revelation"),
    "comedy": ("setup", "misunderstanding", "escalation", "punchline"),
    "adventure": ("call", "obstacle", "risk", "escape"),
    "suspense": ("warning", "threat", "reversal", "relief"),
    "heartwarming": ("need", "kindness", "sacrifice", "reunion"),
    "heist": ("target", "plan", "complication", "consequence"),
    "rivalry": ("challenge", "contest", "setback", "respect"),
    "survival": ("danger", "resource", "dilemma", "rescue"),
    "fantasy": ("discovery", "rule", "price", "transformation"),
    "science_fiction": ("invention", "test", "failure", "discovery"),
    "misadventure": ("goal", "mistake", "chain_reaction", "recovery"),
    "moral_dilemma": ("choice", "temptation", "cost", "decision"),
}


def choose_plot_family(content_id, used_families=()):
    """Choose reproducibly, preferring families absent from recent stories."""
    if not isinstance(content_id, str) or not content_id.strip():
        raise ValueError("content_id is required")
    candidates = [name for name in PLOT_FAMILIES if name not in set(used_families)]
    if not candidates:
        candidates = list(PLOT_FAMILIES)
    digest = hashlib.sha256(content_id.encode("utf-8")).digest()
    return candidates[int.from_bytes(digest[:8], "big") % len(candidates)]


def plan_plot(content_id, family=None, used_families=()):
    """Return structured beat roles for a downstream *creative* story writer."""
    family = family or choose_plot_family(content_id, used_families)
    if family not in PLOT_FAMILIES:
        raise ValueError("unsupported plot family: " + str(family))
    return {
        "content_id": content_id,
        "plot_family": family,
        "beat_roles": list(PLOT_FAMILIES[family]),
        "editorial_approved": False,
        "requires": ["original_dialogue", "specific_actions", "explicit_scene_environment",
                     "continuity_review", "asset_validation"],
    }
