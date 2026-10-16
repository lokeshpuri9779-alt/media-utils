"""Opt-in continuity context for deterministic ASTRA story proposals.

The caller supplies a durable character-state path and records an episode only
after it is accepted. Generating a proposal never mutates continuity history.
"""
from astra_v2.character_storage import load_character, record_episode
from astra_v2.genre_story_supply import genre_proposal


def continuity_proposal(index, character_path, scenario_index=None, structure_index=None):
    state = load_character(character_path)
    if state is None:
        raise ValueError("initialize character before generating episodes")
    proposal = genre_proposal(index, scenario_index=scenario_index, structure_index=structure_index)
    context = []
    if state["episode_ids"]:
        context.append("Earlier episodes: " + ", ".join(state["episode_ids"][-3:]))
    if state["relationships"]:
        context.append("Established relationships: " + "; ".join(
            name + " is " + status for name, status in sorted(state["relationships"].items())
        ))
    if state["unresolved_conflicts"]:
        context.append("Still unresolved: " + "; ".join(state["unresolved_conflicts"]))
    if state["decisions"]:
        context.append("Previous choice: " + state["decisions"][-1]["decision"])
    proposal["character_id"] = state["character_id"]
    proposal["character_revision"] = state["revision"]
    proposal["continuity_context"] = context
    proposal["production_ready"] = False
    return proposal


def accept_character_episode(character_path, proposal, episode):
    """Explicit opt-in continuity commit; never called during proposal creation."""
    if proposal.get("production_ready") is not False:
        raise ValueError("continuity commit requires isolated draft proposal")
    if not isinstance(episode, dict) or episode.get("episode_id") != proposal.get("content_id"):
        raise ValueError("episode must identify the accepted proposal")
    state = load_character(character_path)
    if state is None or state["character_id"] != proposal.get("character_id"):
        raise ValueError("character mismatch")
    return record_episode(character_path, episode, proposal["character_revision"])
