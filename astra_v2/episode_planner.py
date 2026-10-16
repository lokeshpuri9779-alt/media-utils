"""Planning and novelty policy for proposed ASTRA series episodes.

Planning never grants publication approval. A proposal remains a draft until
separate editorial, render, and publisher quality gates pass.
"""
import hashlib
import json
import re


def _normalize(value):
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", str(value).casefold()).split())


def fingerprint(episode):
    """Stable narrative fingerprint, independent of cosmetic title changes."""
    scenes = episode.get("scenes") or []
    narrative = " ".join(_normalize(scene.get("cause", "") + " " +
                                  scene.get("action", "") + " " +
                                  scene.get("consequence", "")) for scene in scenes)
    return hashlib.sha256(narrative.encode("utf-8")).hexdigest()


def known_fingerprints(state):
    """Read confirmed, reserved and pending fingerprints from persistent state."""
    known = set()
    for bucket in ("published", "reserved", "pending"):
        entries = state.get(bucket) or {}
        if not isinstance(entries, dict):
            continue
        for entry in entries.values():
            if isinstance(entry, dict):
                for key in ("plot_fingerprint", "plot_hash"):
                    if entry.get(key):
                        known.add(str(entry[key]))
    return known


def plan_episode(series_id, episode_number, scenes, state=None):
    """Validate a causal episode outline without approving it for production."""
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,63}", str(series_id)):
        raise ValueError("invalid_series_id")
    if type(episode_number) is not int or episode_number < 1:
        raise ValueError("invalid_episode_number")
    if not isinstance(scenes, list) or len(scenes) < 3:
        raise ValueError("episode_requires_three_or_more_scenes")
    normalized = []
    for scene in scenes:
        if not isinstance(scene, dict):
            raise ValueError("invalid_scene")
        fields = ("cause", "action", "consequence")
        if any(not isinstance(scene.get(k), str) or not scene[k].strip() for k in fields):
            raise ValueError("scene_missing_causal_fields")
        normalized.append({k: scene[k].strip() for k in fields})
    proposal = {"series_id": series_id, "episode": episode_number,
                "scenes": normalized, "production_ready": False,
                "kind": "unreviewed_episode_plan"}
    proposal["plot_fingerprint"] = fingerprint(proposal)
    if proposal["plot_fingerprint"] in known_fingerprints(state or {}):
        raise ValueError("episode_plot_already_used")
    return proposal
