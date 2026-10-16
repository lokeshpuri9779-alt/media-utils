"""Opt-in, explicit character bootstrap for durable continuity snapshots.

Never derive identity from narration or auto-approve an episode.
"""
from copy import deepcopy

from astra_v2.character_registry import initial_character


def register_approved_character(snapshot, candidate):
    """Return an updated snapshot only for an explicitly approved character.

    Existing characters are left untouched; conflicting identities are rejected.
    Caller persists returned data through the established state writer.
    """
    if not isinstance(snapshot, dict) or snapshot.get("version") != 1:
        raise ValueError("invalid snapshot")
    characters = snapshot.get("characters")
    if not isinstance(characters, dict):
        raise ValueError("invalid character collection")
    if not isinstance(candidate, dict) or candidate.get("character_approved") is not True:
        raise ValueError("character approval required")
    character_id = candidate.get("character_id")
    name = candidate.get("character_name")
    if not isinstance(character_id, str) or not character_id.strip():
        raise ValueError("explicit character ID required")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("explicit character name required")
    if candidate.get("format") != "short":
        raise ValueError("shorts only")
    existing = characters.get(character_id)
    if existing is not None:
        if not isinstance(existing, dict) or existing.get("name") != name:
            raise ValueError("conflicting character identity")
        return deepcopy(snapshot)
    result = deepcopy(snapshot)
    result["characters"][character_id] = initial_character(character_id, name)
    return result
