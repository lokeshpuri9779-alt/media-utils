"""Deterministic, publication-isolated continuity registry for recurring characters.

Callers persist the returned JSON-compatible state in their own durable store.
Updates require an expected revision so stale writers cannot silently overwrite arcs.
"""
from copy import deepcopy

MAX_EVENTS = 64


def initial_character(character_id, name):
    if not isinstance(character_id, str) or not character_id.strip():
        raise ValueError("character_id is required")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("name is required")
    return {
        "character_id": character_id,
        "name": name,
        "revision": 0,
        "episode_ids": [],
        "relationships": {},
        "unresolved_conflicts": [],
        "decisions": [],
    }


def apply_episode(state, episode, expected_revision):
    """Return a new state; reject stale revisions and repeated episodes."""
    if not isinstance(state, dict) or not isinstance(episode, dict):
        raise ValueError("state and episode must be dictionaries")
    if type(expected_revision) is not int or state.get("revision") != expected_revision:
        raise ValueError("stale character revision")
    episode_id = episode.get("episode_id")
    if not isinstance(episode_id, str) or not episode_id.strip():
        raise ValueError("episode_id is required")
    if episode_id in state["episode_ids"]:
        raise ValueError("duplicate episode")
    result = deepcopy(state)
    for person, relationship in episode.get("relationships", {}).items():
        if not isinstance(person, str) or not person.strip() or not isinstance(relationship, str):
            raise ValueError("invalid relationship")
        result["relationships"][person] = relationship
    conflicts = result["unresolved_conflicts"]
    for conflict in episode.get("resolve_conflicts", []):
        if conflict not in conflicts:
            raise ValueError("cannot resolve unknown conflict")
        conflicts.remove(conflict)
    for conflict in episode.get("new_conflicts", []):
        if not isinstance(conflict, str) or not conflict.strip() or conflict in conflicts:
            raise ValueError("invalid or duplicate conflict")
        conflicts.append(conflict)
    decision = episode.get("decision")
    if decision is not None:
        if not isinstance(decision, str) or not decision.strip():
            raise ValueError("invalid decision")
        result["decisions"].append({"episode_id": episode_id, "decision": decision})
        result["decisions"] = result["decisions"][-MAX_EVENTS:]
    result["episode_ids"].append(episode_id)
    result["revision"] += 1
    return result
