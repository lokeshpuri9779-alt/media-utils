"""Read-only ASTRA runtime runway and publisher heartbeat evidence.

This diagnostic never calls YouTube, Gemini, a renderer, or any publisher.
It checks the exact persisted, hash-bound editorial pair using the existing
production intake gate. Structural eligibility is NOT visual quality approval.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path

from astra_v2.editorial_approval_manifest import validate_manifest
from astra_v2.proposal_history import load_history


def _time(raw):
    if not isinstance(raw, str) or not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc) if dt.tzinfo else None
    except (ValueError, OverflowError):
        return None


def _reason(code):
    """Never leak arbitrary provider comments or full candidate narration."""
    if not isinstance(code, str):
        return "unknown"
    for prefix in (
        "renderer_incompatible", "publication_renderer_incompatible",
        "narrative_duplicate", "editorial_approval_missing",
        "review_story_digest_mismatch", "review_content_id_mismatch",
        "missing_editorial_record", "not_production_ready",
        "not_reviewed_authored_story", "missing_plot_fingerprint",
        "publication_", "reviewer_", "duplicate",
    ):
        if code.startswith(prefix):
            return prefix
    return "other_intake_rejection"


def audit(state, story_doc, review_doc, batch, history, *, now=None, validator=None):
    if any(not isinstance(x, dict) for x in
           (state, story_doc, review_doc, batch)):
        raise ValueError("Live source documents must be JSON objects")
    if state.get("version") != 2:
        raise ValueError("Unrecognized publisher journal")
    for name in ("published", "pending", "reserved"):
        if not isinstance(state.get(name, {}), dict):
            raise ValueError("Malformed publisher journal: " + name)
    stories, reviews = story_doc.get("stories"), review_doc.get("reviews")
    if not isinstance(stories, list) or not isinstance(reviews, list):
        raise ValueError("Incomplete hash-bound editorial pair")
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("Observation timestamp must include UTC offset")
    now = now.astimezone(timezone.utc)

    verdict = (validator or validate_manifest)(stories, reviews, history)
    results = verdict.get("results")
    if (not isinstance(results, list) or len(results) != len(stories)
            or verdict.get("approved_count") !=
            sum(r.get("approved") is True for r in results if isinstance(r, dict))):
        raise ValueError("Invalid intake audit response")
    by_id = {r["content_id"]: r for r in results
             if isinstance(r, dict) and isinstance(r.get("content_id"), str)}
    if len(by_id) != len(results):
        raise ValueError("Incomplete or duplicate intake status")
    issues = Counter(_reason(reason) for entry in results
                     for reason in entry.get("issues", []))
    latest = state.get("last_workflow_result")
    latest_at = _time(latest.get("at")) if isinstance(latest, dict) else None
    age = (now - latest_at).total_seconds() / 60 if latest_at else None
    # An old checkpoint proves only a stale *stored journal*, not that the
    # GitHub Actions scheduler or YouTube service stopped entirely.
    heartbeat = ("unknown_missing_checkpoint" if age is None else
                 "invalid_future_checkpoint" if age < -5 else
                 "stale_stored_checkpoint" if age > 35 else
                 "recent_stored_checkpoint")
    recent = [
        {"content_id": s.get("content_id"),
         "intake_eligible": by_id[s["content_id"]]["approved"],
         "blocking_codes": sorted(set(_reason(x)
                                  for x in by_id[s["content_id"]].get("issues", [])))}
        for s in stories[-3:]
    ]
    return {
        "kind": "astra_readonly_live_runway_v1",
        "observed_at": now.isoformat(),
        "publisher_checkpoint_at": latest_at.isoformat() if latest_at else None,
        "publisher_checkpoint_age_minutes": round(age, 1) if age is not None else None,
        "publisher_checkpoint_status": heartbeat,
        "publisher_last_result": (str(latest.get("outcome") or "")[:55]
                                  if isinstance(latest, dict) else "unknown"),
        "confirmed_today_in_stored_journal": state.get("confirmed_today"),
        "pending_processing_in_stored_journal": len(state["pending"]),
        "gemini_batch_at": batch.get("observed_at"),
        "batch_generated": batch.get("generated"),
        "batch_editorial_approved": batch.get("approved"),
        "persisted_editorial_stories": len(stories),
        "persisted_editorial_decisions": len(reviews),
        "current_intake_eligible": verdict["approved_count"],
        "current_intake_blocked": len(stories) - verdict["approved_count"],
        "current_intake_blocking_categories": dict(sorted(issues.items())),
        "recent_persisted_story_intake": recent,
        "technical_intake_is_not_visual_approval": True,
        "publication_triggered": False,
        "automatic_approval": False,
        "paid_provider_called": False,
        "production_route_modified": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    root = args.state_dir
    names = ("astra_v2_state.json", "astra_story_history.json",
             "astra_duplicate_protection.json", "ai-reviewed-stories.json",
             "ai-reviewed-decisions.json", "gemini-batch-diagnostic.json")
    if any(not (root / name).is_file() for name in names):
        raise SystemExit("Required protected runtime history or editorial pair missing")
    def read(name):
        return json.loads((root / name).read_text(encoding="utf-8"))
    history = load_history(root / "astra_v2_state.json",
                           root / "astra_story_history.json")
    result = audit(read("astra_v2_state.json"), read("ai-reviewed-stories.json"),
                   read("ai-reviewed-decisions.json"),
                   read("gemini-batch-diagnostic.json"), history)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print("ASTRA_LIVE_RUNWAY=" + json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
