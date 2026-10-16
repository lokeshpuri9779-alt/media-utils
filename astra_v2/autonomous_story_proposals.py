"""Autonomous *proposal* supply from reviewed narrative parts.

These are unreviewed proposals, never publication-ready. Novelty memory is
persistent; candidates must be editorially approved before entering production.
"""
import hashlib
import json
import os
from pathlib import Path

ACTORS = ("a lighthouse keeper", "a curious fox", "a repair robot", "a young astronomer", "a river otter")
SETTINGS = ("a flooded village", "a silent observatory", "an abandoned railway", "a mountain garden", "a coastal library")
PROBLEMS = (
    ("the warning bell stopped working", "an old copper wire", "restored the warning bell"),
    ("the bridge lights went dark", "a forgotten hand-cranked generator", "lit the bridge again"),
    ("the waterwheel froze", "a hidden warm spring", "freed the waterwheel"),
    ("the signal tower lost power", "a polished mirror", "sent a daylight signal"),
    ("the town map disappeared", "a faded engraving on stone", "recovered the route"),
)


def proposal(index):
    if not isinstance(index, int) or index < 0:
        raise ValueError("Invalid proposal index")
    actor = ACTORS[index % len(ACTORS)]
    setting = SETTINGS[(index // len(ACTORS)) % len(SETTINGS)]
    problem, clue, payoff = PROBLEMS[(index // (len(ACTORS) * len(SETTINGS))) % len(PROBLEMS)]
    key = f"proposal-{index}"
    cycle = index // (len(ACTORS) * len(SETTINGS) * len(PROBLEMS))
    # Vary the causal setting across cycles without asserting editorial novelty.
    occasion = ("annual festival", "winter market", "morning evacuation",
                "village reunion", "spring parade")[cycle % 5]
    sentences = (
        f"At {setting}, {actor} discovered that {problem} just before the {occasion}.",
        f"The first repair attempt failed, and worried neighbors began preparing to leave before the {occasion}.",
        f"After searching old records, the hero discovered {clue} and organized a careful second attempt for the {occasion}.",
        f"With help from the neighbors, the hero {payoff}, and the {occasion} could finally begin.",
    )
    return {
        "content_id": "astra-proposal-" + hashlib.sha256(key.encode()).hexdigest()[:20],
        "title": f"Unreviewed story proposal {index + 1}",
        "kind": "unreviewed_causal_draft",
        "production_ready": False,
        "plot_fingerprint": hashlib.sha256(" ".join(sentences).casefold().encode()).hexdigest(),
        "story_beats": [
            {"story_beat": role, "speech": speech, "visual": visual}
            for role, speech, visual in zip(
                ("reveal", "build", "twist", "payoff"), sentences,
                ("forest", "door", "book", "signal"))
        ],
    }


def replenish(path, count=24, history=()):
    """Persist novel proposals, not publishable stories, with atomic replace."""
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
    prior = list(history) + state["proposals"]
    next_index = int(state.get("next_index", 0))
    added = []
    for _ in range(count * 200):
        if len(added) >= count:
            break
        candidate = proposal(next_index)
        next_index += 1
        if not is_near_duplicate(candidate, prior):
            assert publication_rejection(candidate) == "unreviewed_causal_draft"
            added.append(candidate)
            prior.append(candidate)
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
        history=load_history())))
