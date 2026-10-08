"""Zero-cost creative routing: local generative composer by default.

OmniRoute is a routing *interface*, not a claim that a provider is connected.
No remote endpoint is called. A paid/remote route must be separately built,
reviewed and explicitly authorized.
"""
import hashlib
import itertools

SETTINGS = [
    ("abandoned observatory", "planet", "the sky", "stars"),
    ("silent orbital station", "ship", "the window", "constellations"),
    ("forgotten underground library", "door", "the ceiling", "lights"),
    ("last greenhouse", "forest", "the glass", "seeds"),
]
PROTAGONISTS = [
    ("Mara", "an apprentice mechanic"),
    ("Ivo", "a curious archivist"),
    ("Sera", "a night-shift gardener"),
    ("Niko", "a young radio operator"),
]
DISCOVERIES = [
    ("a message from tomorrow", "signal", "a warning about a coming blackout"),
    ("a machine that remembers rain", "robot", "a map of the missing rivers"),
    ("a small ship with no passengers", "ship", "a recording of an unknown voice"),
    ("a door that appears at midnight", "door", "instructions to restore the night sky"),
]
ENDING = [
    ("the city", "a thousand windows lit up one by one"),
    ("the station", "the forgotten clocks began ticking again"),
    ("the neighborhood", "people came outside to see the real stars"),
    ("the garden", "the first green shoots appeared at dawn"),
]


def catalog(excluded_ids=(), max_candidates=12, excluded_titles=()):
    """Produce a rotating inventory of distinct structured narrative proposals.

    Deterministic combinations allow stable IDs, replay safety and zero spend.
    The Creative Director can reject any candidate. This is NOT an LLM.
    """
    blocked = set(excluded_ids)
    prior_titles = [str(title).casefold() for title in excluded_titles]
    used_settings = set()
    used_discoveries = set()
    for previous in prior_titles:
        for idx, (place, *_rest) in enumerate(SETTINGS):
            if place in previous:
                used_settings.add(idx)
        for idx, (discovery, *_rest) in enumerate(DISCOVERIES):
            if discovery in previous:
                used_discoveries.add(idx)
    proposals = []
    used_titles = set()
    combinations = itertools.product(range(len(SETTINGS)), range(len(PROTAGONISTS)),
                                      range(len(DISCOVERIES)), range(len(ENDING)))
    for a, b, c, d in combinations:
        # Spread candidates across combinations rather than changing only names.
        if (a + b + c + d) % 3:
            continue
        # Ensure discovery and payoff relate to the setting; a purely random
        # mix can produce visually polished but narratively incoherent stories.
        if (a == 3 and c == 2) or (a == 2 and c == 2):
            continue
        # Avoid recycling the same location or central story mechanism across uploads.
        if a in used_settings or c in used_discoveries:
            continue
        place, visual, surface, objects = SETTINGS[a]
        name, role = PROTAGONISTS[b]
        discovery, clue_visual, revelation = DISCOVERIES[c]
        community, payoff = ENDING[d]
        cid = "rayvan-omniroute-local-" + hashlib.sha256(
            f"{a}:{b}:{c}:{d}".encode()).hexdigest()[:18]
        if cid in blocked:
            continue
        # Include the actual discovery and protagonist, rather than reusing
        # one headline for every different plot at a location.
        title = f"{name} and {discovery.title()} at the {place.title()}"
        if len(title) > 85:
            title = f"{name}: {discovery.title()}"
        # Repeated titles look like mass-produced uploads; reject duplicates.
        normalized_title = title.casefold().strip()
        if normalized_title in used_titles:
            continue
        used_titles.add(normalized_title)
        beats = [
            (f"THE {place.upper()}", f"{name}, {role}, discovered {discovery} inside the {place}. Nobody else had entered that place in years. Yet fresh marks on the floor led straight to the discovery, as if someone had arrived only moments earlier.",
             visual, "THE DISCOVERY", "reveal"),
            ("THE CLUE", f"Every night, {surface} changed, and the {objects} seemed to point toward something nobody could explain. {name} stayed awake to watch. At first nothing happened. Then the pattern repeated, precisely when the old clock stopped, and one detail moved against the others.",
             clue_visual, "FOLLOW THE SIGNAL", "build"),
            ("THE HIDDEN MESSAGE", f"The clue revealed {revelation}, but it would only work if someone believed the impossible. {name} checked the pattern twice, searching for a mistake. There was none. The message described something that had not happened yet, and the warning left almost no time to act.",
             clue_visual, "THE TWIST", "twist"),
            ("ONE SMALL CHOICE", f"{name} shared the discovery with {community}. Some laughed. Others were frightened. But one person listened, then another, until everyone understood what was at stake. Together they followed the warning, and {payoff}. {name} looked back at the place where it began, wondering who had sent the message.",
             visual, "THE PAYOFF", "payoff"),
        ]
        proposals.append({
            "genre": "fiction", "kind": "microfiction",
            "production_ready": True, "content_id": cid, "title": title,
            "hook": beats[0][0],
            "question": f"What secret is hiding inside the {place}?",
            "answer": f"{name} uncovers {discovery} and helps {community} change forever.",
            "source": "", "keywords": ["original science fiction", "microfiction"],
            "story_beats": [
                {"headline": h, "speech": s, "visual": v, "label": label,
                 "story_beat": role, "sub": "AN ORIGINAL RAYVAN STORY",
                 "duration": 1.0}
                for h, s, v, label, role in beats
            ],
        })
        if len(proposals) >= max_candidates:
            break
    return proposals
