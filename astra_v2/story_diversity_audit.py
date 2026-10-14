"""Offline-only story diversity audit. No publication permissions."""
import hashlib
import json
import re

def fingerprint(story):
    """Structural fingerprint independent of titles and character names."""
    scenes = story.get("scenes", [])
    structure = {
        "genre": story.get("genre", ""),
        "location": story.get("location", ""),
        "actions": [s.get("action", "") for s in scenes],
        "states": [[s.get("object_condition_before"), s.get("object_condition_after")] for s in scenes],
        "beats": [re.sub(r"\b(cat|dog|alien|robot|owl|bear|frog|fox|rabbit|mouse)\b", "CHARACTER", s.get("narration", "").lower()) for s in scenes],
    }
    return hashlib.sha256(json.dumps(structure, sort_keys=True).encode()).hexdigest()

def audit(stories):
    seen = set()
    results = []
    for story in stories:
        key = fingerprint(story)
        repeated = key in seen
        seen.add(key)
        scenes = story.get("scenes", [])
        continuity = all(
            a.get("object_condition_after") == b.get("object_condition_before")
            for a, b in zip(scenes, scenes[1:])
        )
        repair_count = sum(s.get("action") == "repair" for s in scenes)
        repairs_valid = repair_count <= 1 and all(
            s.get("object_condition_after") == "repaired"
            for s in scenes[next((i for i,s in enumerate(scenes) if s.get("action") == "repair"), len(scenes)):]
        )
        results.append({"title": story.get("title"), "fingerprint": key,
                        "duplicate": repeated, "continuity_ok": continuity,
                        "repair_sequence_ok": repairs_valid,
                        "creative_quality_verified": False,
                        "publication_allowed": False})
    return {"results": results, "publication_allowed": False,
            "quality_approved": False,
            "structural_duplicates": sum(r["duplicate"] for r in results)}

if __name__ == "__main__":
    from astra_v2.story_batch import build_story_batch
    print(json.dumps(audit(build_story_batch()["stories"]), indent=2))
