"""Fail-closed validation of the durable publisher journal before restoration.

A missing/corrupt astra-state journal must never silently become a fresh
publisher identity history. This module does not modify the journal.
"""
import argparse
import json
from datetime import date
from pathlib import Path


class UnsafePublisherState(RuntimeError):
    """Publisher state cannot safely be used for idempotent uploads."""


def validate_state(state, *, require_history=False):
    if not isinstance(state, dict) or state.get("version") != 2:
        raise UnsafePublisherState("publisher state missing or wrong version")
    try:
        date.fromisoformat(state["day"])
    except (KeyError, TypeError, ValueError) as exc:
        raise UnsafePublisherState("publisher day is missing or invalid") from exc
    for name in ("attempts", "confirmed_today"):
        value = state.get(name)
        if type(value) is not int or value < 0:
            raise UnsafePublisherState(f"invalid publisher counter: {name}")
    for name in ("published", "pending", "reserved"):
        if name == "reserved" and name not in state:
            continue  # Older valid journals may predate reservations.
        records = state.get(name)
        if not isinstance(records, dict):
            raise UnsafePublisherState(f"invalid publisher journal: {name}")
        for key, entry in records.items():
            if not isinstance(key, str) or not key or not isinstance(entry, dict):
                raise UnsafePublisherState(f"invalid {name} identity or entry")
            if name == "published" and not entry.get("video_id"):
                raise UnsafePublisherState("published identity lacks video_id")
            if name == "pending" and not entry.get("content_id"):
                raise UnsafePublisherState("pending upload lacks content_id")
    if require_history and not state["published"]:
        raise UnsafePublisherState("publisher history unexpectedly empty")
    return state


def validate_file(path, *, require_history=False):
    try:
        raw = Path(path).read_text(encoding="utf-8")
        state = json.loads(raw)
    except (OSError, ValueError) as exc:
        raise UnsafePublisherState("publisher journal missing or invalid JSON") from exc
    return validate_state(state, require_history=require_history)


def main():
    parser = argparse.ArgumentParser(description="Validate restored ASTRA publisher journal")
    parser.add_argument("path", nargs="?", default="astra_v2_state.json")
    parser.add_argument("--require-history", action="store_true")
    args = parser.parse_args()
    validate_file(args.path, require_history=args.require_history)
    print("ASTRA_STATE_RESTORE_VALIDATED")


if __name__ == "__main__":
    main()
