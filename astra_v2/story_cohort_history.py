"""Maintain bounded, idempotent history of unreviewed story cohorts."""
import json
from pathlib import Path

LIMIT = 30


def append(history, cohort, run_id, attempt, commit):
    if cohort.get("publication_enabled") is not False or cohort.get("approved_for_production") != 0:
        raise ValueError("Unsafe cohort report")
    if not str(run_id).isdigit() or not str(attempt).isdigit():
        raise ValueError("Invalid workflow identity")
    new = cohort.get("new", {})
    total = new.get("total", 0)
    duplicates = new.get("issue:narrative_duplicate", 0)
    if not isinstance(total, int) or not isinstance(duplicates, int) or total < 0 or not 0 <= duplicates <= total:
        raise ValueError("Invalid cohort counts")
    entries = history.get("runs", [])
    if not isinstance(entries, list):
        raise ValueError("Invalid cohort history")
    key = (str(run_id), str(attempt))
    entry = {
        "run_id": key[0], "attempt": key[1], "commit": commit,
        "new_proposals": total, "narrative_duplicates": duplicates,
        "duplicate_rate": round(duplicates / total, 4) if total else None,
        "publication_enabled": False,
    }
    retained = [x for x in entries if (str(x.get("run_id")), str(x.get("attempt"))) != key]
    return {"schema_version": 1, "runs": (retained + [entry])[-LIMIT:]}


def main():
    history_path = Path("runtime-health/story_cohort_history.json")
    cohort_path = Path("runtime-health/story_cohort_quality.json")
    history = json.loads(history_path.read_text()) if history_path.exists() else {"runs": []}
    cohort = json.loads(cohort_path.read_text())
    import os
    updated = append(history, cohort, os.environ["GITHUB_RUN_ID"], os.environ["GITHUB_RUN_ATTEMPT"], os.environ["GITHUB_SHA"])
    history_path.write_text(json.dumps(updated, indent=2, sort_keys=True) + "\n")
    print("ASTRA_COHORT_TREND_RUNS=" + str(len(updated["runs"])))


if __name__ == "__main__":
    main()
