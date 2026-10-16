"""Atomic-in-memory bootstrap and episode update, gated by verified publication.

No durable write is performed here. Caller must atomically persist returned state.
"""
from astra_v2.character_bootstrap import register_approved_character
from astra_v2.verified_character_memory import update_after_verified_publication


def apply_first_published_episode(snapshot, candidate, report):
    if not isinstance(candidate, dict) or not isinstance(report, dict):
        raise ValueError("candidate and report required")
    if candidate.get("character_approved") is not True:
        raise ValueError("approved character required")
    content_id = candidate.get("content_id")
    episode = candidate.get("character_episode")
    if not isinstance(content_id, str) or not content_id:
        raise ValueError("content ID required")
    if not isinstance(episode, dict) or episode.get("episode_id") != content_id:
        raise ValueError("matching character episode required")
    # Validate publication before any state change, including initialization.
    if report.get("outcome") != "published" or report.get("content_id") != content_id:
        raise ValueError("unverified publication")
    url = report.get("video_url")
    if not isinstance(url, str) or not url.startswith("https://www.youtube.com/watch?v="):
        raise ValueError("public video URL required")
    initialized = register_approved_character(snapshot, candidate)
    character = initialized["characters"][candidate["character_id"]]
    proposal = {"content_id": content_id, "character_id": candidate["character_id"],
                "character_revision": character["revision"]}
    return update_after_verified_publication(initialized, proposal, episode, report)
