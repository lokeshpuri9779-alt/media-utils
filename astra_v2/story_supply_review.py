"""Read-only production-supply assessment for unreviewed story proposals.

No story promotion or publication occurs here.
"""
import json
from collections import Counter
from pathlib import Path
from astra_v2.proposal_history import load_history
from astra_v2.story_editorial import editorial_issues
from astra_v2.publication_quality import publication_rejection
from astra_v2.proposal_novelty_index import NoveltyIndex
from astra_v2.semantic_candidate_index import SemanticCandidateIndex


def assess(ledger_path, publisher_path="astra_v2_state.json",
           story_path="astra_story_history.json"):
    ledger = json.loads(Path(ledger_path).read_text(encoding="utf-8"))
    if not isinstance(ledger, dict) or not isinstance(ledger.get("proposals"), list):
        raise ValueError("Invalid proposal ledger")
    history = load_history(publisher_path, story_path)
    reviewed = []
    editorial_reason_counts = Counter()
    publication_reason_counts = Counter()
    structurally_sound_count = 0
    family_counts = Counter()
    duplicate_by_family = Counter()
    visual_issues_by_family = Counter()
    novelty_index = NoveltyIndex(history)
    semantic_index = SemanticCandidateIndex(history)
    for story in ledger["proposals"]:
        if not isinstance(story, dict):
            raise ValueError("Invalid proposal")
        issues = editorial_issues(story, history, novelty_index=novelty_index,
                                  semantic_index=semantic_index)
        rejection = publication_rejection(story)
        editorial_reason_counts.update(issues)
        family = str(story.get('genre') or 'mystery')
        family_counts[family] += 1
        if 'narrative_duplicate' in issues:
            duplicate_by_family[family] += 1
        if 'insufficient_visual_variety' in issues:
            visual_issues_by_family[family] += 1
        if rejection:
            publication_reason_counts[rejection] += 1
        if not [issue for issue in issues
                if issue != "human_or_model_editorial_review_required"]:
            structurally_sound_count += 1
        reviewed.append({
            "content_id": story.get("content_id"),
            "editorial_issues": issues,
            "publication_rejection": rejection,
            "eligible_for_automatic_publishing": False,
        })
        history.append(story)
        novelty_index.add(story)
        semantic_index.add(story)
    return {
        "proposal_count": len(reviewed),
        "editorial_issue_count": sum(bool(x["editorial_issues"]) for x in reviewed),
        "publication_blocked_count": sum(bool(x["publication_rejection"]) for x in reviewed),
        "approved_for_production": 0,
        "structurally_sound_unreviewed_count": structurally_sound_count,
        "editorial_reason_counts": dict(sorted(editorial_reason_counts.items())),
        "family_counts": dict(sorted(family_counts.items())),
        "narrative_duplicates_by_family": dict(sorted(duplicate_by_family.items())),
        "visual_variety_issues_by_family": dict(sorted(visual_issues_by_family.items())),
        "publication_rejection_reason_counts": dict(sorted(publication_reason_counts.items())),
        "review_queue": [x for x in reviewed if x["editorial_issues"] == ["human_or_model_editorial_review_required"]],
        "proposals": reviewed,
    }


if __name__ == "__main__":
    import os
    result = assess(os.getenv("ASTRA_PROPOSAL_LEDGER", "runtime-health/story_proposals.json"))
    path = Path(os.getenv("ASTRA_SUPPLY_REVIEW_REPORT", "runtime-health/story_supply_review.json"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("ASTRA_STORY_SUPPLY_REVIEW=" + json.dumps({k: v for k, v in result.items() if k not in ("proposals", "review_queue")}))
    print("ASTRA_STORY_REVIEW_QUEUE=" + json.dumps({"count": len(result["review_queue"]), "content_ids": [x["content_id"] for x in result["review_queue"][:25]], "approval_granted": False}))
