"""Negative-control tests for the isolated ASTRA spark-to-beacon image audit.

Uses real, previously rendered PNGs from the current workflow. Replace
selected frames with neighboring frames to simulate missing, stalled, or
mistimed energy transfer. No model is called; no frames are published.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.experimental_causal_visual_audit import (
    OUTPUT, decode_frames, score_frames
)


def evaluate(label, frames, original_report, expected_failed):
    result=score_frames(frames, original_report)
    actual_failed=sorted(name for name, passed in result["checks"].items() if not passed)
    if result["passes_fixed_pixel_checks"]:
        raise AssertionError(f"{label}: incorrectly passed corrupted frames")
    if not set(expected_failed).intersection(actual_failed):
        raise AssertionError(
            f"{label}: expected failures {expected_failed}, got {actual_failed}"
        )
    if result["approved"] or result["published"] or result["production_ready"]:
        raise AssertionError(f"{label}: review gate unexpectedly opened")
    return {
        "case":label,
        "rejected":True,
        "checks_failed":actual_failed,
        "expected_detection":expected_failed,
    }


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--directory",type=Path,default=OUTPUT)
    args=parser.parse_args()
    root=args.directory
    report=json.loads((root/"review.json").read_text(encoding="utf-8"))
    frames=decode_frames(root)
    valid=score_frames(frames, report)
    if not valid["passes_fixed_pixel_checks"]:
        raise AssertionError("Unmodified actual render must pass before injection")

    cases=[]
    # Same payoff shot and same camera, but frame 16 replays the old beam
    # position rather than visibly advancing.
    stalled=frames.copy()
    stalled[16]=frames[15]
    cases.append(evaluate(
        "beam_stalls_in_transit",stalled,report,
        ["beam_front_moves_toward_lighthouse"]
    ))

    # The tip cannot reach the lighthouse because frame 17 repeats 16.
    missing_contact=frames.copy()
    missing_contact[17]=frames[16]
    cases.append(evaluate(
        "beam_never_reaches_beacon",missing_contact,report,
        ["incoming_beam_visible_at_target_before_ignition"]
    ))

    # A fully lit frame is spliced into frame 17: ignition arrives one frame
    # too early, so our temporal cause-effect predicate must reject it.
    early=frames.copy()
    early[17]=frames[18]
    cases.append(evaluate(
        "beacon_ignites_before_authorized_payoff",early,report,
        ["beacon_visibly_ignites_after_contact"]
    ))

    # Keep metadata claiming the beacon lights, but insert a dark frame
    # for the ending. The pixel check must independently reject the lie.
    never_lights=frames.copy()
    never_lights[18]=frames[17]
    never_lights[19]=frames[17]
    cases.append(evaluate(
        "beacon_never_illuminates",never_lights,report,
        ["beacon_visibly_ignites_after_contact"]
    ))

    # Final frame loses the illuminated state: persistence must fail.
    flicker=frames.copy()
    flicker[19]=frames[17]
    cases.append(evaluate(
        "beacon_goes_dark_at_end",flicker,report,
        ["beacon_glow_persists_last_frame"]
    ))

    result={
        "experiment":"isolated actual-frame negative controls",
        "source_frames":len(frames),
        "original_render_passed":True,
        "all_corruptions_rejected":all(x["rejected"] for x in cases),
        "negative_case_count":len(cases),
        "cases":cases,
        "approved":False,
        "published":False,
        "production_ready":False,
        "paid_apis_used":False,
        "manual_review_required":True,
        "semantic_quality":"not_verified"
    }
    (root/"negative_controls.json").write_text(
        json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print("ASTRA_CAUSAL_NEGATIVE_CONTROLS="+json.dumps(result),flush=True)
    if not result["all_corruptions_rejected"] or len(cases)!=5:
        raise SystemExit(1)


if __name__=="__main__":
    main()
