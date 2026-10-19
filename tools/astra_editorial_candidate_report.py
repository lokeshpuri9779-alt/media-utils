"""Generate a review-only ASTRA story candidate report. Never grants publication approval."""
import argparse
import hashlib
import json
from pathlib import Path
from astra_v2.story_expansion_2000 import candidate_records, candidate_count, MECHANISMS
from astra_v2.story_forge import catalog, plot_fingerprint

def build_report(limit=100, rotation=0, seen=None):
    seen = set(seen or ())
    authored = catalog(limit=2000)
    existing_titles = {x["title"].casefold().strip() for x in authored}
    existing_fingerprints = {x["plot_fingerprint"] for x in authored}
    mechanisms = {row[0] for row in MECHANISMS}
    unique = {}
    seen_mechanisms = set()
    # Mechanism-level novelty is distinct from cosmetic setting/character variants.
    # Previously seen fingerprints must never be presented as new authored plots.
    for key, title, genre, beats in candidate_records():
        fp = plot_fingerprint(beats)
        if title.casefold().strip() in existing_titles or fp in existing_fingerprints:
            continue
        if fp in unique:
            continue
        if len(beats) != 4 or any(len(b[1].split()) < 9 for b in beats):
            continue
        mechanism = next((m for m in mechanisms if key.startswith("exp2000-" + m + "-")), None)
        if mechanism is None:
            continue
        if fp in seen:
            seen_mechanisms.add(mechanism)
            continue
        unique[fp] = {"key": key, "title": title, "mechanism": mechanism,
                      "plot_fingerprint": fp, "beats": beats,
                      "production_ready": False, "review_status": "unreviewed"}
    # Stable order across runs, so reviews are reproducible and not silently reapproved.
    buckets = {mechanism: [] for mechanism in sorted(mechanisms)}
    for item in unique.values():
        buckets[item["mechanism"]].append(item)
    for bucket in buckets.values():
        bucket.sort(key=lambda x: hashlib.sha256(x["key"].encode()).hexdigest())
    # Rotate within each mechanism to surface different candidates across days.
    # Rotation changes review order only; it never grants production approval.
    for bucket in buckets.values():
        if bucket:
            shift = (rotation * max(1, limit // max(1, len(buckets)))) % len(bucket)
            bucket[:] = bucket[shift:] + bucket[:shift]
    selected = []
    while len(selected) < limit and any(buckets.values()):
        for mechanism in sorted(buckets):
            if buckets[mechanism] and len(selected) < limit:
                selected.append(buckets[mechanism].pop(0))
    remaining = len(unique) - len(selected)
    status = "exhausted" if remaining == 0 else "low" if remaining < limit * 3 else "healthy"
    selected_mechanisms = {x["mechanism"] for x in selected}
    # A candidate can have a fresh fingerprint while repeating a known causal premise.
    newly_introduced_mechanisms = selected_mechanisms - seen_mechanisms
    return {"authored_premises_total": len(mechanisms),
            "new_premises_in_batch": len(newly_introduced_mechanisms),
            "reused_premises_in_batch": len(selected_mechanisms & seen_mechanisms),
            "cosmetic_variants_are_new_plots": False,
            "remaining_unreviewed_after_selection": remaining, "supply_status": status,
            "requires_new_authored_mechanisms": status != "healthy",
            "source_candidates": candidate_count(), "unique_candidates": len(unique),
            "selected_for_review": len(selected), "mechanisms_represented": len({x["mechanism"] for x in selected}), "publication_approved": 0,
            "note": "Review-only output. Do not feed to publisher without individual editorial approval.",
            "candidates": selected}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="astra-editorial-review.json")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--rotation", type=int, default=0)
    parser.add_argument("--ledger", default="")
    args = parser.parse_args()
    if not 1 <= args.limit <= 500:
        parser.error("--limit must be between 1 and 500")
    if args.rotation < 0:
        parser.error("--rotation must be nonnegative")
    ledger_path = Path(args.ledger) if args.ledger else None
    previous = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path and ledger_path.exists() else {"version": 1, "seen": []}
    if previous.get("version") != 1 or not isinstance(previous.get("seen"), list) or not all(isinstance(x, str) for x in previous["seen"]):
        raise ValueError("invalid_editorial_ledger")
    report = build_report(args.limit, args.rotation, seen=previous["seen"])
    if ledger_path:
        updated = sorted(set(previous["seen"]) | {x["plot_fingerprint"] for x in report["candidates"]})
        ledger_path.write_text(json.dumps({"version": 1, "seen": updated}, indent=2) + "\n", encoding="utf-8")
        report["ledger_seen_total"] = len(updated)
        report["ledger_exhausted"] = len(report["candidates"]) < args.limit
    Path(args.output).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "candidates"}))

if __name__ == "__main__":
    main()
