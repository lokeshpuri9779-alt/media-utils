"""Zero-cost deterministic fiction generator with persistent-ID-compatible outputs.

Builds new narrative combinations from independently authored character,
setting, problem, reveal and resolution motifs. No paid model or network call.
Variation is finite and combinations do not guarantee literary originality.
"""
import hashlib
import itertools
from collections import Counter

CHARACTERS = [
    ("a retired astronaut", "Mara"), ("a young clockmaker", "Ivo"),
    ("a curious street musician", "Lina"), ("an elderly gardener", "Tara"),
    ("a shy delivery robot", "Pip"), ("a lighthouse keeper", "Noor"),
    ("a runaway apprentice", "Emi"), ("a traveling mapmaker", "Arun"),
]
PLACES = [
    ("a floating market", "ship"), ("an abandoned observatory", "planet"),
    ("a city beneath the ocean", "forest"), ("a silent mountain village", "forest"),
    ("a train station at the edge of time", "door"), ("a glass desert", "planet"),
    ("a forgotten moon colony", "planet"), ("a library inside a giant tree", "forest"),
]
MYSTERIES = [
    ("a lantern that glows whenever someone lies", "signal"),
    ("a clock that runs backwards only at dawn", "robot"),
    ("a sealed letter addressed to tomorrow", "door"),
    ("a map that changes whenever it rains", "signal"),
    ("a tiny machine that remembers lost voices", "robot"),
    ("a door that opens onto yesterday's weather", "door"),
    ("a musical note nobody else can hear", "signal"),
    ("a seed that grows only in moonlight", "forest"),
]
REVEALS = [
    "The strange object was carrying a warning from a forgotten friend.",
    "The signal was not a threat but an invitation to help someone.",
    "The mystery had been created to protect a hidden memory.",
    "The object responded to acts of kindness rather than commands.",
    "The clue pointed to a place everyone had stopped noticing.",
    "The apparent mistake was the final piece of an unfinished promise.",
]
RESOLUTIONS = [
    "They shared the discovery and the community finally found its way home.",
    "They chose to protect the secret until its rightful owner returned.",
    "They repaired what was broken and watched the first new light appear.",
    "They returned the lost message and reunited two people long separated.",
    "They turned the discovery into a place where strangers could help each other.",
    "They left a new clue behind so another traveler could continue the journey.",
]

def catalog(excluded_ids=None, limit=32):
    """Return deterministic unseen candidates, bounded to protect CPU render lanes."""
    excluded = set(excluded_ids or ())
    limit = max(0, min(int(limit), 128))
    if limit == 0:
        return []
    result = []
    seen_plot_keys = set()
    seen_mysteries = Counter()
    seen_characters = Counter()
    seen_places = Counter()
    seen_pairs = set()
    # Stable index ordering avoids random story IDs across independent CI jobs.
    combinations = itertools.product(
        range(len(CHARACTERS)), range(len(PLACES)), range(len(MYSTERIES)),
        range(len(REVEALS)), range(len(RESOLUTIONS))
    )
    # Prefer underused characters and locations based on confirmed publications.
    # The state branch is restored by the existing preload workflow.
    from astra_v2.control import STATE_FILE, read_json
    state = read_json(STATE_FILE)
    published_titles = [str(item.get("title", "")).casefold()
                        for group in ("published", "pending")
                        for item in (state.get(group) or {}).values()
                        if isinstance(item, dict)]
    character_usage = [sum(title.startswith(name.casefold() + " ") for title in published_titles)
                       for _, name in CHARACTERS]
    place_usage = [sum(place.removeprefix("a ").removeprefix("an ").casefold() in title
                       for title in published_titles) for place, _ in PLACES]
    combinations = sorted(combinations, key=lambda v: (
        character_usage[v[0]] + place_usage[v[1]],
        (v[0] * 31 + v[1] * 17 + v[2] * 13 + v[3] * 7 + v[4] * 3) % 101, v))
    for c, p, m, r, e in combinations:
        # Scramble sequential choices to avoid repeating the same cast/setting.
        if (c * 7 + p * 11 + m * 13 + r * 17 + e * 19) % 7 != 0:
            continue
        key = f"v1-{c}-{p}-{m}-{r}-{e}"
        cid = "rayvan-procedural-" + hashlib.sha256(key.encode()).hexdigest()[:16]
        if cid in excluded:
            continue
        # Reject cast/location swaps with identical mystery, twist and ending.
        plot_key = (m, r, e)
        if plot_key in seen_plot_keys:
            continue
        if seen_mysteries[m] >= max(1, (limit + len(MYSTERIES) - 1) // len(MYSTERIES)):
            continue
        if seen_characters[c] >= max(1, (limit + len(CHARACTERS) - 1) // len(CHARACTERS)):
            continue
        if seen_places[p] >= max(1, (limit + len(PLACES) - 1) // len(PLACES)):
            continue
        if (c, p) in seen_pairs:
            continue
        character, name = CHARACTERS[c]
        place, place_visual = PLACES[p]
        mystery, mystery_visual = MYSTERIES[m]
        reveal = REVEALS[r]
        resolution = RESOLUTIONS[e]
        object_name = mystery.split(" that ")[0].removeprefix("an ").removeprefix("a ")
        setting_name = place.removeprefix("an ").removeprefix("a ")
        title = f"{name} and the {object_name.title()} at the {setting_name.title()}"
        beats = [
            ("THE UNEXPECTED FIND", f"In {place}, {name}, {character}, discovered {mystery}.", mystery_visual, "DISCOVERY", "reveal"),
            ("THE FIRST CLUE", f"{name} traced the strange discovery to a hidden clue in {place}, and realized the mystery was only beginning.", place_visual, "THE CLUE", "build"),
            ("THE HIDDEN TRUTH", reveal, mystery_visual, "THE TRUTH", "twist"),
            ("A DIFFERENT ENDING", resolution, place_visual, "THE CHOICE", "payoff"),
        ]
        seen_plot_keys.add(plot_key)
        seen_mysteries[m] += 1
        seen_characters[c] += 1
        seen_places[p] += 1
        seen_pairs.add((c, p))
        result.append({
            "genre": "fiction", "kind": "procedural_fiction",
            "production_ready": True, "content_id": cid,
            "title": title, "hook": beats[0][0],
            "question": f"What happens when {name} discovers {mystery}?",
            "answer": reveal + " " + resolution, "source": "",
            "keywords": ["original procedural fiction", "mystery", "fantasy"],
            "story_beats": [
                {"headline": h, "speech": speech, "visual": visual,
                 "label": label, "story_beat": role, "sub": "AN ORIGINAL RAYVAN STORY",
                 "duration": 2.1}
                for h, speech, visual, label, role in beats
            ],
        })
        if len(result) >= limit:
            break
    return result
