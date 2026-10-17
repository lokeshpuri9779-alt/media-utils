"""Explicit opt-in character approvals for the local serialized story source.

The registry starts empty. Only a deliberately reviewed entry with exact
series and character identity can enable character memory. Never infer
approval from a protagonist name or generated narration.
"""
import json
from pathlib import Path


def approved_character_metadata(story, registry_path="astra_v2/approved_series_characters.json"):
    if not isinstance(story, dict):
        return {}
    path = Path(registry_path)
    if not path.is_file():
        return {}
    registry = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(registry, dict) or registry.get("version") != 1:
        raise ValueError("invalid approved series character registry")
    entries = registry.get("characters")
    if not isinstance(entries, dict):
        raise ValueError("invalid approved character entries")
    series_id = story.get("series_id")
    record = entries.get(series_id)
    if record is None:
        return {}
    if not isinstance(record, dict) or record.get("approved") is not True:
        return {}
    character_id, name = record.get("character_id"), record.get("character_name")
    if not isinstance(character_id, str) or not character_id.strip():
        raise ValueError("approved character ID required")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("approved character name required")
    if name != story.get("protagonist_name"):
        raise ValueError("approved character name does not match story protagonist")
    cid = story.get("content_id")
    if not isinstance(cid, str) or not cid.startswith("rayvan-season-01-episode-"):
        raise ValueError("unrecognized approved episode identity")
    return {
        "character_id": character_id,
        "character_name": name,
        "character_approved": True,
        "character_episode": {"episode_id": cid},
    }
