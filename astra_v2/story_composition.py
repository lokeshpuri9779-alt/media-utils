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
    ("an enchanted {prop}", "tests the strange {prop}", "a map appearing on the {prop}",
     "uses the map to guide a traveler", "The traveler waves goodbye."),
    ("a frozen {prop}", "warms the icy {prop}", "a hidden message inside the {prop}",
     "delivers the message before sunrise", "A distant bell rings in thanks."),
    ("a glowing {prop}", "follows the light from the {prop}", "a doorway reflected in the {prop}",
     "opens a passage to the garden", "The garden blooms overnight."),
    ("a singing {prop}", "records the melody of the {prop}", "a rhythm matching the village bells",
     "conducts a midnight concert", "The village wakes to music."),
    ("a shrinking {prop}", "measures the changing {prop}", "a tiny doorway beneath the table",
     "guides an ant colony through the doorway", "The ants build a colorful monument."),
    ("a floating {prop}", "tests why the {prop} rises", "a warm current above the chimney",
     "builds a safe landing platform", "The neighbors cheer from their windows."),
    ("a whispering {prop}", "listens carefully to the {prop}", "a forgotten name in the whisper",
     "reunites two old pen pals", "A handwritten letter arrives at dawn."),
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
        return "celebrate"  # Finale must not repeat a repair mentioned in narration.
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

