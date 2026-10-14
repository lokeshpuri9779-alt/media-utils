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
