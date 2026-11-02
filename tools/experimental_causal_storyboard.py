"""Causal three-shot storyboard proposal for isolated ASTRA CPU previsualization.

Uses ASTRA's existing episode planning validator but never reads or mutates
episode ledgers, editorial approvals, renderer routing, or publishing state.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from astra_v2.episode_planner import plan_episode

STORY_ID = "astra-coastal-spark"
SERIES_ID = "astra-coastal-spark"
FPS = 8
FRAME_COUNT = 20
SHOTS = (
    {
        "id": "01-beacon-dark",
        "beat": "setup",
        "first_frame": 0,
        "last_frame": 5,
        "shot_size": "wide",
        "visual_intent": "The unlit lighthouse is visible as the copper keeper notices a spark.",
        "caption": "THE LIGHT WENT DARK",
        "camera_xyz": [0.0, -8.4, 3.8],
        "camera_target_xyz": [-0.45, 0.65, 1.55],
        "camera_lens_mm": 34,
        "cause": "The lighthouse beacon goes dark before nightfall.",
        "action": "A copper robot spots a small amber spark near the lighthouse.",
        "consequence": "The robot begins approaching the spark.",
        "state_before": "beacon dark; orb on pedestal; keeper at start",
        "state_after": "beacon dark; orb on pedestal; keeper approaching",
    },
    {
        "id": "02-pickup-spark",
        "beat": "attempt",
        "first_frame": 6,
        "last_frame": 14,
        "shot_size": "medium",
        "visual_intent": "The same robot closes its fingers around the glowing orb.",
        "caption": "ONE LAST SPARK",
        "camera_xyz": [0.8, -7.2, 3.4],
        "camera_target_xyz": [0.4, 0.3, 1.45],
        "camera_lens_mm": 47,
        "cause": "The dark lighthouse still needs a new spark.",
        "action": "The robot approaches the pedestal and grasps the amber orb.",
        "consequence": "The amber orb becomes secured in the robot's claw.",
        "state_before": "beacon dark; orb on pedestal; keeper approaching",
        "state_after": "beacon dark; orb in keeper claw; keeper beside pedestal",
    },
    {
        "id": "03-beacon-returns",
        "beat": "payoff",
        "first_frame": 15,
        "last_frame": 19,
        "shot_size": "wide",
        "visual_intent": "The robot raises the spark and the lighthouse beacon lights up.",
        "caption": "THE LIGHT RETURNS",
        "camera_xyz": [0.0, -8.4, 3.8],
        "camera_target_xyz": [-0.45, 0.65, 1.55],
        "camera_lens_mm": 34,
        "cause": "The keeper holds the spark after retrieving it.",
        "action": "The robot lifts the orb and restores the lighthouse beacon.",
        "consequence": "The lighthouse shines again over the dark coast.",
        "state_before": "beacon dark; orb in keeper claw; keeper beside pedestal",
        "state_after": "beacon lit; orb in keeper claw; keeper beside pedestal",
    },
)


def build_storyboard():
    scenes = [{key: shot[key] for key in (
        "cause", "action", "consequence", "state_before", "state_after"
    )} for shot in SHOTS]
    proposal = plan_episode(SERIES_ID, 1, scenes, state={})
    assert proposal["production_ready"] is False
    assert proposal["kind"] == "unreviewed_episode_plan"
    assert len(proposal["plot_fingerprint"]) == 64
    assert tuple(shot["beat"] for shot in SHOTS) == ("setup", "attempt", "payoff")
    assert [shot["first_frame"] for shot in SHOTS] == [0, 6, 15]
    assert [shot["last_frame"] for shot in SHOTS] == [5, 14, 19]
    assert all(
        SHOTS[i]["last_frame"] + 1 == SHOTS[i + 1]["first_frame"]
        for i in range(2)
    )
    assert sum(shot["last_frame"] - shot["first_frame"] + 1 for shot in SHOTS) == FRAME_COUNT
    for shot in SHOTS:
        assert shot["camera_lens_mm"] > 0
        assert len(shot["camera_xyz"]) == len(shot["camera_target_xyz"]) == 3
    return {
        "story_id": STORY_ID,
        "title": "The Keeper and the Last Spark",
        "kind": "experimental_unreviewed_causal_storyboard",
        "plot_fingerprint": proposal["plot_fingerprint"],
        "approved": False,
        "published": False,
        "production_ready": False,
        "paid_apis_used": False,
        "editorial_review_required": True,
        "visual_review_required": True,
        "fiction": True,
        "silent_intentionally": True,
        "fps": FPS,
        "frame_count": FRAME_COUNT,
        "duration_seconds": FRAME_COUNT / FPS,
        "scenes": scenes,
        "shots": list(SHOTS),
        "shot_count": 3,
        "status": "review_only",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path,
                        default=Path("artifacts/experimental-causal-story/shot_plan.json"))
    args = parser.parse_args()
    result = build_storyboard()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("ASTRA_CAUSAL_STORYBOARD=" + json.dumps({
        "shots": result["shot_count"],
        "frames": result["frame_count"],
        "fingerprint": result["plot_fingerprint"],
        "production_ready": False,
    }))


if __name__ == "__main__":
    main()
