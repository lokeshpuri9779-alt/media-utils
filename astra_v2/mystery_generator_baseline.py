"""Frozen pre-PR294 mystery generator, used only for controlled comparison."""
import hashlib
import json
import os
from pathlib import Path

ACTORS = (
    ("a lighthouse keeper", "keeper"), ("a curious fox", "fox"),
    ("a repair robot", "robot"), ("a young astronomer", "astronomer"),
    ("a river otter", "otter"), ("a retired cartographer", "cartographer"),
    ("a clockmaker", "clockmaker"), ("a storm chaser", "storm chaser"),
)
SETTINGS = (
    ("a flooded village", "village"), ("a silent observatory", "observatory"),
    ("an abandoned railway", "railway"), ("a mountain garden", "garden"),
    ("a coastal library", "library"), ("a floating market", "market"),
    ("a desert greenhouse", "greenhouse"), ("an underground museum", "museum"),
)
MYSTERIES = (
    ("the warning bell rang beneath the lake", "a bell-shaped sonar echo", "bell"),
    ("every bridge light blinked in a different rhythm", "a pattern hidden in the wiring", "bridge"),
    ("the waterwheel turned only at midnight", "warm water flowing uphill", "waterwheel"),
    ("the signal tower sent messages to an empty sky", "a mirror reflecting a distant beacon", "signal"),
    ("the town's oldest map changed each morning", "new streets etched into a stone tile", "map"),
    ("all the shadows pointed toward one locked door", "a clockwork shadow moving against the sun", "door"),
    ("the stars vanished above a single rooftop", "a lens hidden in a broken telescope", "telescope"),
    ("a river flowed backward for exactly one minute", "a gate buried under the riverbed", "river"),
    ("the museum's smallest statue changed position nightly", "tiny wet footprints beside its case", "statue"),
    ("the orchard echoed words nobody had spoken", "a repeating distress call in the wind", "signal"),
    ("the lighthouse beam stopped before reaching the sea", "a jammed brass lens mechanism", "lighthouse"),
    ("fresh snow appeared inside a sealed room", "a cold draft from a forgotten tunnel", "snow"),
)
STAKES = (
    "before the evacuation bell sent everyone away",
    "before the last ferry left the harbor",
    "before the mountain pass closed for winter",
    "before the town's water supply ran dry",
    "before the annual night market began",
    "before sunrise erased the only clue",
)
DISCOVERIES = (
    "an overlooked maintenance log", "a melody remembered by an elderly neighbor",
    "a map drawn on the back of a family photograph", "a sequence of lights from a passing train",
    "a small mechanical part lodged beneath the floor", "a message carried by migrating birds",
    "a set of tide marks on the oldest wall", "a constellation reflected in a puddle",
    "a child's drawing that matched the broken machine", "a trail of warm stones beneath the snow",
)
REVERSALS = (
    "the apparent sabotage was actually an emergency signal",
    "the missing object had been protecting the town from a larger danger",
    "the machine was working correctly but responding to a hidden second control",
    "the supposed intruder was trying to return something that had been lost",
    "the strange phenomenon was caused by two systems that had fallen out of sync",
    "the clue pointed away from the obvious culprit and toward an overlooked helper",
    "the warning described tomorrow's weather rather than today's",
    "the locked room was hiding a safe route, not a stolen treasure",
)
RESOLUTIONS = (
    "repaired the mechanism and taught the neighbors how to maintain it",
    "sent a clear signal that guided the missing travelers home",
    "opened the hidden channel and restored the town's water",
    "reunited the separated team and returned the lost object",
    "redirected the danger toward an empty field and kept the village safe",
    "restored the night lights and reopened the route before dawn",
    "shared the discovery so the whole community could solve the problem together",
    "left a reliable warning system for the next generation",
)
EMOTIONAL_TURNS = (
    "pride gave way to doubt before trust returned",
    "fear turned into curiosity when the clue finally made sense",
    "a lonely task became a shared effort",
    "an old disagreement was resolved by a small act of kindness",
    "the hero learned that asking for help was the missing step",
    "a seemingly useless object proved essential",
)
VISUALS = ("bell", "bridge", "waterwheel", "signal", "map", "door", "telescope", "river",
           "statue", "lighthouse", "snow", "clock", "lantern", "ship", "garden", "book")
INVESTIGATION_METHODS = (
    "tested the pattern against a hand-drawn timeline",
    "reconstructed the mechanism from its worn parts",
    "compared witness accounts taken separately",
    "tracked the signal across three locations",
    "built a small safe model to test the theory",
    "checked the clue against weather and tide records",
    "followed the sound to its physical source",
    "mapped which events happened before each failure",
)
OBSTACLES = (
    "a sudden power cut interrupted the first test",
    "two witnesses remembered the event differently",
    "the clue was damaged by rain before it could be copied",
    "the safest route was blocked by a fallen tree",
    "the first explanation failed a simple repeat test",
    "a ticking timer left only minutes to compare the evidence",
    "the team had to work without disturbing nesting animals",
    "the useful part was hidden inside an ordinary object",
)
CONSEQUENCES = (
    "and prevented the next scheduled outage",
    "while keeping the evacuation route open",
    "without wasting the town limited supplies",
    "and made the result easy for children to verify",
    "before the weather changed again",
    "while protecting the fragile original clue",
    "and left a practical check for future caretakers",
    "without blaming anyone before the evidence was clear",
)


def _pick(index, values, stride):
    return values[(index // stride) % len(values)]


def legacy_proposal(index):
    """Create a deterministic four-beat candidate from independent plot dimensions."""
    if not isinstance(index, int) or isinstance(index, bool) or index < 0:
        raise ValueError("Invalid proposal index")
    # Stagger small, co-prime-ish strides so all dimensions evolve early,
    # not only after thousands of candidates; the full product remains large.
    actor, role = _pick(index, ACTORS, 1)
    setting, setting_visual = _pick(index, SETTINGS, 7)
    mystery, clue, visual = _pick(index, MYSTERIES, 13)
    stakes = _pick(index, STAKES, 19)
    discovery = _pick(index, DISCOVERIES, 23)
    reversal = _pick(index, REVERSALS, 31)
    resolution = _pick(index, RESOLUTIONS, 37)
    emotional = _pick(index, EMOTIONAL_TURNS, 43)
    method = _pick(index, INVESTIGATION_METHODS, 47)
    obstacle = _pick(index, OBSTACLES, 53)
    consequence = _pick(index, CONSEQUENCES, 59)
    # The dimensions rotate at different strides; this produces a large
    # deterministic combination space without claiming every draft is unique.
    # Use compact, searchable story titles rather than generic inventory labels.
    title = f"The {visual.capitalize()} Mystery of the {setting.split()[-1].capitalize()}"
    beats = (
        ("reveal", f"As the {role} in {setting}, {actor} needed to understand why {mystery}, {stakes}. If the cause stayed hidden, the neighbors would not know which route or system was safe to use.", visual),
        ("build", f"Instead of guessing, {actor} compared {clue} with {discovery}; {emotional}. {method}, but {obstacle}. The details matched the timing of the first warning, giving the investigation a testable explanation rather than another suspicion.", "book"),
        ("twist", f"The comparison showed that {reversal}. This explained the original mystery rather than introducing a new one. {actor} checked the clue again and found that it fit the evidence gathered at the start.", clue if clue in VISUALS else "signal"),
        ("payoff", f"With the cause understood, {actor} {resolution}. The community saw how the evidence led to the solution {consequence}. The team recorded what they learned so the same problem could be recognized earlier next time.", _pick(index, VISUALS, 3)),
    )
    # Reserve distinct, story-relevant visual keys across the four beats.
    # This fixes avoidable visual repetition without changing narration or
    # treating these unreviewed proposals as publishable.
    visual_keys = [beat[2] for beat in beats]
    if len(set(visual_keys)) < 3:
        replacement = next(
            (key for key in (setting_visual, "lantern", "clock", "garden")
             if key not in visual_keys), None
        )
        if replacement is not None:
            beats = beats[:3] + ((beats[3][0], beats[3][1], replacement),)
    fingerprint_text = " ".join(beat[1] for beat in beats).casefold()
    return {
        "content_id": "astra-proposal-" + hashlib.sha256(f"proposal-{index}".encode()).hexdigest()[:20],
        "title": title,
        "kind": "unreviewed_causal_draft",
        "production_ready": False,
        "proposal_index": index,
        "plot_fingerprint": hashlib.sha256(fingerprint_text.encode()).hexdigest(),
        "story_beats": [
            {"story_beat": role_name, "speech": speech, "visual": visual_name}
            for role_name, speech, visual_name in beats
        ],
    }



