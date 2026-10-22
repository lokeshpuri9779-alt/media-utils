"""Optional, fail-closed editorial story source for Shorts creative selection."""
import json
import os
from pathlib import Path

def load_editorial_stories():
    from astra_v2.creative import CreativeSkip
    source = os.getenv("ASTRA_EDITORIAL_STORIES_FILE", "").strip()
    reviews = os.getenv("ASTRA_EDITORIAL_REVIEWS_FILE", "").strip()
    if not source and not reviews:
        return []
    if not source or not reviews:
        raise CreativeSkip("editorial_intake_incomplete_configuration")
    try:
        from astra_v2.editorial_approved_intake import approved_intake
        from astra_v2.proposal_history import load_history
        publisher = Path(os.getenv("ASTRA_PUBLISHER_STATE_PATH", "astra_v2_state.json"))
        history = Path(os.getenv("ASTRA_STORY_HISTORY_PATH", "astra_story_history.json"))
        if not publisher.is_file() or not history.is_file():
            raise FileNotFoundError("editorial_intake_requires_complete_history")
        stories = json.loads(Path(source).read_text(encoding="utf-8"))
        decisions = json.loads(Path(reviews).read_text(encoding="utf-8"))
        result = approved_intake(stories["stories"], decisions["reviews"],
                                 load_history(publisher, history))
        # Surface why signed approvals are excluded by the live history gate.
        # Diagnostics only: never alter approval, novelty, or publication decisions.
        from collections import Counter
        reasons = Counter(issue for entry in result["audit"]["results"]
                          for issue in entry["issues"])
        print("ASTRA_EDITORIAL_INTAKE_AUDIT=" + json.dumps({
            "reviewed": len(result["audit"]["results"]),
            "eligible": result["intake_count"],
            "excluded": len(result["audit"]["results"]) - result["intake_count"],
            "reasons": dict(sorted(reasons.items())),
        }, sort_keys=True))
        # Read-only diagnostic: expose the strongest historical narrative match.
        # Do not change the novelty threshold or any approval decision.
        from astra_v2.story_editorial import semantic_duplicate_match
        from astra_v2.shorts_novelty import is_near_duplicate
        history_records = load_history(publisher, history)
        for entry in result["audit"]["results"]:
            if "narrative_duplicate" not in entry["issues"]:
                continue
            candidates = [s for s in stories["stories"]
                          if s.get("content_id") == entry["content_id"]]
            if len(candidates) != 1:
                continue
            match = semantic_duplicate_match(candidates[0], history_records)
            print("ASTRA_EDITORIAL_DUPLICATE_EVIDENCE=" + json.dumps({
                "content_id": entry["content_id"],
                "semantic_match": match,
                "other_novelty_match": bool(is_near_duplicate(candidates[0], history_records)),
                "history_record_count": len(history_records),
                "publication_triggered": False,
            }, sort_keys=True))
        print("ASTRA_EDITORIAL_INTAKE_CANDIDATES=" + str(result["intake_count"]))
        # Include the persistent AI-reviewed pair restored from astra-state.
        # This pair is not trusted merely because it exists: run the exact
        # same hash-bound approval and full publication-history gate.
        persistent_source = Path(os.getenv("ASTRA_PERSISTED_EDITORIAL_STORIES_FILE",
                                          "runtime-health/ai-reviewed-stories.json"))
        persistent_reviews = Path(os.getenv("ASTRA_PERSISTED_EDITORIAL_REVIEWS_FILE",
                                           "runtime-health/ai-reviewed-decisions.json"))
        if persistent_source.exists() != persistent_reviews.exists():
            raise CreativeSkip("persistent_editorial_intake_incomplete_pair")
        if persistent_source.is_file():
            additional_stories = json.loads(persistent_source.read_text(encoding="utf-8"))
            additional_reviews = json.loads(persistent_reviews.read_text(encoding="utf-8"))
            history_records = load_history(publisher, history)
            # Treat accepted static stories as reserved to avoid selecting
            # identical candidates from both sources.
            additional = approved_intake(additional_stories["stories"],
                                         additional_reviews["reviews"],
                                         list(history_records) + result["stories"])
            from collections import Counter
            additional_reasons = Counter(issue for entry in additional["audit"]["results"]
                                         for issue in entry["issues"])
            print("ASTRA_PERSISTED_EDITORIAL_AUDIT=" + json.dumps({
                "reviewed": len(additional["audit"]["results"]),
                "eligible": additional["intake_count"],
                "reasons": dict(sorted(additional_reasons.items())),
            }, sort_keys=True))
            result["stories"].extend(additional["stories"])
        return result["stories"]
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise CreativeSkip("editorial_intake_unavailable:" + type(exc).__name__) from exc
