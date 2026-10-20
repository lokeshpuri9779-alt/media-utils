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
        print("ASTRA_EDITORIAL_INTAKE_CANDIDATES=" + str(result["intake_count"]))
        # Classify only explicitly approved authored narratives after the
        # hash-bound review audit; never mutate reviewed source documents.
        output = []
        for reviewed in result["stories"]:
            story = dict(reviewed)
            if story.get("kind") == "authored_causal_story" and story.get("story_beats"):
                if story.get("genre") not in (None, "", "fiction"):
                    raise ValueError("reviewed_authored_story_genre_conflict")
                story["genre"] = "fiction"
            output.append(story)
        return output
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise CreativeSkip("editorial_intake_unavailable:" + type(exc).__name__) from exc
