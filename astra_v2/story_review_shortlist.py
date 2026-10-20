"""Produce a bounded, non-publishing editorial shortlist from audited proposals."""
import json
import os
from pathlib import Path


def shortlist(ledger_path, review_path, output_path, limit=25):
    if not 1 <= limit <= 100:
        raise ValueError("Shortlist limit must be 1..100")
    ledger = json.loads(Path(ledger_path).read_text(encoding="utf-8"))
    review = json.loads(Path(review_path).read_text(encoding="utf-8"))
    proposals = ledger.get("proposals")
    assessments = review.get("proposals")
    if not isinstance(proposals, list) or not isinstance(assessments, list):
        raise ValueError("Invalid proposal or audit report")
    if len(proposals) != len(assessments):
        raise ValueError("Proposal/audit count mismatch")
    selected = []
    seen_titles = set()
    for story, audit in zip(proposals, assessments):
        if not isinstance(story, dict) or not isinstance(audit, dict):
            raise ValueError("Invalid proposal or audit entry")
        if story.get("content_id") != audit.get("content_id"):
            raise ValueError("Proposal/audit ordering mismatch")
        issues = audit.get("editorial_issues")
        if not isinstance(issues, list):
            raise ValueError("Missing editorial issues")
        if issues != ["human_or_model_editorial_review_required"]:
            continue
        if story.get("production_ready") is not False:
            raise ValueError("Review candidate must remain unapproved")
        title_key = str(story.get("title") or "").strip().casefold()
        if not title_key or title_key in seen_titles:
            continue
        seen_titles.add(title_key)
        selected.append({
            "content_id": story.get("content_id"),
            "title": story.get("title"),
            "genre": story.get("genre"),
            "story_beats": [
                {"story_beat": beat.get("story_beat"), "headline": beat.get("headline"),
                 "speech": beat.get("speech"), "visual": beat.get("visual")}
                for beat in story.get("story_beats", [])[:12]
                if isinstance(beat, dict)
            ],
            "editorial_issues": issues,
            "publication_rejection": audit.get("publication_rejection"),
            "production_ready": False,
            "eligible_for_automatic_publishing": False,
        })
        if len(selected) >= limit:
            break
    # Expose reused narration across otherwise distinct story titles for editorial review.
    # Diagnostic only: this does not approve, reject, or publish candidates.
    speech_owners = {}
    for entry in selected:
        for beat in entry["story_beats"]:
            speech = beat.get("speech")
            if isinstance(speech, str) and speech.strip():
                key = " ".join(speech.casefold().split())
                speech_owners.setdefault(key, set()).add(entry["content_id"])
    reused = {speech: owners for speech, owners in speech_owners.items()
              if len(owners) > 1}
    for entry in selected:
        entry["reused_narration_beats"] = sum(
            isinstance(beat.get("speech"), str)
            and " ".join(beat["speech"].casefold().split()) in reused
            for beat in entry["story_beats"]
        )
    # Repeated multi-scene plot structures can hide behind distinct titles.
    # Compare normalized narration for each scene, excluding the opening setup
    # so changes to setting or protagonist cannot conceal an identical plot.
    plot_owners = {}
    for entry in selected:
        beats = entry["story_beats"]
        if len(beats) < 3:
            continue
        plot_key = tuple(
            " ".join(str(beat.get("speech") or "").casefold().split())
            for beat in beats[1:]
        )
        if all(plot_key):
            plot_owners.setdefault(plot_key, set()).add(entry["content_id"])
    reused_plots = {key for key, owners in plot_owners.items() if len(owners) > 1}
    for entry in selected:
        beats = entry["story_beats"]
        key = tuple(
            " ".join(str(beat.get("speech") or "").casefold().split())
            for beat in beats[1:]
        )
        entry["reused_plot_arc"] = len(beats) >= 3 and key in reused_plots
    # Surface concrete scene integrity issues without claiming semantic understanding.
    # A scene with missing speech/visual or a repeated/out-of-order beat label
    # requires editorial attention; this is never an automatic approval signal.
    beat_order = {"reveal": 0, "build": 1, "twist": 2, "payoff": 3}
    for entry in selected:
        flags = []
        previous = -1
        for index, beat in enumerate(entry["story_beats"], start=1):
            if not isinstance(beat.get("speech"), str) or not beat["speech"].strip():
                flags.append(f"scene_{index}_missing_narration")
            if not isinstance(beat.get("visual"), str) or not beat["visual"].strip():
                flags.append(f"scene_{index}_missing_visual")
            label = beat.get("story_beat")
            if label in beat_order:
                position = beat_order[label]
                if position <= previous:
                    flags.append(f"scene_{index}_beat_order")
                previous = position
        entry["scene_integrity_flags"] = flags
    result = {
        "candidates_with_scene_integrity_flags": sum(
            bool(entry["scene_integrity_flags"]) for entry in selected
        ),
        "candidates_with_reused_plot_arc": sum(
            entry["reused_plot_arc"] for entry in selected
        ),
        "candidates_with_reused_narration": sum(
            bool(entry["reused_narration_beats"]) for entry in selected
        ),
        "schema_version": 1,
        "source_proposal_count": len(proposals),
        "review_candidates": selected,
        "candidate_count": len(selected),
        "approved_for_production": 0,
        "publication_enabled": False,
    }
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    result = shortlist(
        os.getenv("ASTRA_PROPOSAL_LEDGER", "runtime-health/story_proposals.json"),
        os.getenv("ASTRA_SUPPLY_REVIEW_REPORT", "runtime-health/story_supply_review.json"),
        os.getenv("ASTRA_REVIEW_SHORTLIST", "runtime-health/story_review_shortlist.json"),
    )
    print("ASTRA_EDITORIAL_SHORTLIST=" + json.dumps({
        "candidate_count": result["candidate_count"],
        "approved_for_production": 0,
        "publication_enabled": False,
    }))
