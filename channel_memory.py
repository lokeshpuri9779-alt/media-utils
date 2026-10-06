from __future__ import annotations

"""Per-channel bounded learning memory for Astra."""

from copy import deepcopy
from datetime import datetime, timezone

from channel_state import channel_key
from distribution import distribution_state
from evolution import evolution_state, optimization_policy


def _belongs(entry: dict, key: str) -> bool:
    stamped = str(entry.get("channel_key") or "").strip().lower()
    # Legacy unstamped history belongs to the original RAYVAN profile only.
    return stamped == key or (not stamped and key == "rayvan")


def channel_dataset(data: dict, key: str | None = None) -> dict:
    key = (key or channel_key()).strip().lower()
    scoped = deepcopy(data)
    scoped["videos"] = {
        vid: entry for vid, entry in (data.get("videos") or {}).items()
        if _belongs(entry, key)
    }
    return scoped


def build_channel_memory(data: dict, key: str | None = None) -> dict:
    key = (key or channel_key()).strip().lower()
    scoped = channel_dataset(data, key)
    evo = evolution_state(scoped)
    scoped["evolution"] = evo
    policy = optimization_policy(scoped)
    dist = distribution_state(scoped)

    genres = {}
    for entry in scoped.get("videos", {}).values():
        genre = str(entry.get("genre") or "unknown")
        genres[genre] = genres.get(genre, 0) + 1

    return {
        "channel_key": key,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "video_count": len(scoped.get("videos", {})),
        "genre_counts": genres,
        "evolution": evo,
        "optimization_policy": policy,
        "distribution": dist,
        "guardrails": {
            "cross_channel_training": False,
            "owner_excluded_samples_respected": True,
            "bounded_learning_only": True,
        },
    }


def refresh_channel_memory(data: dict, key: str | None = None) -> dict:
    key = (key or channel_key()).strip().lower()
    memory = build_channel_memory(data, key)
    data.setdefault("channel_memories", {})[key] = memory
    # Existing ranking code consumes these top-level views. Mirror only the
    # active channel's bounded state to keep backward compatibility.
    data["evolution"] = memory["evolution"]
    data["optimization_policy"] = memory["optimization_policy"]
    return memory


def active_memory(data: dict) -> dict:
    key = channel_key()
    existing = (data.get("channel_memories") or {}).get(key)
    return existing if isinstance(existing, dict) else build_channel_memory(data, key)
