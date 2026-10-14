"""Offline JSONL history for story similarity checks. Never grants publication."""
import json
from pathlib import Path
from astra_v2.story_diversity_audit import audit_history

def read_history(path):
    file = Path(path)
    if not file.exists():
        return []
    return [json.loads(line) for line in file.read_text(encoding="utf-8").splitlines() if line.strip()]

def evaluate_and_record(stories, path, threshold=0.82):
    previous = read_history(path)
    result = audit_history(stories, history=previous, threshold=threshold)
    accepted = [story for story, check in zip(stories, result["results"]) if not check["near_duplicate"]]
    if accepted:
        file = Path(path)
        file.parent.mkdir(parents=True, exist_ok=True)
        with file.open("a", encoding="utf-8") as handle:
            for story in accepted:
                handle.write(json.dumps(story, sort_keys=True) + "\n")
    return {**result, "recorded": len(accepted), "publication_allowed": False, "quality_approved": False}
