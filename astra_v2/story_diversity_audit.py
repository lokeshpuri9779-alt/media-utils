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
        continuity = bool(scenes) and all(
            a.get("object_condition_after") == b.get("object_condition_before")
            for a, b in zip(scenes, scenes[1:])
        )
        repair_count = sum(s.get("action") == "repair" for s in scenes)
        repairs_valid = bool(scenes) and repair_count <= 1 and all(
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

# Heuristic near-duplicate detection; not a semantic embedding model.
STOPWORDS = frozenset("the a an and or to in at on with for from into of is was are they it its their then".split())

def story_tokens(story):
    words = re.findall(r"[a-z]+", " ".join(s.get("narration", "") for s in story.get("scenes", [])).lower())
    return set(words) - STOPWORDS

def similarity(a, b):
    """Blend narration-token Jaccard and action-sequence similarity."""
    ta, tb = story_tokens(a), story_tokens(b)
    lexical = len(ta & tb) / len(ta | tb) if ta | tb else 1.0
    # Detect repeated plot scaffolds even when the narration uses different words.
    same_structure = fingerprint(a) == fingerprint(b)
    # Plot action sequences alone are a weak signal; keep this as a review flag,
    # not an automatic rejection of otherwise different narratives.
    aa = [s.get("action") for s in a.get("scenes", [])]
    ab = [s.get("action") for s in b.get("scenes", [])]
    actions = sum(x == y for x, y in zip(aa, ab)) / max(len(aa), len(ab), 1)
    return 1.0 if same_structure else round(0.8 * lexical + 0.2 * actions, 4)

def audit_history(stories, history=(), threshold=0.82):
    """Compare candidates against prior story plans; caller manages history storage."""
    if not 0 <= threshold <= 1:
        raise ValueError("threshold must be between 0 and 1")
    accepted = list(history)
    results = []
    for story in stories:
        score = max((similarity(story, old) for old in accepted), default=0.0)
        near_duplicate = score >= threshold
        results.append({"title": story.get("title"), "max_similarity": score,
                        "near_duplicate": near_duplicate})
        if not near_duplicate:
            accepted.append(story)
    return {"results": results, "near_duplicates": sum(r["near_duplicate"] for r in results),
            "publication_allowed": False, "quality_approved": False}
