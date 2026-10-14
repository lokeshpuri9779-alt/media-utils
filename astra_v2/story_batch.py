"""Deterministic, offline, non-publishing multi-story rehearsal plans.

These are authored story templates, not AI-generated unlimited narratives.
Each story has a stable cast, distinct beats and a validated prop.
"""
import hashlib
import json
from astra_v2.coordinated_development import build_ensemble_plan, verify_story_cast
from astra_v2.character_object_catalog import OBJECTS, prop

TEMPLATES = (
    {"title": "The Missing Cake", "cast": ("cat", "dog"), "prop": "cake",
     "genre": "mystery", "location": "bakery", "beats": ("The cat discovers a missing cake.", "The dog points at the crumbs.",
               "The cat follows the trail.", "The dog reacts to the surprise.",
               "The cat celebrates the discovery.")},
    {"title": "Robot's Lost Key", "cast": ("robot", "mouse"), "prop": "key",
     "genre": "adventure", "location": "workshop", "beats": ("The robot searches for a lost key.", "The mouse points at a clue.",
               "The robot carries the key.", "The mouse reacts in disbelief.",
               "The robot celebrates the recovery.")},
    {"title": "The Umbrella Mix-up", "cast": ("bear", "frog"), "prop": "umbrella",
     "genre": "slapstick", "location": "park", "beats": ("The bear finds a mysterious umbrella.", "The frog points at it.",
               "The bear carries the umbrella.", "The frog reacts to the mix-up.",
               "The bear celebrates the rescue.")},
    {"title": "The Alien's Telescope", "cast": ("alien", "owl"), "prop": "telescope",
     "genre": "discovery", "location": "observatory", "beats": ("The alien discovers a telescope.", "The owl points to the stars.",
               "The alien carries the telescope.", "The owl reacts to the view.",
               "The alien celebrates the discovery.")},
)
ACTIONS = ("approach", "point", "carry", "react", "celebrate")
# New locomotion cues are deliberately confined to selected story templates.
STORY_ACTIONS = {
    "The Missing Cake": ("walk", "point", "carry", "react", "celebrate"),
    "Robot's Lost Key": ("run", "point", "carry", "react", "celebrate"),
    "The Umbrella Mix-up": ("approach", "jump", "carry", "react", "dance"),
    "The Alien's Telescope": ("walk", "point", "carry", "jump", "dance"),
}


def build_story_batch(seed="astra-story-rehearsal", limit=4):
    if not isinstance(seed, str) or not seed.strip():
        raise ValueError("seed must be a nonempty string")
    if not isinstance(limit, int) or not 1 <= limit <= len(TEMPLATES):
        raise ValueError("limit outside template catalog")
    # Stable seeded ordering, with no duplicate template inside a batch.
    order = sorted(range(len(TEMPLATES)),
                   key=lambda i: hashlib.sha256(f"{seed}|{i}".encode()).digest())
    stories = []
    for i in order[:limit]:
        template = TEMPLATES[i]
        story_seed = f"{seed}|story-{i}"
        plan = build_ensemble_plan(story_seed, [list(template["cast"]) for _ in ACTIONS])
        prop_index = OBJECTS.index(template["prop"]) * 50
        for scene, action, narration in zip(plan["scenes"], STORY_ACTIONS[template["title"]], template["beats"]):
            scene.update(object_id=prop_index, object=prop(prop_index),
                         action=action, narration=narration, visual_style="storybook",
                         location=template["location"], genre=template["genre"],
                         caption=narration)
        plan.update(title=template["title"], genre=template["genre"], location=template["location"], pilot_type="offline_story_batch",
                    publication_allowed=False, quality_approved=False)
        verify_story_cast(plan)
        stories.append(plan)
    return {"seed": seed, "story_count": len(stories), "stories": stories,
            "publication_allowed": False, "quality_approved": False}


if __name__ == "__main__":
    import argparse
    from pathlib import Path
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", default="astra-story-rehearsal")
    parser.add_argument("--limit", type=int, default=4)
    parser.add_argument("--output", default="verification-output/story-batch.json")
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(build_story_batch(args.seed, args.limit), indent=2))
    print(f"Offline story batch written: {output}")
