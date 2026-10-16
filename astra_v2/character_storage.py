"""Atomic local JSON persistence for ASTRA character continuity.

The caller must provide a durable workspace path. Single-process optimistic
revision checks prevent stale sequential writes; cross-process locking is not
provided, so concurrent workers must serialize writes externally.
"""
import json
import os
from pathlib import Path
import tempfile

from astra_v2.character_registry import apply_episode, initial_character


def load_character(path):
    path = Path(path)
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as stream:
        state = json.load(stream)
    if not isinstance(state, dict) or type(state.get("revision")) is not int:
        raise ValueError("invalid character state")
    return state


def save_character(path, state, expected_revision):
    path = Path(path)
    current = load_character(path)
    actual_revision = None if current is None else current["revision"]
    if actual_revision != expected_revision:
        raise ValueError("stale stored character revision")
    if type(state.get("revision")) is not int:
        raise ValueError("invalid character revision")
    if state["revision"] != (0 if current is None else current["revision"] + 1):
        raise ValueError("invalid revision transition")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".character-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(state, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def record_episode(path, episode, expected_revision):
    state = load_character(path)
    if state is None:
        raise ValueError("character must be initialized")
    updated = apply_episode(state, episode, expected_revision)
    save_character(path, updated, expected_revision)
    return updated


def initialize_character(path, character_id, name):
    state = initial_character(character_id, name)
    save_character(path, state, None)
    return state
