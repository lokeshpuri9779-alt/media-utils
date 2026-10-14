"""Offline JSONL history for story similarity checks. Never grants publication."""
import json
from pathlib import Path
from astra_v2.story_diversity_audit import audit_history

def read_history(path):
    file = Path(path)
    if not file.exists():
        return []
    records = []
    for number, line in enumerate(file.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Corrupt history line {number}") from exc
        if not isinstance(record, dict) or not isinstance(record.get("scenes"), list) or not record["scenes"] or not all(isinstance(s, dict) and isinstance(s.get("narration"), str) and isinstance(s.get("action"), str) for s in record["scenes"]):
            raise ValueError(f"Invalid history story on line {number}")
        records.append(record)
    return records

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
