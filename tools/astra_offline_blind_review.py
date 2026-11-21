"""Source-masked, review-only comparison of three same-theme ASTRA stories.

The two local-model texts are taken from pinned regression fixtures documenting
real 0.5B and 1.5B CPU runs. The third is an assistant-drafted reference
written *after* seeing earlier failures. This is NOT a balanced A/B experiment,
true double-blind study, human-authored gold standard, or publisher gate.

No inference, network, payment, automatic scoring, or publication occurs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from tools.astra_offline_reference_benchmark import validate_reference

BENCHMARK = "astra-lighthouse-source-masked-v1"
THEME = "copper robot repairs a storm-damaged lighthouse warning light"
FIELDS = {
    "cause_and_effect": "Does each beat clearly cause or complicate the next?",
    "physical_actions": "Are concrete visible actions depicted rather than intentions?",
    "payoff_resolution": "Is the original warning-light problem visibly resolved?",
    "novelty_and_detail": "Does the story add original, specific development rather than rephrasing a plan?",
    "renderability": "Could the events and props be consistently visualized in four scenes?",
}
SCORE_MIN, SCORE_MAX = 1, 5

# This original reference intentionally follows a different action route
# (reflector -> loose clamp -> replacement dish) than the causal plan used in
# both model runs. Its quality has NOT been independently verified.
ASSISTANT_REFERENCE = {
    "case_id": "lighthouse-reflector",
    "title": "The Copper Robot and the Broken Reflector",
    "theme": "a copper robot repairs a storm-damaged lighthouse warning light",
    "initial_state": [
        "beacon_dark", "ship_at_risk", "reflector_bent",
        "replacement_dish_available", "spare_bolts_available",
    ],
    "required_end_state": ["beacon_visible", "ship_safe"],
    "forbidden_end_state": ["beacon_dark", "ship_at_risk", "temporary_clamp_failed"],
    "scenes": [
        {
            "stage": "setup",
            "beat": (
                "A copper robot watches a cargo vessel approach jagged rocks as "
                "the lighthouse beam vanishes in a squall. Inside the lantern "
                "room, it discovers a bent metal reflector, which throws the "
                "lamp's light into the ceiling instead of across the sea."
            ),
            "requires": ["beacon_dark", "ship_at_risk", "reflector_bent"],
            "adds": ["reflector_fault_located"], "removes": [],
        },
        {
            "stage": "attempt",
            "beat": (
                "The robot opens the brass housing, straightens the reflector "
                "with a wrench and holds it in place using a temporary clamp. "
                "A narrow beam reaches the water for a moment. The robot "
                "tightens the clamp as the tower begins to shake."
            ),
            "requires": ["reflector_fault_located", "reflector_bent"],
            "adds": ["temporary_clamp_fitted", "partial_beam_visible"],
            "removes": ["reflector_bent"],
        },
        {
            "stage": "setback",
            "beat": (
                "A violent gust shakes the housing. The clamp snaps, and the "
                "reflector swings loose again, sending the beam across the "
                "ceiling. The approaching vessel turns toward the reef. "
                "The robot spots a polished spare dish beside a crate of bolts."
            ),
            "requires": ["temporary_clamp_fitted", "partial_beam_visible"],
            "adds": ["temporary_clamp_failed", "spare_dish_located"],
            "removes": ["temporary_clamp_fitted", "partial_beam_visible"],
        },
        {
            "stage": "payoff",
            "beat": (
                "The robot removes the damaged reflector and bolts the spare "
                "dish firmly behind the lamp. The lighthouse beam cuts across "
                "the black water and illuminates the reef. The cargo vessel "
                "changes course into open sea while the replacement stays "
                "steady through the wind."
            ),
            "requires": [
                "spare_dish_located", "temporary_clamp_failed",
                "replacement_dish_available", "spare_bolts_available",
            ],
            "adds": ["beacon_visible", "ship_safe"],
            "removes": ["beacon_dark", "ship_at_risk", "temporary_clamp_failed"],
        },
    ],
}

ARCHIVED_MODEL_TEXTS = [
    {
        "source": "qwen2.5-0.5b-instruct-q4_k_m",
        "source_type": "regression_fixture_real_cpu_run",
        "run_url": "https://github.com/lokeshpuri9779-alt/media-utils/actions/runs/41660334335",
        "title": "The Copper Robot's Repair Mission",
        "story_beats": [
            "A copper robot, tasked with repairing a lighthouse warning signal, finds itself caught in a storm.",
            "The robot must navigate through the stormy waters and over the towering lighthouse, where the warning signal is flashing.",
            "As the robot tries to navigate through the storm, it realizes that the lighthouse is not just a warning signal, but a lifeline for the town.",
            "The copper robot must use its skills and wit to navigate the stormy waters and find a way to repair the lighthouse warning signal before it goes off.",
        ],
    },
    {
        "source": "qwen2.5-1.5b-instruct-q4_k_m",
        "source_type": "regression_fixture_real_cpu_run",
        "run_url": "https://github.com/lokeshpuri9779-alt/media-utils/actions/runs/41707761872",
        "title": "The Copper Robot's Stormy Repair",
        "story_beats": [
            "At a stormy lighthouse, a copper robot notices the warning lamp go dark as a cargo ship approaches an unlit reef.",
            "The robot climbs inside the lighthouse and finds a corroded switch; it attempts to clean the connector.",
            "Lightning strikes, cutting power and knocking away the spare battery; the signal remains dark as the ship approaches the dangerous rocks.",
            "The robot splices its own power cable across the broken switch; the beacon beam shines again, and the ship turns safely away.",
        ],
    },
]


def _sha_bytes(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_packets() -> tuple[dict, dict, dict]:
    """Separate review text, provenance, and human-input template."""
    ledger = validate_reference(ASSISTANT_REFERENCE)
    if not ledger["terminal_conditions_met"]:
        raise ValueError("reference ledger must close its declared state")
    sources = [
        {
            "source": "assistant_drafted_posthoc_reference",
            "source_type": "assistant_reference_not_independently_editorially_verified",
            "run_url": None,
            "title": ASSISTANT_REFERENCE["title"],
            "story_beats": [scene["beat"] for scene in ASSISTANT_REFERENCE["scenes"]],
        },
        *ARCHIVED_MODEL_TEXTS,
    ]
    ids = set()
    blind_cases, provenance = [], []
    for case in sources:
        title, beats = case["title"], case["story_beats"]
        if not isinstance(title, str) or not isinstance(beats, list) or len(beats) != 4:
            raise ValueError("invalid comparison story")
        if any(not isinstance(beat, str) or len(beat.strip()) < 25 for beat in beats):
            raise ValueError("empty or invalid comparison beat")
        digest = _sha_bytes({"title": title, "story_beats": beats})
        rid = "case-" + digest[:14]
        if rid in ids:
            raise ValueError("duplicate blind review ID")
        ids.add(rid)
        blind_cases.append({
            "review_id": rid, "title": title, "story_beats": beats,
        })
        provenance.append({
            "review_id": rid, "source": case["source"],
            "source_type": case["source_type"], "run_url": case["run_url"],
            "text_sha256": digest,
        })
    blind_cases.sort(key=lambda item: item["review_id"])
    provenance.sort(key=lambda item: item["review_id"])
    blind = {
        "benchmark": BENCHMARK,
        "theme": THEME,
        "design": "source_masked_posthoc_same_theme",
        "source_labels_hidden_from_review_sheet": True,
        "genuine_double_blind": False,
        "fully_controlled_model_comparison": False,
        "caveat": (
            "The reference was drafted after earlier model failures, "
            "and input prompts differ. Ratings cannot establish a fair "
            "model comparison or publication suitability."
        ),
        "rubric": FIELDS,
        "score_range": [SCORE_MIN, SCORE_MAX],
        "cases": blind_cases,
        "automated_quality_scores": None,
        "human_evaluation_status": "not_submitted",
        "approved": False, "production_ready": False, "published": False,
    }
    sheet = {
        "benchmark": BENCHMARK,
        "blind_packet_sha256": _sha_bytes(blind),
        "reviewer": "",
        "reviews": [
            {"review_id": case["review_id"],
             "scores": {key: None for key in FIELDS},
             "evidence": {key: "" for key in FIELDS}}
            for case in blind_cases
        ],
    }
    key = {
        "benchmark": BENCHMARK,
        "blind_packet_sha256": _sha_bytes(blind),
        "UNBLIND_ONLY_AFTER_SCORING": True,
        "source_verification": (
            "Source labels rely on pinned regression test fixture text "
            "and the linked GitHub CPU-run evidence."
        ),
        "assistant_reference_not_human_ground_truth": True,
        "provenance": provenance,
        "approved": False, "production_ready": False, "published": False,
    }
    return blind, sheet, key


def validate_human_ratings(ratings: dict, blind: dict) -> dict:
    """Validate supplied ratings, not certify reviewer identity or quality."""
    if not isinstance(ratings, dict) or set(ratings) != {
        "benchmark", "blind_packet_sha256", "reviewer", "reviews",
    }:
        raise ValueError("ratings file has incorrect keys")
    if ratings["benchmark"] != BENCHMARK:
        raise ValueError("unexpected benchmark")
    if ratings["blind_packet_sha256"] != _sha_bytes(blind):
        raise ValueError("ratings refer to a different blind packet")
    reviewer = ratings["reviewer"]
    if not isinstance(reviewer, str) or not 2 <= len(reviewer.strip()) <= 90:
        raise ValueError("reviewer identifier missing or too long")
    expected = {case["review_id"] for case in blind["cases"]}
    entries = ratings["reviews"]
    if not isinstance(entries, list) or len(entries) != len(expected):
        raise ValueError("ratings must cover every case exactly once")
    observed = set()
    results = []
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {
            "review_id", "scores", "evidence",
        }:
            raise ValueError("invalid rating entry")
        cid = entry["review_id"]
        if not isinstance(cid, str) or cid not in expected or cid in observed:
            raise ValueError("unknown or duplicate rated case")
        observed.add(cid)
        scores, evidence = entry["scores"], entry["evidence"]
        if not isinstance(scores, dict) or set(scores) != set(FIELDS):
            raise ValueError("incomplete score rubric")
        if not isinstance(evidence, dict) or set(evidence) != set(FIELDS):
            raise ValueError("incomplete evidence rubric")
        for key in FIELDS:
            value, note = scores[key], evidence[key]
            if type(value) is not int or not SCORE_MIN <= value <= SCORE_MAX:
                raise ValueError(f"invalid score for {key}")
            if not isinstance(note, str) or not 12 <= len(note.strip()) <= 500:
                raise ValueError(f"missing or unbounded evidence for {key}")
        results.append({
            "review_id": cid,
            "mean_score": round(sum(scores.values()) / len(FIELDS), 2),
            "scores": scores,
        })
    if observed != expected:
        raise ValueError("missing review case")
    return {
        "benchmark": BENCHMARK,
        "reviewer_supplied_scoring_not_verified": True,
        "human_review_identity_verified": False,
        "review_complete": True,
        "results": sorted(results, key=lambda x: x["review_id"]),
        "comparison_limitations": blind["caveat"],
        "editorial_approval_granted": False,
        "approved": False, "production_ready": False, "published": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path,
                        default=Path("artifacts/offline-blind-story-review"))
    parser.add_argument("--ratings", type=Path, help="Optional human-entered rating JSON")
    args = parser.parse_args()
    blind, sheet, key = build_packets()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, doc in [
        ("blind-review.json", blind), ("rating-template.json", sheet),
        ("source-key.json", key),
    ]:
        (args.output_dir / name).write_text(
            json.dumps(doc, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    if args.ratings is not None:
        supplied = json.loads(args.ratings.read_text(encoding="utf-8"))
        report = validate_human_ratings(supplied, blind)
        (args.output_dir / "review-scores.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps({
        "benchmark": BENCHMARK,
        "cases": len(blind["cases"]),
        "automated_quality_scores": False,
        "ratings_checked": args.ratings is not None,
        "approved": False, "production_ready": False, "published": False,
    }))


if __name__ == "__main__":
    main()
