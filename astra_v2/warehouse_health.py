"""Read-only production warehouse readiness check.

This does not grant approval, claim work, publish, or create schema.
"""
from __future__ import annotations
import argparse
import json

from astra_v2.adaptive_shared_queue import warehouse_from_environment


def check():
    warehouse = warehouse_from_environment()
    counts = warehouse.counts()
    if not isinstance(counts, dict) or any(
        type(counts.get(key)) is not int or counts[key] < 0
        for key in ("ready", "reserved", "published", "expired")
    ):
        raise ValueError("invalid_warehouse_counts")
    if counts["expired"] > counts["reserved"]:
        raise ValueError("invalid_expired_count")
    return {"warehouse_reachable": True, "counts": counts,
            "publication_triggered": False,
            "requires_manual_reconciliation": counts["expired"] > 0}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    print(json.dumps(check(), sort_keys=True))


if __name__ == "__main__":
    main()
