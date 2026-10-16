"""Persistent, compositional proposal generation; proposals are never auto-approved."""
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


def proposal(index):
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



def _backfill_story_title(story):
    """Replace legacy inventory labels with titles derived from the story content."""
    title = str(story.get("title") or "").strip()
    if title and not title.casefold().startswith(("unreviewed story proposal", "story proposal ")):
        return title
    beats = story.get("story_beats") or []
    first = beats[0] if beats and isinstance(beats[0], dict) else {}
    visual = str(first.get("visual") or "curious").replace("_", " ").strip().title()
    speech = str(first.get("speech") or "")
    import re
    match = re.search(r"\bin (?:a|an|the) ([a-z][a-z -]{2,45}?)(?:,| needed to| was| would)", speech, re.IGNORECASE)
    setting = match.group(1).strip().title() if match else "Hidden World"
    return f"The {visual} Mystery of {setting}"


def _backfill_legacy_titles(proposals):
    changed = 0
    for story in proposals:
        if not isinstance(story, dict):
            continue
        title = _backfill_story_title(story)
        if title != story.get("title"):
            story["title"] = title
            changed += 1
    return changed


def replenish(path, count=24, history=()):
    """Persist novel proposals atomically; never promote or publish them."""
    if not 1 <= count <= 100:
        raise ValueError("Proposal batch size out of range")
    from astra_v2.shorts_novelty import is_near_duplicate
    from astra_v2.publication_quality import publication_rejection
    target = Path(path)
    if target.exists():
        state = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(state, dict) or not isinstance(state.get("proposals"), list):
            raise ValueError("Invalid proposal ledger")
    else:
        state = {"next_index": 0, "proposals": []}
    _backfill_legacy_titles(state["proposals"])
    prior = list(history) + state["proposals"]
    next_index = int(state.get("next_index", 0))
    added = []
    for _ in range(count * 200):
        if len(added) >= count:
            break
        if next_index % 2:
            from astra_v2.genre_story_supply import genre_proposal
            candidate = genre_proposal(next_index)
        else:
            candidate = proposal(next_index)
        next_index += 1
        if not is_near_duplicate(candidate, prior):
            if publication_rejection(candidate) != "unreviewed_causal_draft":
                raise ValueError("Proposal unexpectedly bypassed or failed publication isolation")
            added.append(candidate)
            prior.append(candidate)
    # Track the real acceptance rate rather than assuming every generated idea is usable.
    attempts = next_index - int(state.get("next_index", 0))
    acceptance_rate = round(len(added) / attempts, 4) if attempts else 0.0
    from collections import Counter
    recent = (state["proposals"] + added)[-500:]
    genres = Counter(str(item.get("genre", "mystery")) for item in recent if isinstance(item, dict))
    structures = Counter(str(item.get("plot_structure", "legacy")) for item in recent if isinstance(item, dict))
    pairs = Counter(
        (str(item.get("premise_id")), str(item.get("outcome_id")))
        for item in recent
        if isinstance(item, dict) and item.get("premise_id") and item.get("outcome_id")
    )
    diversity = {
        "window": len(recent),
        "genre_counts": dict(sorted(genres.items())),
        "structure_counts": dict(sorted(structures.items())),
        "unique_structural_pairs": len(pairs),
        "repeated_structural_pairs": sum(n - 1 for n in pairs.values() if n > 1),
    }
    state["supply_health"] = {
        "requested": count,
        "accepted": len(added),
        "attempted": attempts,
        "acceptance_rate": acceptance_rate,
        "exhaustion_warning": len(added) < count or (attempts >= count * 4),
        "diversity": diversity,
    }
    if state["supply_health"]["exhaustion_warning"]:
        print("ASTRA_STORY_SUPPLY_EXHAUSTION_WARNING=1")
    print(f"ASTRA_STORY_SUPPLY_ACCEPTANCE_RATE={acceptance_rate}")
    state["next_index"] = next_index
    state["proposals"].extend(added)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".tmp")
    temporary.write_text(json.dumps(state, indent=2), encoding="utf-8")
    os.replace(temporary, target)
    return len(added)


if __name__ == "__main__":
    from astra_v2.proposal_history import load_history
    print("ASTRA_NEW_UNREVIEWED_PROPOSALS=" + str(replenish(
        os.getenv("ASTRA_PROPOSAL_LEDGER", "runtime-health/story_proposals.json"),
        count=int(os.getenv("ASTRA_PROPOSAL_BATCH", "24")),
        history=load_history())))
