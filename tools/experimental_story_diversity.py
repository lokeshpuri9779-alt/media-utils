"""Second, distinct ASTRA story candidate. Planning-only, no render or publication.

Tests narrative diversity before investing CPU minutes in a new Blender scene.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from astra_v2.episode_planner import plan_episode
from tools.experimental_causal_storyboard import build_storyboard

SCENES = [
    {
        "cause": "A paper airplane carrying a seed is blown into a rain-filled drain.",
        "action": "A small green mechanical frog sees the stranded airplane below a street grate.",
        "consequence": "The frog decides to recover the seed before the rain carries it away.",
        "state_before": "paper plane in drain; seed trapped; frog on pavement; flowerpot empty",
        "state_after": "paper plane in drain; seed trapped; frog at grate; flowerpot empty",
    },
    {
        "cause": "The water rises while the paper plane remains out of reach.",
        "action": "The frog extends a magnetic fishing line, catches the paper clip on the airplane, and pulls it up.",
        "consequence": "The seed and paper airplane are rescued onto the pavement.",
        "state_before": "paper plane in drain; seed trapped; frog at grate; flowerpot empty",
        "state_after": "paper plane rescued; seed accessible; frog holds line; flowerpot empty",
    },
    {
        "cause": "The rescued seed will still be lost unless it is planted.",
        "action": "The frog places the seed in a nearby empty flowerpot and rain begins watering it.",
        "consequence": "A tiny green sprout emerges from the pot.",
        "state_before": "paper plane rescued; seed accessible; frog holds line; flowerpot empty",
        "state_after": "paper plane rescued; seed planted; frog by pot; tiny sprout visible",
    },
]
SHOT_FRAMES = [(0, 7), (8, 21), (22, 31)]
SHOTS = [
    {
        "beat": beat,
        "first_frame": first,
        "last_frame": last,
        "visual_focus": focus,
        "camera": camera,
        "required_visible_cue": cue,
        "scene": SCENES[i],
    }
    for i, (beat, (first, last), focus, camera, cue) in enumerate(zip(
        ("setup", "attempt", "payoff"),
        SHOT_FRAMES,
        ("drain, trapped paper plane and frog", "magnetic line and retrieved plane", "seed entering pot then sprout"),
        ("wide overhead curb", "low medium grate", "close-up pot"),
        ("plane remains in water", "line contacts paper clip before retrieval", "seed visibly enters soil before sprout"),
    ))
]


def build():
    first = build_storyboard()
    proposal = plan_episode("astra-frog-seed-rescue", 1, SCENES, state={})
    assert proposal["kind"] == "unreviewed_episode_plan"
    assert proposal["production_ready"] is False
    assert proposal["plot_fingerprint"] != first["plot_fingerprint"]
    assert [s["beat"] for s in SHOTS] == ["setup", "attempt", "payoff"]
    assert [s["first_frame"] for s in SHOTS] == [0, 8, 22]
    assert [s["last_frame"] for s in SHOTS] == [7, 21, 31]
    assert all(SCENES[i]["state_after"] == SCENES[i + 1]["state_before"] for i in (0, 1))
    assert sum(s["last_frame"] - s["first_frame"] + 1 for s in SHOTS) == 32
    assert all(s["required_visible_cue"] for s in SHOTS)
    assert all(
        not any(word in json.dumps(s).lower() for word in ("lighthouse", "beacon", "robot", "orb"))
        for s in SHOTS
    )
    return {
        "title": "The Frog and the Lost Seed",
        "story_id": "astra-frog-seed-rescue",
        "plot_fingerprint": proposal["plot_fingerprint"],
        "comparison_story_fingerprint": first["plot_fingerprint"],
        "shot_count": 3,
        "frame_budget": 32,
        "shots": SHOTS,
        "approved": False,
        "published": False,
        "production_ready": False,
        "paid_apis_used": False,
        "rendered": False,
        "visual_quality": "not_tested",
        "manual_editorial_review_required": True,
        "next_validation": "isolated Blender 3-shot frog/grate/flowerpot render and visual causality check",
    }


def main():
    result = build()
    dest = Path("artifacts/experimental-story-diversity/frog_seed_plan.json")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    assert json.loads(dest.read_text()) == result
    print("ASTRA_DISTINCT_STORY_PLAN=" + json.dumps({
        "title": result["title"],
        "different_fingerprint": result["plot_fingerprint"] != result["comparison_story_fingerprint"],
        "shots": result["shot_count"],
        "frame_budget": result["frame_budget"],
        "rendered": False,
        "approved": False,
        "production_ready": False,
    }))


if __name__ == "__main__":
    main()
