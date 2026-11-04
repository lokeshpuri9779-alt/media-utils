"""Offline, read-only script and renderer feasibility report for unreviewed proposals.

The report does not change scripts, approve stories, render media, call a model,
or authorize publication. Structural renderer eligibility does NOT establish
visual/narration semantic fidelity.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

from astra_v2.creative_skill_upgrade import story_advisory
from astra_v2.editorial_approval_manifest import story_digest


MAX_STORIES = 50
MAX_DOCUMENT_BYTES = 5_000_000


def _reason_category(reason):
    """Return known diagnostic categories, never arbitrary renderer text."""
    value = str(reason or "").casefold()
    if "human_actor" in value or "human actor" in value:
        return "unsupported_human_actor"
    if "scene_art" in value or "reviewed_art" in value or "missing_art" in value:
        return "missing_verified_artwork"
    if "empty directed plan" in value:
        return "empty_storyboard"
    if "cast" in value or "character" in value:
        return "cast_mismatch"
    if "shot " in value or "visual" in value:
        return "invalid_visual_shot"
    return "other_renderer_incompatibility"



def scene_taxonomy_diagnostic(story):
    """Inspect the same pre-render Studio shot plan without trusting art coverage.

    This measures recognizable scene terms only: no asset inventory, rendered
    pixels, semantic fidelity, editorial decision, model call or publication.
    """
    if story.get("genre") != "fiction":
        return {"status": "not_applicable", "shot_count": 0,
                "recognized_shots": 0, "unresolved_shots": 0}
    try:
        from copy import deepcopy
        from studio_renderer import make_plan
        from astra_v2.visual_artifact_backdrop import analyze_story_scene
        plan = make_plan(deepcopy(story))
        if not isinstance(plan, (list, tuple)) or not 1 <= len(plan) <= 100:
            raise ValueError("invalid_studio_plan")
        recognized = 0
        unresolved = 0
        for shot in plan:
            if not isinstance(shot, dict):
                raise ValueError("invalid_studio_shot")
            analysis = analyze_story_scene(shot)
            if analysis.get("scene") is None:
                unresolved += 1
            else:
                recognized += 1
        if recognized == len(plan):
            status = "all_shots_recognized"
        elif unresolved == len(plan):
            status = "no_shots_recognized"
        else:
            status = "partially_recognized"
        return {"status": status, "shot_count": len(plan),
                "recognized_shots": recognized, "unresolved_shots": unresolved}
    except Exception:
        # This optional diagnostic never blocks independent editorial review.
        # Do not leak prompt/credential paths or report unknown shots as good.
        return {"status": "unavailable", "shot_count": 0,
                "recognized_shots": 0, "unresolved_shots": 0}


def analyze_batch(document, checker=None):
    """Generate per-candidate diagnostics without modifying source proposals.

    checker is injected in tests; production uses the existing renderer preflight.
    Renderer errors are classified without recording exception/credential strings.
    """
    if not isinstance(document, dict) or document.get("status") != "unreviewed":
        raise ValueError("unreviewed_batch_required")
    stories = document.get("stories")
    if not isinstance(stories, list) or len(stories) > MAX_STORIES:
        raise ValueError("invalid_batch_size")

    if checker is None:
        from astra_v2.renderer_eligibility import check_renderer_eligibility
        checker = check_renderer_eligibility

    rows = []
    for index, story in enumerate(stories):
        if not isinstance(story, dict):
            raise ValueError("invalid_story")
        try:
            digest = story_digest(story)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("invalid_story_payload") from exc
        try:
            script = story_advisory(story)
        except (TypeError, ValueError):
            script = {"status": "unavailable", "cliche_count": 0,
                      "repeated_sentence_count": 0, "approval": False}
        # Non-fiction is not assessed by the directed-fiction renderer.
        if story.get("genre") != "fiction":
            status, category, shot_count = "not_applicable", "not_fiction", 0
        else:
            try:
                eligible, reason, modes = checker(story)
                if eligible is True:
                    status = "structurally_eligible"
                    category = "none"
                    shot_count = len(modes) if isinstance(modes, (list, tuple)) else 0
                else:
                    status = "incompatible"
                    category = _reason_category(reason)
                    shot_count = 0
            except Exception:
                # Diagnostics are isolated and never turn failure into eligibility.
                status, category, shot_count = "unavailable", "renderer_check_failed", 0

        scene = scene_taxonomy_diagnostic(story)
        rows.append({
            "index": index, "story_sha256": digest,
            "scene_taxonomy": scene,
            "script": script,
            "renderer_status": status,
            "renderer_reason_category": category,
            "renderer_shot_count": shot_count,
            "semantic_visual_approval": False,
            "editorial_approval": False,
            "publication_approved": False,
        })

    return {
        "status": "diagnostic_only",
        "generated": len(rows),
        "script_status_counts": dict(sorted(Counter(row["script"]["status"] for row in rows).items())),
        "renderer_status_counts": dict(sorted(Counter(row["renderer_status"] for row in rows).items())),
        "renderer_reason_counts": dict(sorted(Counter(row["renderer_reason_category"] for row in rows).items())),
        "scene_taxonomy_status_counts": dict(sorted(Counter(row["scene_taxonomy"]["status"] for row in rows).items())),
        "scene_taxonomy_recognized_shots": sum(row["scene_taxonomy"]["recognized_shots"] for row in rows),
        "scene_taxonomy_unresolved_shots": sum(row["scene_taxonomy"]["unresolved_shots"] for row in rows),
        "scene_taxonomy_scope": "planning_only_no_verified_artwork_or_semantic_approval",
        "candidates": rows,
        "semantic_visual_approval": False,
        "editorial_approval": False,
        "publication_triggered": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline ASTRA creative pre-render diagnostics")
    parser.add_argument("--input", default="runtime-health/gemini-proposals.json")
    parser.add_argument("--output", default="runtime-health/creative-preflight-report.json")
    args = parser.parse_args(argv)
    source = Path(args.input)
    if source.stat().st_size > MAX_DOCUMENT_BYTES:
        raise SystemExit("Input exceeds bounded diagnostic size")
    document = json.loads(source.read_text(encoding="utf-8"))
    report = analyze_batch(document)
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    # Sanitized counts only: never log prompts, stories, provider responses, keys.
    print("ASTRA_CREATIVE_PREFLIGHT=" + json.dumps({
        "generated": report["generated"],
        "renderer_status_counts": report["renderer_status_counts"],
        "script_status_counts": report["script_status_counts"],
        "scene_taxonomy_status_counts": report["scene_taxonomy_status_counts"],
        "scene_taxonomy_unresolved_shots": report["scene_taxonomy_unresolved_shots"],
        "approval": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
