"""Fail-closed character memory updates from independently verified publication.

Only a verified publication report with matching content and public video URL
can advance an existing character. The caller must persist the returned snapshot.
"""
from copy import deepcopy
from astra_v2.character_registry import apply_episode


def update_after_verified_publication(snapshot, proposal, episode, report):
    if not all(isinstance(value, dict) for value in (snapshot, proposal, episode, report)):
        raise ValueError("invalid publication continuity inputs")
    if snapshot.get("version") != 1 or not isinstance(snapshot.get("characters"), dict):
        raise ValueError("invalid continuity snapshot")
    content_id = proposal.get("content_id")
    if not isinstance(content_id, str) or not content_id:
        raise ValueError("missing content identity")
    if report.get("outcome") != "published" or report.get("content_id") != content_id:
        raise ValueError("publication not verified for proposal")
    video_url = report.get("video_url")
    if not isinstance(video_url, str) or not video_url.startswith("https://www.youtube.com/watch?v="):
        raise ValueError("verified public YouTube URL required")
    if episode.get("episode_id") != content_id:
        raise ValueError("episode does not match published content")
    character_id = proposal.get("character_id")
    state = snapshot["characters"].get(character_id)
    if state is None:
        raise ValueError("unknown character")
    if state.get("revision") != proposal.get("character_revision"):
        raise ValueError("stale character history")
    updated = deepcopy(snapshot)
    updated["characters"][character_id] = apply_episode(state, episode, state["revision"])
    return updated
