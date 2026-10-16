"""Safe, explicit character snapshot exchange for ASTRA's astra-state branch.

This module does not publish, push, or change GitHub Actions workflows.
The existing serialized state-branch writer can copy this directory only after
a separate integration validates successful episode publication.
"""
import json
from pathlib import Path

from astra_v2.character_storage import load_character

SNAPSHOT_DIRECTORY = "character-continuity"
MANIFEST_VERSION = 1


def export_snapshot(directory, character_paths):
    """Write a validated manifest; reject duplicate IDs and missing states."""
    destination = Path(directory)
    states = {}
    for path in character_paths:
        state = load_character(path)
        if state is None:
            raise ValueError("missing character state")
        character_id = state.get("character_id")
        if not isinstance(character_id, str) or not character_id:
            raise ValueError("invalid character ID")
        if character_id in states:
            raise ValueError("duplicate character ID")
        states[character_id] = state
    snapshot = {"version": MANIFEST_VERSION, "characters": states}
    destination.parent.mkdir(parents=True, exist_ok=True)
    from tempfile import NamedTemporaryFile
    import os
    with NamedTemporaryFile("w", encoding="utf-8", dir=destination.parent, prefix=".continuity-", delete=False) as tmp:
        temp_path = Path(tmp.name)
        json.dump(snapshot, tmp, sort_keys=True, ensure_ascii=False, indent=2)
        tmp.flush()
        os.fsync(tmp.fileno())
    try:
        os.replace(temp_path, destination)
    finally:
        temp_path.unlink(missing_ok=True)
    return snapshot


def read_snapshot(path):
    with Path(path).open("r", encoding="utf-8") as stream:
        data = json.load(stream)
    if not isinstance(data, dict) or data.get("version") != MANIFEST_VERSION:
        raise ValueError("unsupported character snapshot")
    characters = data.get("characters")
    if not isinstance(characters, dict):
        raise ValueError("invalid character snapshot")
    for character_id, state in characters.items():
        if not isinstance(state, dict) or state.get("character_id") != character_id:
            raise ValueError("character identity mismatch")
        if type(state.get("revision")) is not int or state["revision"] < 0:
            raise ValueError("invalid character revision")
    return data
