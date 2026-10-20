"""Read-only production inventory performance probe; never grants approval."""
import argparse
import json
import time
from pathlib import Path

from astra_v2.story_editorial_report import report
from astra_v2.story_supply_review import assess


def benchmark(ledger_path, sample=256):
    ledger = json.loads(Path(ledger_path).read_text(encoding="utf-8"))
    proposals = ledger.get("proposals")
    if not isinstance(proposals, list):
        raise ValueError("Invalid proposal ledger")
    selected = proposals[:sample]
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "sample.json"
        output = root / "editorial.json"
        source.write_text(json.dumps({"proposals": selected}), encoding="utf-8")
        start = time.perf_counter()
        editorial = report(source, output)
        triage_seconds = time.perf_counter() - start
        start = time.perf_counter()
        audit = assess(source)
        audit_seconds = time.perf_counter() - start
    if editorial["total_proposals"] != len(selected) or audit["proposal_count"] != len(selected):
        raise AssertionError("Assessment count mismatch")
    if audit["approved_for_production"] != 0 or editorial["automatic_publication_enabled"]:
        raise AssertionError("Unexpected automatic approval")
    return {"sample_count": len(selected), "triage_seconds": round(triage_seconds, 3),
            "audit_seconds": round(audit_seconds, 3), "approved_for_production": 0}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", default="runtime-health/story_proposals.json")
    parser.add_argument("--sample", type=int, default=256)
    args = parser.parse_args()
    if not 1 <= args.sample <= 10000:
        parser.error("--sample must be 1..10000")
    print(json.dumps(benchmark(args.ledger, args.sample), sort_keys=True))
