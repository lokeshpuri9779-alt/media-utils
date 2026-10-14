"""Rule-based, offline five-beat story composition; not generative AI."""
import hashlib

CONFLICTS = (
    ("a missing {prop}", "searches for {prop}", "a hidden {prop}"),
    ("a mysterious {prop}", "examines {prop}", "an unexpected clue"),
    ("a broken {prop}", "tries to repair {prop}", "a surprising mechanism"),
    ("a runaway {prop}", "chases {prop}", "a secret passage"),
    ("a misplaced {prop}", "follows clues to {prop}", "a helpful stranger"),
)
RESOLUTIONS = (
    ("returns {prop} to its owner", "Everyone celebrates the reunion."),
    ("solves the mystery of {prop}", "The friends share their discovery."),
    ("repairs {prop} together", "The workshop fills with applause."),
    ("finds a new home for {prop}", "They head home as a team."),
    ("uses {prop} to help a neighbor", "A new friendship begins."),
)

def compose(template, seed, episode):
    """Produce coherent setup, attempt, discovery, resolution and aftermath."""
    cast = template["cast"]
    prop = template["prop"].replace("_", " ")
    key = hashlib.sha256(f"{seed}|{episode}|{template['title']}".encode()).digest()
    conflict = CONFLICTS[key[0] % len(CONFLICTS)]
    resolution = RESOLUTIONS[key[1] % len(RESOLUTIONS)]
    first, second = cast
    values = {"prop": prop}
    beats = (
        f"The {first} notices {conflict[0].format(**values)}.",
        f"The {second} {conflict[1].format(**values)}.",
        f"Together they discover {conflict[2].format(**values)}.",
        f"The {first} {resolution[0].format(**values)}.",
        resolution[1],
    )
    return beats


def action_for_beat(index, narration):
    """Map story events to supported procedural action cues."""
    text = narration.lower()
    if index == 0:
        return "approach"
    if any(word in text for word in ("chases", "races", "runaway", "rushes")):
        return "run"
    if any(word in text for word in ("repairs", "returns", "carries", "lifts", "uses")):
        return "carry"
    if any(word in text for word in ("discovers", "clue", "notices", "examines")):
        return "point"
    if index == 4 or any(word in text for word in ("celebrates", "applause")):
        return "celebrate"
    if any(word in text for word in ("surprise", "mysterious")):
        return "react"
    return ("walk", "point", "react", "carry", "celebrate")[index % 5]

