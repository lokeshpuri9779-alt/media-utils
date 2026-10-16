"""ASTRA Shorts eight-gate readiness audit; read-only and fail-closed.

This is a diagnostic tool, not a replacement for runtime publication gates.
"""
import json
import os
from pathlib import Path

GATES = (
    "ai_generation", "editorial_approval", "persistent_novelty",
    "approved_story_supply", "renderer", "video_quality",
    "youtube_publication", "performance_learning",
)


def assess(story=None, history=(), video_path=None, publication=None, metrics=None):
    from astra_v2.openai_creative import enabled
    from astra_v2.story_editorial import editorial_issues
    from astra_v2.publication_quality import publication_rejection
    from astra_v2.shorts_novelty import is_near_duplicate
    from astra_v2.story_planning import planning_issues
    result = {key: {"passed": False, "reason": "not_verified"} for key in GATES}
    result["ai_generation"] = {"passed": False,
                               "reason": "paid_model_opt_in" if enabled() else "no_model_enabled"}
    if isinstance(story, dict):
        issues = editorial_issues(story, history)
        rejection = publication_rejection(story)
        approved = not issues and not rejection and bool(story.get("production_ready"))
        result["editorial_approval"] = {"passed": approved,
                                        "reason": "approved" if approved else
                                        ",".join(issues + ([rejection] if rejection else [])) or "not_approved"}
        result["persistent_novelty"] = {"passed": not is_near_duplicate(story, history),
                                         "reason": "unique_against_supplied_history" if not is_near_duplicate(story, history) else "duplicate"}
        result["approved_story_supply"] = {"passed": approved and not planning_issues(story),
                                            "reason": "candidate_eligible" if approved and not planning_issues(story) else "no_approved_candidate"}
        result["renderer"] = {"passed": bool(video_path and Path(video_path).is_file()),
                               "reason": "video_file_present" if video_path and Path(video_path).is_file() else "no_video_file"}
        if video_path and Path(video_path).is_file():
            try:
                from astra_v2.creative import inspect_video
                inspect_video(Path(video_path))
                result["video_quality"] = {"passed": True, "reason": "technical_media_preflight_only"}
            except Exception as exc:
                result["video_quality"]["reason"] = "media_preflight_failed:" + type(exc).__name__
    if isinstance(publication, dict) and publication.get("outcome") == "published" and publication.get("video_id"):
        result["youtube_publication"] = {"passed": True, "reason": "publication_record_supplied"}
    if isinstance(metrics, dict) and metrics.get("video_id") and metrics.get("measured_at"):
        result["performance_learning"] = {"passed": True, "reason": "metrics_record_supplied_not_learning_proof"}
    result["end_to_end_verified"] = False  # requires independently corroborated upload and QA
    return result


def main():
    story_path = os.getenv("ASTRA_AUDIT_STORY", "")
    story = json.loads(Path(story_path).read_text()) if story_path else None
    result = assess(story=story, video_path=os.getenv("ASTRA_AUDIT_VIDEO"))
    target = Path(os.getenv("ASTRA_AUDIT_OUTPUT", "runtime-health/production_readiness.json"))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2))
    print("ASTRA_PRODUCTION_READINESS=" + json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
