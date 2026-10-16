"""Build opt-in episode manifests from explicit, approved story metadata.

No character identity is guessed from a title, genre, or narration.
This is a pure builder; publisher must still verify the actual YouTube upload.
"""


def build_character_manifests(candidate, character_state):
    if not isinstance(candidate, dict) or not isinstance(character_state, dict):
        raise ValueError("candidate and character state must be dictionaries")
    cid = candidate.get("content_id")
    character_id = candidate.get("character_id")
    if not isinstance(cid, str) or not cid.strip():
        raise ValueError("missing content ID")
    if not isinstance(character_id, str) or not character_id.strip():
        raise ValueError("candidate has no explicit character identity")
    if character_id != character_state.get("character_id"):
        raise ValueError("candidate character identity mismatch")
    if type(character_state.get("revision")) is not int or character_state["revision"] < 0:
        raise ValueError("invalid character revision")
    if candidate.get("character_approved") is not True:
        raise ValueError("character episode has not been approved")
    if candidate.get("format") != "short":
        raise ValueError("character episode must be a short")
    episode = candidate.get("character_episode")
    if not isinstance(episode, dict) or episode.get("episode_id") != cid:
        raise ValueError("approved episode does not match content")
    permitted = {"episode_id", "decision", "relationships", "resolve_conflicts", "new_conflicts"}
    if set(episode) - permitted:
        raise ValueError("unsupported character episode fields")
    proposal = {"content_id": cid, "character_id": character_id,
                "character_revision": character_state["revision"]}
    return proposal, dict(episode)
