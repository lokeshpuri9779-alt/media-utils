"""Build deterministic previsualization shot packets for ASTRA reference stories.

This is an offline, stdlib-only *planning* tool. It neither renders frames nor
proves semantic/visual fidelity. All shot directions are explicitly authored
metadata attached to already validated assistant-drafted scene references.
No model, network, publishing, approval, or production dependencies.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from tools.astra_offline_reference_benchmark import (
    REFERENCE_CASES, STAGES, validate_reference,
)

VISUAL_STYLE = "review-only 3D animated previsualization; nonphotoreal draft"
SHOT_TYPES = {"wide", "medium", "close"}
BLUEPRINTS = {
    "glasshouse-sunshade": {
        "character_id": "mina_beetle",
        "character_anchor": "Mina: small jade-green beetle with two copper antenna tips",
        "location_anchor": "timber-and-glass greenhouse, three seedling benches and a pulley above them",
        "assets": [
            "canvas_shade", "pulley", "thin_cord", "seedling_trays",
            "braided_rope", "wooden_frame",
        ],
        "shots": [
            {"stage": "setup", "shot_type": "wide",
             "action": "Mina notices curled seedlings under sunlight and points at a jammed overhead shade pulley",
             "motion": "slow approach toward shadowless planting trays",
             "focus_state": "pulley_diagnosed",
             "props": ["canvas_shade", "pulley", "seedling_trays"]},
            {"stage": "attempt", "shot_type": "medium",
             "action": "Mina loops thin cord over the pulley and pulls the shade halfway across the seedlings",
             "motion": "show the cord tightening and canvas tracking sideways",
             "focus_state": "shade_partly_drawn",
             "props": ["thin_cord", "pulley", "canvas_shade"]},
            {"stage": "setback", "shot_type": "close",
             "action": "A gust snaps the thin cord and the canvas slides back into open sunlight",
             "motion": "brief cord snap followed by a quick shade recoil",
             "focus_state": "temporary_cord_snapped",
             "props": ["thin_cord", "canvas_shade", "seedling_trays"]},
            {"stage": "payoff", "shot_type": "medium",
             "action": "Mina threads a thick braided rope through the pulley, pulls the shade fully across, and knots it to the frame",
             "motion": "canvas settles; moving shade covers every planting tray",
             "focus_state": "shade_secured",
             "props": ["braided_rope", "pulley", "canvas_shade", "seedling_trays", "wooden_frame"]},
        ],
    },
    "footbridge-ducklings": {
        "character_id": "beaver_builder",
        "character_anchor": "brown beaver with a wide flat tail, three tiny yellow ducklings",
        "location_anchor": "flooded riverbank with two weathered bridge posts beside a narrow island",
        "assets": [
            "bridge_posts", "loose_plank", "flat_stone", "reed_rope",
            "river_current", "river_island",
        ],
        "shots": [
            {"stage": "setup", "shot_type": "wide",
             "action": "Beaver sees three ducklings stranded across a gap in the flooded footbridge",
             "motion": "river currents sweep past the missing center plank",
             "focus_state": "crossing_needed",
             "props": ["bridge_posts", "river_island", "river_current"]},
            {"stage": "attempt", "shot_type": "medium",
             "action": "Beaver drags a plank into the gap and pins one end with a flat stone",
             "motion": "plank flexes when beaver taps its loose end",
             "focus_state": "plank_loosely_fitted",
             "props": ["loose_plank", "bridge_posts", "flat_stone"]},
            {"stage": "setback", "shot_type": "close",
             "action": "Floodwater dislodges the stone, flips the plank into the shallows, and beaver retrieves it",
             "motion": "water surges once; plank slips toward a reed bed",
             "focus_state": "plank_washed_out",
             "props": ["flat_stone", "loose_plank", "river_current"]},
            {"stage": "payoff", "shot_type": "wide",
             "action": "Beaver lashes the retrieved plank to both bridge posts and ducklings cross the secure bridge",
             "motion": "three ducklings walk in sequence onto the safe bank",
             "focus_state": "bridge_secure",
             "props": ["loose_plank", "bridge_posts", "reed_rope"]},
        ],
    },
    "moon-mirror-garden": {
        "character_id": "moth_keeper",
        "character_anchor": "small twilight-purple moth keeper wearing a plain linen vest",
        "location_anchor": "urban rooftop garden, metal moon mirror, water tank and night-flower beds",
        "assets": [
            "clockwork_mirror", "brass_handle", "holding_pin", "metal_clip",
            "night_flowers", "moonlight",
        ],
        "shots": [
            {"stage": "setup", "shot_type": "wide",
             "action": "Moth keeper notices closed night flowers while a misaligned mirror illuminates a brick wall",
             "motion": "camera reveals an unlit flower bed under the rooftop mirror",
             "focus_state": "mirror_fault_located",
             "props": ["clockwork_mirror", "night_flowers", "moonlight"]},
            {"stage": "attempt", "shot_type": "medium",
             "action": "Keeper turns the brass handle to aim a narrow moonlit patch at the flower bed",
             "motion": "moonlight spot tracks across petals and pauses",
             "focus_state": "temporary_alignment",
             "props": ["clockwork_mirror", "brass_handle", "moonlight", "night_flowers"]},
            {"stage": "setback", "shot_type": "close",
             "action": "Wind breaks the holding pin and the mirror swings away from the flowers",
             "motion": "holding pin snaps; bright patch slides from the bed",
             "focus_state": "pin_broken",
             "props": ["holding_pin", "clockwork_mirror", "night_flowers"]},
            {"stage": "payoff", "shot_type": "medium",
             "action": "Keeper replaces the pin with a metal clip, locks the mirror, and flowers open in the restored moonlight",
             "motion": "mirror holds position as petals open and moths return",
             "focus_state": "mirror_secured",
             "props": ["metal_clip", "clockwork_mirror", "moonlight", "night_flowers"]},
        ],
    },
}


def _json_sha(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def build_packet(cases: list[dict] | None = None,
                 blueprints: dict | None = None) -> dict:
    """Create shot-card previews only after validating causal event ledgers."""
    cases = REFERENCE_CASES if cases is None else cases
    blueprints = BLUEPRINTS if blueprints is None else blueprints
    if not isinstance(cases, list) or not cases:
        raise ValueError("reference stories missing")
    case_ids = [case.get("case_id") for case in cases if isinstance(case, dict)]
    if len(case_ids) != len(cases) or len(set(case_ids)) != len(cases):
        raise ValueError("missing or duplicate case id")
    if not isinstance(blueprints, dict) or set(blueprints) != set(case_ids):
        raise ValueError("shot blueprints must match reference cases exactly")
    packets = []
    for case in cases:
        ledger = validate_reference(case)
        plan = blueprints[case["case_id"]]
        if not isinstance(plan, dict) or set(plan) != {
            "character_id", "character_anchor", "location_anchor", "assets", "shots"
        }:
            raise ValueError("unknown or missing visual continuity plan fields")
        if not isinstance(plan["character_id"], str) or not plan["character_id"].strip():
            raise ValueError("missing character id")
        for field in ("character_anchor", "location_anchor"):
            text = plan[field]
            if not isinstance(text, str) or not 20 <= len(text) <= 220:
                raise ValueError(f"invalid continuity anchor: {field}")
        assets, shots = plan["assets"], plan["shots"]
        if not isinstance(assets, list) or not 3 <= len(assets) <= 16 or any(
            not isinstance(v, str) or not v for v in assets
        ) or len(set(assets)) != len(assets):
            raise ValueError("invalid or repeated asset catalog")
        if not isinstance(shots, list) or len(shots) != len(STAGES):
            raise ValueError("expected exactly four storyboard shots")
        cards = []
        last_after = None
        for stage, visual, scene, transition in zip(
            STAGES, shots, case["scenes"], ledger["sequence"]
        ):
            if not isinstance(visual, dict) or set(visual) != {
                "stage", "shot_type", "action", "motion", "focus_state", "props"
            } or visual["stage"] != stage:
                raise ValueError("shot stage order or fields invalid")
            if visual["shot_type"] not in SHOT_TYPES:
                raise ValueError("unsupported shot framing")
            for name in ("action", "motion"):
                value = visual[name]
                if not isinstance(value, str) or not 30 <= len(value) <= 240:
                    raise ValueError(f"missing or unbounded {stage} {name}")
            props = visual["props"]
            if not isinstance(props, list) or not props or any(
                not isinstance(prop, str) for prop in props
            ) or len(set(props)) != len(props) or not set(props) <= set(assets):
                raise ValueError(f"{stage}: undeclared or duplicate visual prop")
            if visual["focus_state"] not in transition["added"]:
                raise ValueError(f"{stage}: focus state is not actually created")
            if last_after is not None and transition["before"] != last_after:
                raise ValueError(f"{stage}: scene state discontinuity")
            last_after = transition["after"]
            cards.append({
                "stage": stage,
                "shot_type": visual["shot_type"],
                "character_id": plan["character_id"],
                "character_anchor": plan["character_anchor"],
                "location_anchor": plan["location_anchor"],
                "visual_style": VISUAL_STYLE,
                "visible_action": visual["action"],
                "motion_direction": visual["motion"],
                "source_beat": scene["beat"],
                "focus_state": visual["focus_state"],
                "props": props,
                "before_state": transition["before"],
                "after_state": transition["after"],
                "asset_verification": "not_verified",
                "frame_generation_executed": False,
                "manual_visual_review_required": True,
            })
        if not set(case["required_end_state"]) <= set(last_after):
            raise ValueError("storyboard did not reach required terminal state")
        if set(last_after) & set(case["forbidden_end_state"]):
            raise ValueError("storyboard left forbidden state")
        packets.append({
            "case_id": case["case_id"],
            "theme": case["theme"],
            "title": case["title"],
            "story_digest": _json_sha(case),
            "character_id": plan["character_id"],
            "assets": assets,
            "shot_count": len(cards),
            "shots": cards,
            "event_state_contract_valid": True,
            "story_visual_semantics": "not_verified",
            "source_status": "assistant_drafted_reference_not_independently_reviewed",
            "approved": False, "production_ready": False, "published": False,
        })
    return {
        "experiment": "astra-offline-storyboards-v1",
        "reference_count": len(packets),
        "total_shots": sum(p["shot_count"] for p in packets),
        "packets": packets,
        "real_model_inference_executed": False,
        "frames_rendered": False,
        "semantic_fidelity": "not_verified",
        "manual_editorial_and_visual_review_required": True,
        "replaces_astra_main": False,
        "approved": False, "production_ready": False, "published": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=Path("artifacts/offline-storyboards/packet.json"))
    args = parser.parse_args()
    report = build_packet()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps({
        "experiment": report["experiment"],
        "reference_count": report["reference_count"],
        "total_shots": report["total_shots"],
        "frames_rendered": False, "approved": False,
        "production_ready": False, "published": False,
    }))


if __name__ == "__main__":
    main()
