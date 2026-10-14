"""Offline plot-pattern fingerprints. This is a coarse heuristic, not semantic understanding."""
import re

PLOT_CUES = {
    "loss": ("missing", "lost", "misplaced", "disappears"),
    "damage": ("broken", "damaged", "repairs", "repair"),
    "pursuit": ("runaway", "chases", "races", "escapes"),
    "mystery": ("mysterious", "secret", "clue", "hidden"),
    "recovery": ("returns", "reunion", "finding", "recovers"),
    "cooperation": ("together", "friends", "share"),
}

def plot_signature(story):
    scenes = story.get("scenes", [])
    beats = [str(scene.get("narration", "")).lower() for scene in scenes]
    roles = []
    for beat in beats:
        words = set(re.findall(r"[a-z]+", beat))
        roles.append(tuple(sorted(role for role, cues in PLOT_CUES.items()
                                  if any(cue in words for cue in cues))))
    return tuple(roles)

def plot_repetition(a, b):
    left, right = plot_signature(a), plot_signature(b)
    if not left or not right or len(left) != len(right):
        return False
    return all(x == y for x, y in zip(left, right)) and any(left)
