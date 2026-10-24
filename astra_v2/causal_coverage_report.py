"""Read-only coverage report for explicit causal annotations in verified stories.

Missing annotations are reported, never invented or treated as proof of novelty.
"""
import argparse
import json
from pathlib import Path

FIELDS = ("central_conflict", "decisive_choice", "resolution")


def coverage_report(records):
    if isinstance(records, dict):
        records = list(records.values())
    if not isinstance(records, list):
        raise ValueError("story records must be a list or mapping")
    total = complete = partial = missing = 0
    examples = []
    for record in records:
        if not isinstance(record, dict):
            continue
        total += 1
        present = sum(bool(str(record.get(field) or "").strip()) for field in FIELDS)
        if present == len(FIELDS):
            complete += 1
        elif present:
            partial += 1
        else:
            missing += 1
        if present < len(FIELDS) and len(examples) < 20:
            examples.append({"content_id": record.get("content_id"), "title": record.get("title"), "present_fields": present})
    return {"total": total, "complete": complete, "partial": partial, "missing": missing,
            "complete_percent": round(100 * complete / total, 1) if total else 0.0,
            "incomplete_examples": examples}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path, help="JSON history or publisher-state file")
    args = parser.parse_args()
    data = json.loads(args.path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "published" in data:
        data = data["published"]
    elif isinstance(data, dict) and "stories" in data:
        data = data["stories"]
    print(json.dumps(coverage_report(data), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
