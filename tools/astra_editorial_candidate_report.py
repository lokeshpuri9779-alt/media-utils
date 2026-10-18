"""Generate a review-only ASTRA story candidate report. Never grants publication approval."""
import argparse
import hashlib
import json
from pathlib import Path
from astra_v2.story_expansion_2000 import candidate_records, candidate_count
from astra_v2.story_forge import catalog, plot_fingerprint

def build_report(limit=100):
    authored = catalog(limit=2000)
    existing_titles = {x["title"].casefold().strip() for x in authored}
    existing_fingerprints = {x["plot_fingerprint"] for x in authored}
    unique = {}
    for key, title, genre, beats in candidate_records():
        fp = plot_fingerprint(beats)
        if title.casefold().strip() in existing_titles or fp in existing_fingerprints:
            continue
        if fp in unique:
            continue
        if len(beats) != 4 or any(len(b[1].split()) < 9 for b in beats):
            continue
        unique[fp] = {"key": key, "title": title, "mechanism": key.split("-")[1],
                      "plot_fingerprint": fp, "beats": beats,
                      "production_ready": False, "review_status": "unreviewed"}
    # Stable order across runs, so reviews are reproducible and not silently reapproved.
    selected = sorted(unique.values(), key=lambda x: hashlib.sha256(x["key"].encode()).hexdigest())[:limit]
    return {"source_candidates": candidate_count(), "unique_candidates": len(unique),
            "selected_for_review": len(selected), "publication_approved": 0,
            "note": "Review-only output. Do not feed to publisher without individual editorial approval.",
            "candidates": selected}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="astra-editorial-review.json")
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    if not 1 <= args.limit <= 500:
        parser.error("--limit must be between 1 and 500")
    report = build_report(args.limit)
    Path(args.output).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "candidates"}))

if __name__ == "__main__":
    main()
