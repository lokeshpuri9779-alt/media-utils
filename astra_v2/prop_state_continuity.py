"""Conservative object-condition tracking for authored Studio fiction beats.

This metadata does not change rendering or bypass editorial quality gates.
Only explicit condition declarations or unambiguous action verbs alter state.
"""
import re

CONDITIONS = {"intact", "damaged", "repaired"}
REPAIR = re.compile(r"\b(?:repaired|fixed|mended|restored)\b", re.I)
DAMAGE = re.compile(r"\b(?:broke|broken|cracked|damaged|shattered)\b", re.I)


def assign_prop_states(shots):
    """Attach a consistent condition timeline without mutating input shots."""
    states = {}
    result = []
    for shot in shots:
        item = dict(shot)
        prop = item.get("story_prop")
        if not prop:
            result.append(item)
            continue
        # Explicit instance IDs distinguish two objects of the same type.
        # Legacy stories without IDs continue sharing state by prop type.
        instance_id = item.get("story_prop_id")
        if instance_id is not None and (not isinstance(instance_id, str) or not instance_id.strip()):
            raise ValueError("invalid_story_prop_id")
        key = (prop, instance_id.strip() if instance_id is not None else None)
        state = states.get(key)
        declared = item.get("story_prop_state")
        if declared is not None:
            if declared not in CONDITIONS:
                raise ValueError("unsupported_story_prop_state")
            state = declared
        else:
            # Condition changes only on explicit past-tense narration, not
            # ambiguous 'repair' intentions or generic action labels.
            speech = str(item.get("speech") or "")
            if REPAIR.search(speech):
                if state == "damaged":
                    item["story_prop_repair_transition"] = True
                state = "repaired"
            elif DAMAGE.search(speech):
                state = "damaged"
            if state is not None:
                item["story_prop_state"] = state
        states[key] = state
        result.append(item)
    return result
