"""Deterministic, offline, non-publishing multi-story rehearsal plans.

These are authored story templates, not AI-generated unlimited narratives.
Each story has a stable cast, distinct beats and a validated prop.
"""
import hashlib
import json
from astra_v2.coordinated_development import build_ensemble_plan, verify_story_cast
from astra_v2.character_object_catalog import OBJECTS, prop
from astra_v2.story_composition import compose, action_for_beat

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
    {"title": "The Runaway Lantern", "cast": ("fox", "rabbit"), "prop": "lamp",
     "genre": "chase", "location": "park", "beats": ("A lantern rolls away in the wind.", "The rabbit races after its glow.",
               "The fox catches the lantern near a tree.", "The rabbit notices a hidden trail.",
               "Together they light the way home.")},
    {"title": "The Clockwork Surprise", "cast": ("robot", "owl"), "prop": "clock",
     "genre": "puzzle", "location": "workshop", "beats": ("A workshop clock begins running backward.", "The owl spots a missing gear.",
               "The robot carries the clock to the workbench.", "A secret compartment opens.",
               "They discover a tiny music box inside.")},
    {"title": "The Picnic Switch", "cast": ("dog", "bear"), "prop": "backpack",
     "genre": "comedy", "location": "park", "beats": ("A picnic basket appears in the wrong place.", "The dog points toward a trail of crumbs.",
               "The bear lifts the basket with care.", "A curious squirrel has swapped the lunches.",
               "Everyone shares the picnic instead.")},
    {"title": "The Midnight Signal", "cast": ("alien", "cat"), "prop": "telescope",
     "genre": "science-fiction", "location": "observatory", "beats": ("A mysterious light flashes across the sky.", "The cat points toward a distant star.",
               "The alien adjusts the telescope.", "The signal turns into a friendly greeting.",
               "They send a bright reply into the night.")},
)
ACTIONS = ("approach", "point", "carry", "react", "celebrate")
# New locomotion cues are deliberately confined to selected story templates.
STORY_ACTIONS = {
    "The Missing Cake": ("walk", "point", "carry", "react", "celebrate"),
    "Robot's Lost Key": ("run", "point", "carry", "react", "celebrate"),
    "The Umbrella Mix-up": ("approach", "jump", "carry", "react", "dance"),
    "The Alien's Telescope": ("walk", "point", "carry", "jump", "dance"),
    "The Runaway Lantern": ("run", "run", "carry", "react", "walk"),
    "The Clockwork Surprise": ("approach", "point", "carry", "react", "dance"),
    "The Picnic Switch": ("walk", "point", "carry", "react", "celebrate"),
    "The Midnight Signal": ("approach", "point", "carry", "react", "celebrate"),
}


def build_story_batch(seed="astra-story-rehearsal", limit=4, episode=1, composed=True):
    if not isinstance(episode, int) or not 1 <= episode <= 100000:
        raise ValueError("episode outside supported range")
    if not isinstance(seed, str) or not seed.strip():
        raise ValueError("seed must be a nonempty string")
    if not isinstance(limit, int) or not 1 <= limit <= len(TEMPLATES):
        raise ValueError("limit outside template catalog")
    # Stable seeded ordering, with no duplicate template inside a batch.
    # Rotate through all authored plots before any template repeats.
    # The cycle is reproducible for a given seed; episodes within one cycle
    # get disjoint sets when the requested batch size divides catalog size.
    cycle = (episode - 1) // max(1, (len(TEMPLATES) // limit))
    slot = (episode - 1) % max(1, (len(TEMPLATES) // limit))
    order = sorted(range(len(TEMPLATES)),
                   key=lambda i: hashlib.sha256(f"{seed}|cycle-{cycle}|{i}".encode()).digest())
    selected = order[slot * limit:(slot + 1) * limit]
    if len(selected) < limit:
        selected += order[:limit - len(selected)]
    stories = []
    for i in selected:
        template = TEMPLATES[i]
        story_seed = f"{seed}|episode-{episode}|story-{i}"
        plan = build_ensemble_plan(story_seed, [list(template["cast"]) for _ in ACTIONS])
        prop_index = OBJECTS.index(template["prop"]) * 50
        beats = compose(template, seed, episode) if composed else template["beats"]
        actions = tuple(action_for_beat(j, narration) for j, narration in enumerate(beats)) if composed else STORY_ACTIONS[template["title"]]
        for scene, action, narration in zip(plan["scenes"], actions, beats):
            scene.update(object_id=prop_index, object=prop(prop_index),
                         action=action, narration=narration, visual_style="storybook",
                         location=template["location"], genre=template["genre"],
                         caption=narration)
        plan.update(title=template["title"], episode=episode, genre=template["genre"], location=template["location"], pilot_type="offline_story_batch", composition_mode="rule_based" if composed else "authored",
                    publication_allowed=False, quality_approved=False)
        verify_story_cast(plan)
        stories.append(plan)
    return {"seed": seed, "episode": episode, "story_count": len(stories), "stories": stories,
            "publication_allowed": False, "quality_approved": False}


if __name__ == "__main__":
    import argparse
    from pathlib import Path
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", default="astra-story-rehearsal")
    parser.add_argument("--limit", type=int, default=4)
    parser.add_argument("--episode", type=int, default=1)
    parser.add_argument("--authored", action="store_true", help="Use legacy authored regression fixtures")
    parser.add_argument("--output", default="verification-output/story-batch.json")
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(build_story_batch(args.seed, args.limit, args.episode, not args.authored), indent=2))
    print(f"Offline story batch written: {output}")
