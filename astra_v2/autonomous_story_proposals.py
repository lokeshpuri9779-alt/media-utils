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


# Different evidence paths require different actions and explanations;
# these are not cosmetic title/character substitutions.
CAUSAL_PATHS = (
    (
        "The first clue contradicted the town's explanation",
        "tested a competing explanation against the original clue",
        "Only the second explanation accounted for both observations",
        "The team documented the rejected explanation so it would not mislead anyone again",
    ),
    (
        "A failed test revealed that an important assumption was wrong",
        "repeated the test under controlled conditions",
        "The repeated result exposed the missing cause",
        "The team added a repeatable check to catch the same failure early",
    ),
    (
        "Two witnesses described incompatible versions of the event",
        "reconstructed the timeline from independent records",
        "The timeline showed how both witnesses had seen different stages of the same event",
        "The team published a shared timeline so future warnings could be interpreted correctly",
    ),
    (
        "A harmless-looking side effect threatened the safest route",
        "traced the side effect backward to the mechanism that triggered it",
        "The traced chain of events identified the hidden trigger",
        "The team isolated the trigger and checked that the safe route stayed open",
    ),
    (
        "The obvious solution would have damaged the only surviving clue",
        "built a reversible test before touching the original evidence",
        "The reversible test revealed the cause without destroying the clue",
        "The team preserved the original evidence for future investigators",
    ),
    (
        "A helper's earlier warning had been dismissed as unrelated",
        "compared the warning with the new physical evidence",
        "The warning predicted the failure more accurately than the first theory",
        "The team included the helper in designing a better early-warning procedure",
    ),
)


# Distinct plot engines: each has a different core problem, intervention, and outcome.
# These are story-level premises, not just investigation phrasing.
PLOT_ENGINES = (
    (
        "A false alarm threatened to split the town into rival rescue teams",
        "tested which warnings were reliable before anyone was sent into danger",
        "The alarm had been triggered by a harmless echo, not an approaching disaster",
        "published a verified warning protocol and reunited the rescue teams",
    ),
    (
        "A vital delivery disappeared between two checkpoints",
        "reconstructed custody of the delivery and found a mistaken handoff",
        "The supposed theft was a routing error made during an emergency",
        "returned the delivery and introduced a shared handoff record",
    ),
    (
        "A new machine improved one neighborhood while harming another",
        "measured the unintended effects across both neighborhoods",
        "The machine diverted resources from the people it was meant to help",
        "redesigned the controls to distribute the benefit fairly",
    ),
    (
        "An old promise prevented neighbors from asking for urgent help",
        "found out what each neighbor believed the promise required",
        "Both sides had been protecting the same person without realizing it",
        "negotiated a new agreement and restored cooperation",
    ),
    (
        "An apparent intruder was leaving clues at abandoned buildings",
        "followed the clues without confronting the unknown visitor",
        "The visitor was a lost caretaker marking a safe escape route",
        "guided the caretaker home and preserved the escape markings",
    ),
    (
        "A competition prize vanished just before the final challenge",
        "audited the rules and checked who had access to the prize",
        "The prize had been moved to protect it from a hidden hazard",
        "repaired the unsafe venue and restarted the competition transparently",
    ),
    (
        "A flood barrier protected the village but trapped wildlife upstream",
        "modeled the water flow and traced the animals' blocked passage",
        "A forgotten maintenance gate could protect both homes and wildlife",
        "opened a safe passage and installed a seasonal gate inspection",
    ),
    (
        "An archive's newest records contradicted its oldest map",
        "compared the records with physical landmarks that had survived",
        "The archive had preserved two different eras of the same settlement",
        "created a layered map and reunited families with their missing history",
    ),
    (
        "A shared garden began failing after a well-intended repair",
        "compared soil samples before and after the repair",
        "The new drainage channel was washing nutrients away",
        "rerouted the drainage and helped the gardeners restore the soil",
    ),
    (
        "An emergency broadcast seemed to predict accidents that never happened",
        "compared broadcast timestamps with maintenance records",
        "The warnings were delayed recordings from earlier safety drills",
        "corrected the transmitter clock and documented the drill archive",
    ),
    (
        "A museum exhibit went dark whenever visitors approached",
        "tested the display with different visitor paths and lighting levels",
        "A protective sensor was mistaking reflections for dangerous heat",
        "recalibrated the sensor and kept the fragile exhibit protected",
    ),
    (
        "Two villages claimed ownership of the same ancient bridge",
        "compared historical agreements with the bridge's repair records",
        "Both villages had inherited different maintenance duties, not exclusive ownership",
        "formed a joint repair council and reopened the crossing",
    ),
    (
        "A rescue boat repeatedly returned to the wrong shore",
        "charted the current against the boat's navigation marks",
        "An underwater obstruction had redirected the river after the last storm",
        "marked the safer channel and removed the obstruction carefully",
    ),
    (
        "A school science fair lost power just before judging",
        "isolated the electrical circuits and checked each project's load",
        "A demonstration battery was feeding current backward into the shared circuit",
        "installed isolation switches and restarted the fair safely",
    ),
    (
        "A mountain village's food store emptied faster than deliveries arrived",
        "tracked storage losses and compared the delivery schedule with weather records",
        "A damaged vent was spoiling food rather than anyone stealing it",
        "repaired the vent and introduced a shared inventory check",
    ),
    (
        "A historic clock began sounding the wrong hour during an important festival",
        "observed its mechanism through one full cycle without adjusting it",
        "A replacement gear had the wrong number of teeth",
        "installed the correct gear and preserved the old part as evidence",
    ),
)

# Narrative architectures change the order and agency of the investigation.
# Every arc still resolves its initial problem and remains unreviewed.
NARRATIVE_ARCHITECTURES = (
    (
        "Before acting, the team had to choose between two costly alternatives",
        "A limited trial ruled out the tempting shortcut",
        "The protagonist changed course after the evidence challenged the first plan",
        "The final choice preserved the evidence and earned back the community's trust",
    ),
    (
        "The apparent solution worked briefly, then exposed a deeper consequence",
        "The team stopped the fix and measured the new harm",
        "The second attempt addressed the underlying cause instead of the symptom",
        "The community adopted a safer long-term maintenance plan",
    ),
    (
        "Two allies disagreed about which clue deserved attention",
        "They split the investigation into independent tests",
        "Their separate findings became consistent only when combined",
        "Both allies received credit and agreed to share evidence earlier",
    ),
    (
        "A strict deadline made careful investigation seem impossible",
        "The protagonist negotiated a temporary safe pause",
        "The pause allowed a small test that prevented a larger mistake",
        "The team created an emergency procedure that protects time for verification",
    ),
    (
        "The first witness seemed unreliable but held the only missing detail",
        "The protagonist asked the witness to reconstruct the event without interruption",
        "The missing detail reconciled the conflicting accounts",
        "The witness was invited to help document the corrected record",
    ),
    (
        "The team could rescue one group immediately or protect everyone later",
        "They created a temporary safeguard while testing the permanent solution",
        "The safeguard bought time to resolve the cause without abandoning anyone",
        "The final solution removed the tradeoff and kept the safeguard available",
    ),
    (
        "A trusted tool produced a confident but misleading result",
        "The protagonist verified its output using a different method",
        "The independent measurement uncovered the tool's hidden limitation",
        "The team required independent verification before future critical decisions",
    ),
    (
        "An earlier mistake left the protagonist reluctant to intervene",
        "A friend proposed a reversible action with a clear stopping rule",
        "The cautious trial succeeded because the protagonist acknowledged the old mistake",
        "The protagonist taught others how to test uncertain ideas safely",
    ),
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
    causal_opening, causal_test, causal_reveal, causal_aftermath = _pick(index, CAUSAL_PATHS, 17)
    plot_problem, plot_action, plot_reveal, plot_outcome = _pick(index, PLOT_ENGINES, 11)
    arc_setup, arc_decision, arc_turn, arc_aftermath = _pick(index, NARRATIVE_ARCHITECTURES, 5)
    # The dimensions rotate at different strides; this produces a large
    # deterministic combination space without claiming every draft is unique.
    # Use compact, searchable story titles rather than generic inventory labels.
    title = f"The {visual.capitalize()} Mystery of the {setting.split()[-1].capitalize()}"
    beats = (
        ("reveal", f"As the {role} in {setting}, {actor} needed to understand why {mystery}, {stakes}. {plot_problem}. {arc_setup}. The neighbors needed a trustworthy explanation before taking action.", visual),
        ("build", f"Instead of guessing, {actor} compared {clue} with {discovery}; {emotional}. {causal_opening}. {actor} {causal_test} and {plot_action}. {arc_decision}; {method}, but {obstacle}. The evidence gave the team a testable explanation rather than another suspicion.", "book"),
        ("twist", f"{causal_reveal}: {reversal}. {plot_reveal}. {arc_turn}. This explained the original mystery rather than introducing a new one. The team compared this explanation with the original evidence. {actor} checked the clue again and found that it fit the evidence gathered at the start.", clue if clue in VISUALS else "signal"),
        ("payoff", f"With the cause understood, {actor} {resolution}. The community saw how the evidence led to the solution {consequence}. {causal_aftermath}. Together they {plot_outcome}. {arc_aftermath}.", _pick(index, VISUALS, 3)),
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
    from astra_v2.proposal_novelty_index import NoveltyIndex
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
    novelty_index = NoveltyIndex(prior)
    from astra_v2.semantic_candidate_index import SemanticCandidateIndex
    semantic_index = SemanticCandidateIndex(prior)
    next_index = int(state.get("next_index", 0))
    added = []
    semantic_rejected = 0
    for _ in range(count * 200):
        if len(added) >= count:
            break
        if next_index % 2:
            from astra_v2.genre_story_supply import genre_proposal, balanced_genre_index, balanced_structure_index
            candidate = genre_proposal(
                next_index,
                scenario_index=balanced_genre_index(next_index, prior),
                structure_index=balanced_structure_index(next_index, prior),
            )
        else:
            candidate = proposal(next_index)
        next_index += 1
        if not novelty_index.is_near_duplicate(candidate):
            if semantic_index.match(candidate) is not None:
                semantic_rejected += 1
                continue
            if publication_rejection(candidate) != "unreviewed_causal_draft":
                raise ValueError("Proposal unexpectedly bypassed or failed publication isolation")
            added.append(candidate)
            prior.append(candidate)
            novelty_index.add(candidate)
            semantic_index.add(candidate)
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
        "semantic_duplicates_rejected": semantic_rejected,
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
