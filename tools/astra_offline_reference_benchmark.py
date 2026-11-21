"""Review-only ASTRA story reference set with checkable event-state contracts.

The three stories are independently drafted assistant reference material, NOT
validated human-authored ground truth, generated model output, or publication
candidates. Ledger checks validate declared transitions, not visual or story
semantics. No network, model, production or publication dependencies.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

STAGES = ("setup", "attempt", "setback", "payoff")
STATE = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
CASE_ID = re.compile(r"^[a-z][a-z0-9-]{3,63}$")
SOURCE = "assistant_drafted_reference_not_editorially_verified"

REFERENCE_CASES = [
    {
        "case_id": "glasshouse-sunshade",
        "title": "The Beetle and the Burning Greenhouse",
        "theme": "a greenhouse beetle repairs a jammed sunshade to protect seedlings",
        "initial_state": ["shade_jammed", "seedlings_exposed", "braided_rope_available"],
        "required_end_state": ["shade_secured", "seedlings_shaded"],
        "forbidden_end_state": ["seedlings_exposed", "temporary_cord_snapped"],
        "scenes": [
            {"stage": "setup",
             "beat": "By noon, Mina the beetle sees the greenhouse seedlings curling beneath a jammed canvas sunshade. The pulley hangs crooked, and harsh sunlight reaches every planting tray. She knows the delicate sprouts will dry out unless she moves the shade.",
             "requires": ["shade_jammed"], "adds": ["pulley_diagnosed"], "removes": []},
            {"stage": "attempt",
             "beat": "Mina climbs the wooden frame and loops a thin cord around the loose pulley. She pulls until the canvas covers half the benches, then wedges the cord against a nail. For a moment, the nearest leaves stop wilting.",
             "requires": ["pulley_diagnosed", "shade_jammed"],
             "adds": ["temporary_cord_fixed", "shade_partly_drawn"], "removes": ["shade_jammed"]},
            {"stage": "setback",
             "beat": "A strong gust tears the thin cord from the nail. The canvas whips back, striking the frame and exposing the trays to full sunlight again. Mina searches her tool box and finds a thicker braided rope beneath the spare clips.",
             "requires": ["temporary_cord_fixed", "shade_partly_drawn"],
             "adds": ["temporary_cord_snapped"], "removes": ["temporary_cord_fixed", "shade_partly_drawn"]},
            {"stage": "payoff",
             "beat": "Mina threads the braided rope through the pulley, fastens it with two knots, and pulls the shade across every tray. She secures the rope to the frame. The seedlings rest in shadow as the afternoon sun climbs higher.",
             "requires": ["temporary_cord_snapped", "braided_rope_available"],
             "adds": ["shade_secured", "seedlings_shaded"],
             "removes": ["seedlings_exposed", "temporary_cord_snapped"]},
        ],
    },
    {
        "case_id": "footbridge-ducklings",
        "title": "The Beaver's Last Plank",
        "theme": "a beaver repairs a flood-damaged footbridge for stranded ducklings",
        "initial_state": ["bridge_gap", "ducklings_stranded", "plank_available",
                          "bridge_posts_intact", "reed_rope_available"],
        "required_end_state": ["bridge_secure", "ducklings_safe"],
        "forbidden_end_state": ["ducklings_stranded", "bridge_gap", "plank_washed_out"],
        "scenes": [
            {"stage": "setup",
             "beat": "After rain, a beaver finds three ducklings stranded on an island beside a wooden footbridge. The center plank has floated loose, and the current is too strong for them to paddle across. The beaver points them toward the bridge posts and begins searching for timber.",
             "requires": ["ducklings_stranded", "bridge_gap"],
             "adds": ["crossing_needed"], "removes": []},
            {"stage": "attempt",
             "beat": "The beaver drags a fallen plank from the bank, slides it between the old bridge rails and pins one end beneath a flat stone. The ducklings gather at the edge, but the plank trembles when the beaver taps it with a paw.",
             "requires": ["plank_available", "bridge_gap"],
             "adds": ["plank_loosely_fitted"], "removes": ["plank_available"]},
            {"stage": "setback",
             "beat": "An upstream surge knocks the stone free and flips the unsecured plank into the shallow water. The ducklings retreat while the beaver catches the board against a reed bed. The two bridge posts are still standing, giving the beaver somewhere firmer to anchor it.",
             "requires": ["plank_loosely_fitted", "bridge_posts_intact"],
             "adds": ["plank_recovered", "plank_washed_out"],
             "removes": ["plank_loosely_fitted"]},
            {"stage": "payoff",
             "beat": "The beaver ties the recovered plank to both posts with reed rope and braces the ends with stones. It tests the crossing, then gestures for the ducklings to follow. One by one they walk over the steady bridge to the safe bank.",
             "requires": ["plank_recovered", "reed_rope_available", "bridge_posts_intact"],
             "adds": ["bridge_secure", "ducklings_safe"],
             "removes": ["ducklings_stranded", "bridge_gap", "plank_washed_out"]},
        ],
    },
    {
        "case_id": "moon-mirror-garden",
        "title": "The Moon Mirror on the Roof",
        "theme": "a moth keeper fixes a rooftop moonlight mirror for night flowers",
        "initial_state": ["mirror_misaligned", "flowers_closed", "moths_displaced",
                          "spare_clip_available"],
        "required_end_state": ["mirror_secured", "flowers_open", "moths_returned"],
        "forbidden_end_state": ["mirror_misaligned", "flowers_closed", "pin_broken"],
        "scenes": [
            {"stage": "setup",
             "beat": "On a rooftop at dusk, a small moth keeper notices that the garden's night flowers remain closed. A clockwork mirror that reflects moonlight into the beds is pointing at a brick wall. Without the light, the visiting moths circle the empty roof.",
             "requires": ["mirror_misaligned", "flowers_closed"],
             "adds": ["mirror_fault_located"], "removes": []},
            {"stage": "attempt",
             "beat": "The keeper turns the stiff brass handle and guides the mirror toward the garden. A silver patch crosses the first row of flowers, and their petals begin to loosen. The keeper steadies the handle with a strip of cloth.",
             "requires": ["mirror_fault_located"],
             "adds": ["temporary_alignment"], "removes": []},
            {"stage": "setback",
             "beat": "A sudden wind catches the mirror, snapping its holding pin and swinging the glass away from the beds. Darkness returns, and the moths scatter around the water tank. The keeper spots a spare metal clip beneath the tool shelf.",
             "requires": ["temporary_alignment"],
             "adds": ["pin_broken", "light_lost"], "removes": ["temporary_alignment"]},
            {"stage": "payoff",
             "beat": "The keeper replaces the broken pin with the metal clip, tightens the handle and aims the mirror at the flower beds. Moonlight settles across the petals; they open, and the moths return to feed. The mirror stays fixed through the wind.",
             "requires": ["pin_broken", "spare_clip_available"],
             "adds": ["mirror_secured", "flowers_open", "moths_returned"],
             "removes": ["mirror_misaligned", "flowers_closed", "moths_displaced",
                         "pin_broken", "light_lost"]},
        ],
    },
]


def _names(values: object, label: str, *, nonempty: bool = False) -> list[str]:
    if not isinstance(values, list) or (nonempty and not values):
        raise ValueError(f"{label}: expected a list")
    if any(not isinstance(x, str) or not STATE.fullmatch(x) for x in values):
        raise ValueError(f"{label}: invalid state name")
    if len(set(values)) != len(values):
        raise ValueError(f"{label}: duplicate state name")
    return values


def validate_reference(case: dict) -> dict:
    """Fail closed on continuity defects in declared scene transitions."""
    if not isinstance(case, dict) or set(case) != {
        "case_id", "title", "theme", "initial_state", "required_end_state",
        "forbidden_end_state", "scenes",
    }:
        raise ValueError("reference case requires exact, known keys")
    cid = case["case_id"]
    if not isinstance(cid, str) or not CASE_ID.fullmatch(cid):
        raise ValueError("invalid case id")
    if not isinstance(case["title"], str) or not 8 <= len(case["title"]) <= 100:
        raise ValueError("invalid reference title")
    if not isinstance(case["theme"], str) or not 20 <= len(case["theme"]) <= 150:
        raise ValueError("invalid reference theme")
    initial = set(_names(case["initial_state"], "initial", nonempty=True))
    required = set(_names(case["required_end_state"], "required", nonempty=True))
    forbidden = set(_names(case["forbidden_end_state"], "forbidden"))
    if required & forbidden:
        raise ValueError("contradictory required and forbidden terminal state")
    scenes = case["scenes"]
    if not isinstance(scenes, list) or len(scenes) != 4:
        raise ValueError("expected four scenes")
    state = set(initial)
    history = []
    seen_text = set()
    for stage, scene in zip(STAGES, scenes):
        if not isinstance(scene, dict) or set(scene) != {
            "stage", "beat", "requires", "adds", "removes",
        } or scene["stage"] != stage:
            raise ValueError(f"{stage}: invalid or out-of-order scene")
        beat = scene["beat"]
        if not isinstance(beat, str) or not 25 <= len(beat.split()) <= 60:
            raise ValueError(f"{stage}: reference beat outside 25..60 words")
        if beat.casefold().strip() in seen_text:
            raise ValueError("duplicate reference beat")
        seen_text.add(beat.casefold().strip())
        pre = set(_names(scene["requires"], f"{stage}.requires", nonempty=True))
        adds = set(_names(scene["adds"], f"{stage}.adds", nonempty=True))
        removes = set(_names(scene["removes"], f"{stage}.removes"))
        if pre - state:
            raise ValueError(f"{stage}: unmet preconditions: {sorted(pre - state)}")
        if removes - state:
            raise ValueError(f"{stage}: cannot remove absent state")
        if adds & state:
            raise ValueError(f"{stage}: redundant state additions")
        if adds & removes:
            raise ValueError(f"{stage}: contradictory effects")
        state.difference_update(removes)
        state.update(adds)
        history.append({
            "stage": stage,
            "before": sorted((state - adds) | removes),
            "after": sorted(state),
            "added": sorted(adds),
            "removed": sorted(removes),
        })
    if required - state:
        raise ValueError(f"incomplete ending: missing {sorted(required - state)}")
    if state & forbidden:
        raise ValueError(f"unsafe ending: unresolved {sorted(state & forbidden)}")
    return {
        "case_id": cid, "event_state_contract_valid": True,
        "terminal_conditions_met": True,
        "sequence": history,
        "prose_semantics": "not_verified",
        "visual_quality": "not_verified",
        "human_editorial_review_required": True,
        "approved": False, "production_ready": False, "published": False,
    }


def build_review_packet() -> dict:
    """Produce deterministic, entirely local comparison material."""
    seen = set()
    records = []
    for case in REFERENCE_CASES:
        if case["case_id"] in seen:
            raise ValueError("duplicate benchmark case")
        seen.add(case["case_id"])
        audit = validate_reference(case)
        records.append({
            "case_id": case["case_id"], "source": SOURCE,
            "title": case["title"], "theme": case["theme"],
            "story_beats": [scene["beat"] for scene in case["scenes"]],
            "event_state_audit": audit,
            "editorial_status": "awaiting_independent_human_review",
            "approved": False, "production_ready": False, "published": False,
        })
    if len(records) != 3:
        raise ValueError("expected exactly three reference genres")
    return {
        "benchmark": "astra-offline-story-reference-v1",
        "review_only": True,
        "reference_is_quality_ground_truth": False,
        "replaces_story_factory": False,
        "real_model_inference_executed": False,
        "model_quality_conclusion": "no_new_evidence",
        "human_editorial_review_required": True,
        "evaluation_questions": [
            "Does every attempt change a visible object or character state?",
            "Does the setback undo or complicate the attempted action?",
            "Does the payoff resolve the original problem in observable pixels?",
            "Can each beat be rendered with consistent characters and props?",
            "Is the story genuinely engaging rather than merely well-structured?",
        ],
        "cases": records,
        "approved": False, "production_ready": False, "published": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=Path("artifacts/offline-reference-benchmark/packet.json"))
    args = parser.parse_args()
    packet = build_review_packet()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")
    print(json.dumps({"benchmark": packet["benchmark"],
                      "references": len(packet["cases"]),
                      "human_editorial_review_required": True,
                      "approved": False, "production_ready": False}))


if __name__ == "__main__":
    main()
