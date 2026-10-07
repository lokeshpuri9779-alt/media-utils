from __future__ import annotations

"""Curated character-animation stories for Astra's cinematic character lane.

Stories are original, dialogue-led, visually staged for vertical AI video, and
target a complete 25-40 second mini-story rather than a short visual demo.
"""

import os


def _beat(speech: str, action: str, beat: str, voice: str, speed: float = 1.03, speaker: str = "", *, visible_characters: tuple[str, ...] = ()) -> dict:
    return {
        "headline": "",
        "speech": speech,
        "visual": "character",
        "story_beat": beat,
        "character_action": action,
        "voice_name": voice,
        "voice_speed": speed,
        "speaker": speaker,
        "visible_characters": list(visible_characters),
        "duration": 4.2,
    }


def catalog() -> list[dict]:
    return [
        {
            "genre": "fiction",
            "kind": "character_comedy",
            "content_id": "tiny-dragon-bubbles-v2-sync",
            "production_ready": True,
            "character_story": True,
            "animal_character_story": True,
            "tone": "heartwarming funny family-friendly stylized 3D fantasy comedy",
            "hook": "EVERY DRAGON COULD BREATHE FIRE... EXCEPT HIM",
            "question": "What happens when the smallest dragon can only blow bubbles?",
            "answer": "His strange little mistake becomes exactly what saves the village celebration.",
            "title": "The Dragon Who Could Only Blow Bubbles — Synced Cut",
            "voice_speed": 1.02,
            "voice_cast": {
                "Pip": {"voice": "af_heart", "speed": 1.04},
                "Ember": {"voice": "am_adam", "speed": 1.02},
                "Grandma": {"voice": "af_heart", "speed": 0.96},
            },
            "target_duration_min": 28,
            "target_duration_max": 40,
            "character_bible": (
                "Pip: tiny teal baby dragon with cream belly, rounded snout, oversized amber eyes, "
                "two short ivory horns and tiny wings. Ember: older red dragon sister, taller and confident. "
                "Grandma dragon: gentle moss-green dragon with silver spectacles. Preserve exact scale, eye color, "
                "horn shape, markings and proportions across every scene. Environment: cozy cliffside dragon village "
                "decorated with lanterns for a sunset festival."
            ),
            "story_beats": [
                _beat(
                    "Okay... one tiny flame. That's all I need.",
                    "Pip plants his feet, squeezes his eyes shut and tries very hard to breathe fire while festival lanterns glow behind him.",
                    "reveal", "af_heart", 1.04, "Pip",
                ),
                _beat(
                    "Pffft! ...Oh, come on.",
                    "Instead of fire, one enormous shimmering bubble floats from Pip's mouth and pops on his nose. He stares cross-eyed at the soap foam.",
                    "build", "af_heart", 1.05, "Pip",
                ),
                _beat(
                    "Impressive. You defeated the air.",
                    "Ember folds her arms with a teasing grin while Pip gives her a deeply offended side-eye. Keep the teasing affectionate, not mean.",
                    "contrast", "am_adam", 1.02, "Ember",
                ),
                _beat(
                    "Laugh now. I'm saving my good fire for later.",
                    "Pip turns away proudly, takes two steps, then quietly checks whether Ember believed him. She clearly did not.",
                    "build", "af_heart", 1.05, "Pip",
                ),
                _beat(
                    "Pip! The lantern flame went out!",
                    "A gust sweeps through the festival and every paper lantern goes dark. Grandma points toward the highest lantern hanging over a narrow ledge.",
                    "escalation", "af_heart", 1.00, "Grandma",
                ),
                _beat(
                    "I can't make fire... but I can reach it.",
                    "Pip blows a chain of glowing bubbles that gently lift a tiny ember upward toward the high lantern. Everyone watches in stunned silence.",
                    "payoff", "af_heart", 1.00, "Pip",
                ),
                _beat(
                    "Okay. That was actually impressive.",
                    "The lanterns relight across the village. Ember hugs Pip while he pretends to look smug, then accidentally blows one last bubble around both their heads.",
                    "button", "am_adam", 1.02, "Ember",
                ),
            ],
        },
        {
            "genre": "fiction",
            "kind": "character_comedy",
            "content_id": "bear-cub-bakery-v1",
            "production_ready": True,
            "character_story": True,
            "animal_character_story": True,
            "tone": "warm funny family-friendly stylized 3D animal comedy",
            "hook": "HE WAS TOLD NOT TO TOUCH THE DOUGH",
            "question": "Can a bear cub secretly bake one tiny bun without destroying breakfast?",
            "answer": "No. But the disaster turns into the bakery's funniest new recipe.",
            "title": "The Bear Cub Who Tried to Bake",
            "voice_cast": {
                "Papa": {"voice": "am_adam", "speed": 1.03},
                "Milo": {"voice": "af_heart", "speed": 1.06},
            },
            "voice_speed": 1.03,
            "target_duration_min": 28,
            "target_duration_max": 40,
            "character_bible": (
                "Milo: small honey-brown bear cub with round ears, cream muzzle, green apron slightly too large. "
                "Papa Bear: broad dark-brown bear wearing a white baker apron and flour-dusted chef cap. "
                "Preserve fur colors, apron colors, body scale and facial proportions. Environment: warm woodland bakery "
                "with wooden counters, copper pans, baskets of bread and morning sunlight. There is exactly one Milo cub and exactly one Papa adult in this story; they never duplicate or exchange body size. Show only the cast specified for each shot, with everyone else off-screen."
            ),
            "story_beats": [
                _beat(
                    "Papa: Milo, don't touch the dough. Milo: I wasn't even looking at it.",
                    "Papa Bear points at a huge bowl of rising dough. Milo deliberately looks everywhere except at the bowl.",
                    "reveal", "am_adam", 1.02, visible_characters=("Papa", "Milo"),
                ),
                _beat(
                    "Milo: I'm just... checking if it's lonely.",
                    "Papa is already outside the frame. In a solo shot, Milo pats the dough; it sticks to his paws.",
                    "build", "af_heart", 1.06, visible_characters=("Milo",),
                ),
                _beat(
                    "Milo: Why are you climbing me?!",
                    "The elastic dough stretches up Milo's arms and over his head like a giant sticky hat while he waddles backward in panic.",
                    "escalation", "af_heart", 1.08, visible_characters=("Milo",),
                ),
                _beat(
                    "Papa: Milo? Milo: Everything is completely under control.",
                    "Papa returns. Milo freezes behind the counter with a huge dough blob slowly rising above his head.",
                    "contrast", "am_adam", 1.00, visible_characters=("Papa", "Milo"),
                ),
                _beat(
                    "The dough suddenly pops free and lands perfectly in six muffin cups.",
                    "The dough launches across the counter in slow-motion blobs and lands neatly in six baking cups. Milo and Papa stare at the impossible result.",
                    "payoff", "af_heart", 1.03, visible_characters=("Papa", "Milo"),
                ),
                _beat(
                    "Papa: You invented something. Milo: I meant to do that.",
                    "A locked medium two-shot: exactly one adult Papa on screen-left and exactly one small Milo on screen-right, behind a tray of already-baked buns. Papa holds a tasted bun and reacts with surprise; Milo smiles proudly. Both remain in their original positions for the whole shot. No oven reveal or additional entrance.",
                    "payoff", "am_adam", 1.01, visible_characters=("Papa", "Milo"),
                ),
                _beat(
                    "Papa: Then clean the ceiling. Milo: I have retired from baking.",
                    "Camera tilts up to reveal dough stuck all over the ceiling. Milo slowly backs toward the door while Papa raises one eyebrow.",
                    "button", "af_heart", 1.04, visible_characters=("Papa", "Milo"),
                ),
            ],
        },
        {
            "genre": "fiction",
            "kind": "character_comedy",
            "content_id": "penguin-red-button-v1",
            "production_ready": True,
            "character_story": True,
            "animal_character_story": True,
            "tone": "fast funny family-friendly stylized 3D arctic comedy",
            "hook": "THERE WAS ONE BUTTON HE WAS NOT ALLOWED TO PRESS",
            "question": "What does a curious penguin do with a giant red button labeled DO NOT PRESS?",
            "answer": "He presses it—and accidentally discovers what the button was actually for.",
            "title": "The Penguin and the Red Button",
            "voice_speed": 1.04,
            "target_duration_min": 27,
            "target_duration_max": 39,
            "character_bible": (
                "Nico: small round emperor penguin chick with charcoal-grey fluff, white belly, orange cheek patches, huge curious brown eyes. "
                "Tala: taller adult emperor penguin with sleek black-and-white feathers and calm expression. Preserve markings, size and eye shape. "
                "Environment: colorful polar research station with rounded machinery, snow outside windows and one comically large red button."
            ),
            "story_beats": [
                _beat(
                    "Tala: Nico. Whatever you do, don't press the red button. Nico: Which red button?",
                    "Tala points directly at a huge glowing red button. Nico looks at it, then innocently looks at three completely unrelated objects.",
                    "reveal", "am_adam", 1.02,
                ),
                _beat(
                    "Nico: This one?",
                    "Nico raises one tiny flipper toward the button. Tala slowly lowers it with one finger and gives him a long stare.",
                    "build", "af_heart", 1.04,
                ),
                _beat(
                    "Tala: Especially that one. Nico: Very clear.",
                    "Tala exits through an automatic door. Nico waits exactly one second, then turns dramatically toward the button.",
                    "build", "am_adam", 1.02,
                ),
                _beat(
                    "Nico: I am only going to inspect it.",
                    "Nico leans closer and closer until his belly accidentally bumps the button with a loud click.",
                    "escalation", "af_heart", 1.05,
                ),
                _beat(
                    "Nico: ...That feels bad.",
                    "Warning lights flash. Machinery rumbles. Nico panics and tries to un-press the button with both flippers.",
                    "escalation", "af_heart", 1.06,
                ),
                _beat(
                    "A hidden wall opens and thousands of fish slide into the feeding bay.",
                    "Instead of disaster, a giant fish dispenser opens and neatly fills every feeding tray. Nico stops panicking and slowly smiles.",
                    "payoff", "af_heart", 1.01,
                ),
                _beat(
                    "Tala: That's the lunch button. Nico: Then the label is extremely misleading.",
                    "Tala returns carrying an identical sign that says DO NOT PRESS BEFORE LUNCH. Nico casually steals one fish while she fixes it.",
                    "button", "am_adam", 1.01,
                ),
            ],
        },
        {
            "genre": "fiction",
            "kind": "character_comedy",
            "content_id": "lion-cub-mango-mishap-v2",
            "production_ready": True,
            "character_story": True,
            "animal_character_story": True,
            "tone": "family-friendly funny cartoon animal comedy",
            "hook": "HE ONLY WANTED ONE MANGO",
            "question": "What happens when a tiny lion cub tries to steal the biggest mango?",
            "answer": "The mango rolls straight back to Mom, forcing the world's shortest confession.",
            "title": "The Lion Cub and the Giant Mango",
            "voice_speed": 1.03,
            "target_duration_min": 26,
            "target_duration_max": 38,
            "character_bible": (
                "Kito: small golden lion cub, oversized expressive amber eyes, rounded ears, short fluffy mane beginning to grow. "
                "Mother lion: taller golden lioness with warm brown eyes. Preserve fur markings, eye colors, scale and facial proportions. "
                "Environment: lush sunny mango grove beside a small jungle path."
            ),
            "story_beats": [
                _beat("Mom: One mango, Kito. Kito: Absolutely.", "Mother points to a basket of small mangoes. Kito nods angelically while staring at an enormous mango on a nearby branch.", "reveal", "af_heart", 1.02),
                _beat("Kito: She said one. She never said small.", "Kito sneaks toward the giant mango and grins at his own legal interpretation.", "build", "af_heart", 1.05),
                _beat("Kito: Come on... you are basically already mine.", "Kito pulls the mango with both paws until it suddenly drops and squashes him flat for one comic beat.", "build", "af_heart", 1.06),
                _beat("Kito: Nope. Nope nope nope!", "The mango escapes and rolls downhill. Kito sprints after it, paws scrambling and ears bouncing.", "escalation", "af_heart", 1.08),
                _beat("Mom: Looking for this?", "The mango rolls to a perfect stop against Mother's paw. Kito skids into frame and freezes.", "payoff", "af_heart", 1.00),
                _beat("Kito: I can explain. Mom: Please do. Kito: ...Wind?", "Kito attempts an innocent smile while the trees behind him are completely still.", "payoff", "af_heart", 1.03),
                _beat("Mom: Next time, just ask. Kito: Can I have the giant mango? Mom: No.", "Mother slices the mango anyway and shares it. Kito takes a huge bite, then pauses at her answer with puffed cheeks.", "button", "af_heart", 1.01),
            ],
        },
    ]


def pilot_story() -> dict:
    requested=(os.environ.get("ASTRA_CHARACTER_STORY_ID") or "").strip()
    stories=catalog()
    if requested:
        for story in stories:
            if story["content_id"] == requested:
                return dict(story)
        raise KeyError(f"Unknown ASTRA_CHARACTER_STORY_ID: {requested}")
    return dict(next(s for s in stories if s.get("production_ready")))
