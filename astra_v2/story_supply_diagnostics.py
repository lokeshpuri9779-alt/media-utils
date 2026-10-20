"""Read-only diagnostics for the finite ASTRA draft generator.

Never changes production_ready or grants publishing permission.
"""
from collections import Counter
from astra_v2.story_forge import draft_catalog, editorial_screen, catalog
from astra_v2.production_story_gate import candidate_issues


def supply_report():
    drafts = draft_catalog()
    screened = editorial_screen()
    reasons = Counter(reason for _, reason in screened["rejected"])
    authored = catalog(limit=2000)
    failures = Counter(issue for story in authored for issue in candidate_issues(story))
    return {
        "authored_catalog": len(authored),
        "draft_candidates": len(drafts),
        "rewrite_queue": len(screened["rewrite_queue"]),
        "rejected": len(screened["rejected"]),
        "rejection_reasons": dict(sorted(reasons.items())),
        "authored_gate_issues": dict(sorted(failures.items())),
        "draft_auto_approved": 0,
        "generator_type": "finite_actor_problem_setback_combinations",
        "autonomous_production_ready_supply": False,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(supply_report(), indent=2, sort_keys=True))
