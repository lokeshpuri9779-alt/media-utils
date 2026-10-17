"""Persistent mechanism-level editorial novelty ledger.

Local JSON persistence is suitable for a checked-out GitHub Actions workspace.
Callers must explicitly commit the ledger to a persistent branch/artifact; a
runner's ephemeral filesystem alone does not preserve history between runs.
This module never approves stories for publication.
"""
import json
import os
from pathlib import Path
from astra_v2.story_mechanism_novelty import mechanism_novelty_queue

SCHEMA_VERSION = 1


def load_mechanisms(path):
    file = Path(path)
    if not file.exists():
        return set()
    data = json.loads(file.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("invalid_mechanism_ledger_schema")
    keys = data.get("reviewed_mechanisms")
    if not isinstance(keys, list) or any(not isinstance(k, str) or not k for k in keys):
        raise ValueError("invalid_mechanism_ledger_entries")
    return set(keys)


def save_mechanisms(path, mechanisms):
    file = Path(path)
    file.parent.mkdir(parents=True, exist_ok=True)
    keys = sorted(set(mechanisms))
    if any(not isinstance(k, str) or not k for k in keys):
        raise ValueError("invalid_mechanism_key")
    temp = file.with_name(file.name + ".tmp")
    try:
        temp.write_text(json.dumps({"schema_version": SCHEMA_VERSION,
                                    "reviewed_mechanisms": keys},
                                   indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temp, file)
    finally:
        if temp.exists():
            temp.unlink()


def queue_from_ledger(path, limit=None):
    """Read-only selection: recording review is a separate explicit action."""
    return mechanism_novelty_queue(load_mechanisms(path), limit=limit)


def record_reviewed(path, mechanism):
    """Record a completed review, never production approval."""
    if not isinstance(mechanism, str) or not mechanism:
        raise ValueError("invalid_mechanism_key")
    history = load_mechanisms(path)
    history.add(mechanism)
    save_mechanisms(path, history)
    return len(history)
