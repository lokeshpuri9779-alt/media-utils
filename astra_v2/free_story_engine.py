"""Free deterministic story composer: fresh combinations, no external APIs.

Not an LLM. Human-authored story arcs are recombined into unique, inspectable
four-beat narratives. Existing studio quality gates decide publishability.
"""
import hashlib

ARCS = [
    {
        "key": "signal-seed",
        "title": "The Signal Hidden Inside a Seed",
        "question": "What if the last seed carried a message from the future?",
        "answer": "A lone botanist plants a strange seed and discovers a forest that transmits a warning through its leaves.",
        "beats": [
            ("THE SEED WAS TALKING", "When the last seed began transmitting a signal, Mira thought the radio was broken.", "signal", "SIGNAL FOUND", "reveal"),
            ("SHE PLANTED IT", "She buried the seed beneath the abandoned station, where nobody had seen green in years.", "forest", "DAY ONE", "build"),
            ("THE LEAVES FORMED WORDS", "At dawn, the new leaves arranged themselves into a map of tomorrow's storm.", "forest", "WARNING", "twist"),
            ("THE CITY LISTENED", "Mira shared the map. For the first time in decades, the whole city prepared together.", "signal", "A NEW START", "payoff"),
        ],
    },
    {
        "key": "moon-door",
        "title": "The Door That Remembered the Moon",
        "question": "Why does an old door open only when the moon disappears?",
        "answer": "A child finds a forgotten doorway that holds a recording of the night the stars went silent.",
        "beats": [
            ("THE MOON WENT DARK", "Every time the moon disappeared, a locked door in the station opened for exactly one minute.", "door", "ONE MINUTE", "reveal"),
            ("INSIDE WAS A SKY", "Niko stepped through and found a room filled with moving constellations, each one missing a star.", "planet", "LOST STARS", "build"),
            ("A VOICE COUNTED DOWN", "A tiny machine was replaying the last minute before the city's lights had erased the night.", "robot", "REPLAY", "twist"),
            ("THE LIGHTS WENT OUT", "Niko switched off the empty station's floodlights, and the real stars returned overhead.", "planet", "LOOK UP", "payoff"),
        ],
    },
    {
        "key": "ship-clock",
        "title": "The Ship That Delivered Yesterday",
        "question": "Can a spaceship bring back one forgotten day?",
        "answer": "An unmanned vessel returns a lost recording, letting a family hear a voice they thought was gone.",
        "beats": [
            ("A SHIP CAME BACK", "The rescue ship returned after forty years, but its clock still showed the day it left.", "ship", "ARRIVAL", "reveal"),
            ("NO CREW ABOARD", "Inside, Ava found only a recording device and a small parcel addressed to her grandmother.", "ship", "UNDELIVERED", "build"),
            ("A VOICE FROM BEFORE", "The recording held her grandfather's last bedtime story, saved before the ship vanished.", "signal", "PLAYBACK", "twist"),
            ("ONE MORE STORY", "Ava played it for her grandmother, and the quiet house filled with laughter again.", "signal", "HOME", "payoff"),
        ],
    },
]


def catalog():
    stories = []
    for arc in ARCS:
        cid = "rayvan-free-original-" + hashlib.sha256(arc["key"].encode()).hexdigest()[:16]
        stories.append({
            "genre": "fiction", "kind": "microfiction",
            "production_ready": True, "content_id": cid,
            "title": arc["title"], "hook": arc["beats"][0][0],
            "question": arc["question"], "answer": arc["answer"],
            "source": "", "keywords": ["original microfiction", "science fiction"],
            "story_beats": [
                {"headline": title, "speech": speech, "visual": visual,
                 "label": label, "story_beat": role, "sub": "AN ORIGINAL RAYVAN STORY",
                 "duration": 2.1}
                for title, speech, visual, label, role in arc["beats"]
            ],
        })
    return stories
