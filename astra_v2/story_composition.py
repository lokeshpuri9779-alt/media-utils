"""Rule-based, offline five-beat story composition; not generative AI."""
import hashlib

# Each conflict has a matching attempt, discovery and resolution.
# Deterministic variants preserve causal continuity without claiming AI generation.
SCENARIOS = (
    ("a missing {prop}", "searches for the {prop}", "the {prop} behind a shelf",
     "returns the {prop} to its owner", "Everyone celebrates the reunion."),
    ("a mysterious {prop}", "examines the {prop}", "a clue hidden beside the {prop}",
     "uses the {prop} to solve the mystery", "The friends share their discovery."),
    ("a broken {prop}", "examines the damaged {prop}", "the loose part inside the {prop}",
     "repairs the {prop} together", "The friends celebrate the successful repair."),
    ("a runaway {prop}", "chases the {prop}", "the {prop} beside a secret passage",
     "carries the {prop} safely home", "Everyone celebrates the rescue."),
    ("a misplaced {prop}", "follows clues to the {prop}", "the {prop} near a helpful stranger",
     "returns the {prop} to its owner", "The friends celebrate finding its owner."),
)


def compose(template, seed, episode):
    """Produce a deterministic five-beat story with a matching resolution."""
    prop = template["prop"].replace("_", " ")
    first, second = template["cast"]
    key = hashlib.sha256(f"{seed}|{episode}|{template['title']}".encode()).digest()
    scenario = SCENARIOS[key[0] % len(SCENARIOS)]
    values = {"prop": prop}
    setup, attempt, discovery, resolution, aftermath = (part.format(**values) for part in scenario)
    return (
        f"The {first} notices {setup}.",
        f"The {second} {attempt}.",
        f"Together they discover {discovery}.",
        f"The {first} {resolution}.",
        aftermath,
    )


def action_for_beat(index, narration):
    """Map story events to supported procedural action cues."""
    text = narration.lower()
    if index == 0:
        return "approach"
    if index == 4:
        return "celebrate"
    if any(word in text for word in ("chases", "races", "runaway", "rushes")):
        return "run"
    if "repairs" in text or "repair" in text:
        return "repair"
    if any(word in text for word in ("returns", "carries", "lifts", "uses")):
        return "carry"
    if any(word in text for word in ("discovers", "clue", "notices", "examines")):
        return "point"
    if index == 4 or any(word in text for word in ("celebrates", "applause")):
        return "celebrate"
    if any(word in text for word in ("surprise", "mysterious")):
        return "react"
    return ("walk", "point", "react", "carry", "celebrate")[index % 5]

