"""Fail-closed validation for the durable ASTRA publishing journal.

Run before preflight/preload and again before writing back to astra-state.
Never replace a missing or malformed journal with an empty state: doing so
would forget previously published, pending and reserved upload identities.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


class StateJournalError(ValueError):
    """State cannot safely be used for upload decisions."""


def validate_state_journal(path: str | Path) -> dict:
    source = Path(path)
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise StateJournalError("missing or unreadable state journal") from exc
    if not isinstance(data, dict) or data.get("version") != 2:
        raise StateJournalError("invalid state journal version or root")
    if not isinstance(data.get("day"), str) or not data["day"]:
        raise StateJournalError("invalid journal day")
    for field in ("attempts", "confirmed_today"):
        value = data.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise StateJournalError(f"invalid {field} counter")
    for field in ("published", "pending", "reserved"):
        if field not in data and field == "reserved":
            continue  # Older valid journals did not have reservations.
        entries = data.get(field)
        if not isinstance(entries, dict):
            raise StateJournalError(f"invalid {field} journal")
        if any(not isinstance(key, str) or not isinstance(value, dict)
               for key, value in entries.items()):
            raise StateJournalError(f"invalid {field} entry")
    return data


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else "astra_v2_state.json"
    try:
        data = validate_state_journal(path)
    except StateJournalError as exc:
        print(f"ASTRA_STATE_JOURNAL_INVALID={exc}", file=sys.stderr)
        return 1
    print("ASTRA_STATE_JOURNAL_VALID=" + json.dumps({
        "published": len(data["published"]),
        "pending": len(data["pending"]),
        "reserved": len(data.get("reserved", {})),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
