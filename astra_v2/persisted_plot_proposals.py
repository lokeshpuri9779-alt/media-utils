"""Read-only proposal generation excluding structures from persisted story history.

This module never approves or publishes stories. Caller must persist history
through the existing state lifecycle; this function only consumes it.
"""
from astra_v2.proposal_history import load_history
from astra_v2.plot_first_proposals import proposals, structural_key


def proposals_with_history(limit=100, publisher_path="astra_v2_state.json",
                           story_path="astra_story_history.json"):
    history = load_history(publisher_path=publisher_path, story_path=story_path)
    structures = {key for record in history if (key := structural_key(record)) is not None}
    fingerprints = {record["plot_fingerprint"] for record in history
                    if isinstance(record.get("plot_fingerprint"), str)
                    and record["plot_fingerprint"]}
    return proposals(limit=limit, excluded_plot_hashes=fingerprints,
                     excluded_structural_keys=structures)
