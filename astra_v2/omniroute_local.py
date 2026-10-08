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
    # A serialized season advances only after the previous episode has been
    # confirmed in the published/reserved identity set. No random resets.
    # One canonical arc is deliberately stable across runs and workers.
    prior_titles = [str(title).casefold() for title in excluded_titles]
    used_settings = set()
    used_discoveries = set()
    proposals = []
    used_titles = set()
    combinations = itertools.product(range(len(SETTINGS)), range(len(PROTAGONISTS)),
                                      range(len(DISCOVERIES)), range(len(ENDING)))
    # Lock the first season to one protagonist, location and mystery.
    # Episodes are numbered by a stable season-specific identifier.
    for a, b, c, d in combinations:
        if (a, b, c) != (0, 0, 0):
            continue
        # Spread candidates across combinations rather than changing only names.
        # Do not skip episode numbers in a serialized season.
        # Ensure discovery and payoff relate to the setting; a purely random
        # mix can produce visually polished but narratively incoherent stories.
        if (a == 3 and c == 2) or (a == 2 and c == 2):
            continue
        # Recurring locations and characters are intentional in a series.
        place, visual, surface, objects = SETTINGS[a]
        name, role = PROTAGONISTS[b]
        discovery, clue_visual, revelation = DISCOVERIES[c]
        community, payoff = ENDING[d]
        episode = d + 1
        cid = f"rayvan-season-01-episode-{episode:02d}"
        # Pre-render episodes independently in parallel. Publication order
        # is enforced separately by the publisher, never by this catalog.
        if cid in blocked:
            continue
        # Include the actual discovery and protagonist, rather than reusing
        # one headline for every different plot at a location.
        title = f"The Tomorrow Signal | S1 E{episode:02d} | {name}"
        if len(title) > 85:
            title = f"{name}: {discovery.title()}"
        # Repeated titles look like mass-produced uploads; reject duplicates.
        normalized_title = title.casefold().strip()
        if normalized_title in used_titles:
            continue
        used_titles.add(normalized_title)
        # Four complete acts, with a narration budget calibrated for a
        # 55-59 second Short. TTS timing is checked by the renderer.
        beats = [
            (f"THE {place.upper()}",
             f"{name}, {role}, found {discovery} inside the {place}. The building had been sealed for years. But fresh footprints crossed the dust, and one set stopped right beside the strange object.",
             visual, "THE DISCOVERY", "reveal"),
            ("THE CLUE",
             f"Each night, {surface} changed while the {objects} shifted into a new pattern. {name} watched until midnight. The clock stopped. Then one mark moved backward, pointing to a place no map showed.",
             clue_visual, "FOLLOW THE SIGNAL", "build"),
            ("THE HIDDEN MESSAGE",
             f"The pattern contained {revelation}. {name} checked it twice. Every detail matched, except the final line: the disaster would begin before sunrise. There was no time to ask who had sent it.",
             clue_visual, "THE TWIST", "twist"),
            ("ONE SMALL CHOICE",
             f"{name} warned {community}. Nobody believed the story at first. Then the lights flickered, exactly as predicted. Neighbors followed the instructions together, and {payoff}. But the mysterious sender never revealed their name.",
             visual, "THE PAYOFF", "payoff"),
        ]
        # Each installment advances the same mystery instead of replaying
        # the discovery with a different closing sentence.
        episode_arcs = {
            1: (
                "Mara found a radio blinking inside the abandoned observatory. It spoke tomorrow's date, then warned that every light in the city would go out before dawn. The radio had no batteries. Someone had scratched Mara's name into its metal case.",
                "She traced a cable beneath the floorboards and discovered a room that did not appear on the building plans. A second radio waited inside, broadcasting her own voice. It was counting down from sixty, although she had never recorded the message.",
                "When Mara unplugged the cable, the countdown continued. Outside, the first streetlights went dark. Her recorded voice whispered that the blackout was not an accident. Someone was using the city's power to open a door beneath the observatory.",
                "Mara grabbed the radio and ran for the stairs. A heavy door slammed shut behind her. The final message arrived in a voice she recognized: her missing brother's. He said, 'Do not let them turn the lights back on.'"
            ),
            2: (
                "Mara's missing brother had just spoken through a radio that predicted tomorrow. She followed his warning and left the city dark. Beneath the observatory, the locked door began to glow, and something knocked from the other side.",
                "She found an emergency generator, but its switch was marked with the same symbol carved into her brother's old notebook. His last entry said the door opened only when the city was fully powered. Someone had lied about the blackout.",
                "A stranger arrived carrying a photograph of Mara standing beside the door. The picture was dated next week. In it, her brother stood behind her, older than he should have been, holding a key made of blue glass.",
                "Mara refused to start the generator. The stranger smiled and pressed a hidden switch. Lights returned across the city, one block at a time. From beneath the floor, the knocking stopped. Then a voice said, 'Thank you for opening it.'"
            ),
            3: (
                "The city's lights came back, and the observatory door opened by itself. Mara expected to find her brother. Instead she saw the same city, abandoned and silent, under a sky without stars. Footprints led from the doorway toward her.",
                "A small clock lay on the floor, ticking backward. Its face displayed tomorrow's date. Mara stepped across the threshold and heard the radio announce a new warning: only one version of the city could survive sunrise.",
                "She found her brother's jacket hanging on a chair, but the name stitched inside belonged to the stranger. On the wall were hundreds of photographs showing Mara making different choices. Every picture ended with the same empty streets.",
                "Mara turned back toward the door. On the other side stood another Mara, holding the blue glass key. The double whispered, 'You are the one who came through last time.' Then both radios began counting down together."
            ),
            4: (
                "Two versions of Mara faced each other across the observatory doorway. One held the blue glass key. Both radios counted down to sunrise, and neither city had enough time left to understand what the key would unlock.",
                "The other Mara explained that the warning came from a future where the door had never closed. Every attempt to save one city erased another. The missing brother had stayed behind to keep the passage from spreading.",
                "Mara realized the radios were not predicting disasters. They were sending memories backward from failed timelines. She broke the glass key in half and handed one piece to her double. The countdown froze for the first time.",
                "The door sealed, and stars returned to both skies. But when Mara reached home, her brother's notebook contained a new page. It showed a drawing of a second door beneath the sea, with tomorrow's date written underneath."
            ),
        }
        if episode in episode_arcs:
            speeches = episode_arcs[episode]
            beats = [(headline, speeches[i], visual_id, label, role)
                     for i, (headline, _speech, visual_id, label, role) in enumerate(beats)]
        proposals.append({
            "genre": "fiction", "kind": "microfiction",
            "series_id": "the-tomorrow-signal-s1", "season": 1,
            "episode": episode, "previous_episode_id": (
                f"rayvan-season-01-episode-{episode-1:02d}" if episode > 1 else None),
            "production_ready": True, "content_id": cid, "title": title,
            "hook": beats[0][0],
            "question": f"What secret is hiding inside the {place}?",
            "answer": f"{name} uncovers {discovery} and helps {community} change forever.",
            "source": "", "keywords": ["original science fiction", "microfiction"],
            "story_beats": [
                {"headline": h, "speech": s, "visual": v, "label": label,
                 "story_beat": role, "sub": f"THE TOMORROW SIGNAL · EP {episode}",
                 "duration": 1.0}
                for h, s, v, label, role in beats
            ],
        })
        if len(proposals) >= max_candidates:
            break
    return proposals
