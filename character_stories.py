from __future__ import annotations

"""Curated cinematic character stories for Astra.

The character lane prioritizes:
- an immediate visual problem in the first 2 seconds
- character-to-character dialogue instead of narrator-only exposition
- escalating action, reaction shots and a clear reversal
- a warm/comedic emotional payoff
- 28-35 second Shorts with 7-8 substantial beats
"""


def _story_quality(story: dict) -> dict:
    story=dict(story)
    story.setdefault("target_duration_min", 28)
    story.setdefault("target_duration_max", 35)
    story.setdefault("dialogue_driven", True)
    story.setdefault("minimum_story_beats", 7)
    story.setdefault("production_ready", True)
    return story


def catalog() -> list[dict]:
    return [
        _story_quality({
            "genre": "fiction",
            "kind": "character_comedy",
            "content_id": "lion-cub-mango-bargain-v2",
            "character_story": True,
            "animal_character_story": True,
            "tone": "warm family-friendly cinematic animal comedy with expressive dialogue",
            "hook": "THE CUB MADE A TERRIBLE DEAL",
            "question": "Can a tiny lion cub hide the biggest mango in the grove from his mother?",
            "answer": "He tries to bargain his way out of trouble, but the runaway mango exposes him—and Mom turns the disaster into breakfast.",
            "title": "The Lion Cub's Terrible Mango Deal",
            "voice_speed": 1.00,
            "character_bible": (
                "Main character: small golden lion cub named Kito, oversized expressive amber eyes, "
                "rounded ears, short fluffy mane beginning to grow, no clothing. "
                "Mother lion: taller golden lioness named Nala with warm brown eyes and calm amused expressions. "
                "Keep fur markings, eye colors, body scale and facial proportions identical across every scene. "
                "Environment: lush sunny mango grove beside a curved jungle path. "
                "The giant mango remains the same size and color throughout."
            ),
            "story_beats": [
                {
                    "headline": "",
                    "speaker": "Kito",
                    "dialogue": "Okay... one mango. Nobody has to know.",
                    "speech": "Kito: Okay... one mango. Nobody has to know.",
                    "visual": "character",
                    "story_beat": "hook",
                    "character_action": (
                        "Kito tiptoes toward an enormous ripe mango, glances left and right, then whispers to himself "
                        "with a mischievous grin. Start on his guilty face, then reveal the absurdly huge mango."
                    ),
                },
                {
                    "headline": "",
                    "speaker": "Kito",
                    "dialogue": "Why is the best one always the heaviest?",
                    "speech": "Kito: Why is the best one always the heaviest?",
                    "visual": "character",
                    "story_beat": "build",
                    "character_action": (
                        "Kito pulls the mango free with both paws. It drops into his arms and squashes him nearly flat. "
                        "He struggles upright, knees shaking, then looks offended at the fruit."
                    ),
                },
                {
                    "headline": "",
                    "speaker": "Nala",
                    "dialogue": "Kito? What are you doing?",
                    "speech": "Nala: Kito? What are you doing?",
                    "visual": "character",
                    "story_beat": "pressure",
                    "character_action": (
                        "From off-screen, Nala calls his name. Kito freezes mid-step. Cut to a tight reaction close-up: "
                        "eyes wide, ears stiff, mango wobbling dangerously in his paws."
                    ),
                },
                {
                    "headline": "",
                    "speaker": "Kito",
                    "dialogue": "Exercise! Very advanced exercise.",
                    "speech": "Kito: Exercise! Very advanced exercise.",
                    "visual": "character",
                    "story_beat": "comic_lie",
                    "character_action": (
                        "Kito forces a confident smile and pretends the giant mango is a workout weight, doing one shaky curl. "
                        "His tiny paws tremble while he tries to look serious."
                    ),
                },
                {
                    "headline": "",
                    "speaker": "Nala",
                    "dialogue": "With breakfast?",
                    "speech": "Nala: With breakfast?",
                    "visual": "character",
                    "story_beat": "reversal",
                    "character_action": (
                        "Nala steps into frame with one eyebrow raised. Kito opens his mouth to answer; the mango slips from his paws "
                        "and begins rolling downhill between them."
                    ),
                },
                {
                    "headline": "",
                    "speaker": "Kito",
                    "dialogue": "I can explain!",
                    "speech": "Kito: I can explain!",
                    "visual": "character",
                    "story_beat": "chase",
                    "character_action": (
                        "The mango barrels down the jungle path. Kito sprints after it in panic, paws scrambling and ears bouncing. "
                        "Nala follows at an easy walk, visibly trying not to laugh."
                    ),
                },
                {
                    "headline": "",
                    "speaker": "Nala",
                    "dialogue": "You wanted one mango. Now we all get one.",
                    "speech": "Nala: You wanted one mango. Now we all get one.",
                    "visual": "character",
                    "story_beat": "payoff",
                    "character_action": (
                        "The mango stops against a tree and splits open cleanly. Nala sits beside it, smiling. "
                        "Kito arrives exhausted and stares at the perfect slices in disbelief."
                    ),
                },
                {
                    "headline": "",
                    "speaker": "Kito",
                    "dialogue": "So... the exercise worked?",
                    "speech": "Kito: So... the exercise worked?",
                    "visual": "character",
                    "story_beat": "button",
                    "character_action": (
                        "Kito takes an enormous bite, cheeks puffed out. Nala gives him a deadpan look, then both break into laughter. "
                        "Finish on a warm two-shot as they share the mango."
                    ),
                },
            ],
        }),
        _story_quality({
            "genre": "fiction",
            "kind": "character_comedy",
            "content_id": "fox-cub-moon-cookie-v1",
            "character_story": True,
            "animal_character_story": True,
            "tone": "whimsical family-friendly cinematic animal comedy",
            "hook": "SHE THOUGHT THE MOON WAS A COOKIE",
            "question": "What happens when a fox cub decides to catch the moon for dessert?",
            "answer": "Her reflection-chasing plan fails spectacularly until her father turns the mistake into a tiny midnight picnic.",
            "title": "The Fox Cub Who Tried to Eat the Moon",
            "voice_speed": 1.00,
            "character_bible": (
                "Main character: tiny red fox cub named Miso, cream muzzle, huge green eyes, fluffy tail. "
                "Father fox: taller red fox named Ren, darker ear tips, calm playful expression. "
                "Night setting beside a quiet forest pond, blue moonlight, warm firefly accents. "
                "Maintain exact fur patterns and proportions in every scene."
            ),
            "story_beats": [
                {"speaker":"Miso","dialogue":"Dad... who left that giant cookie in the sky?","speech":"Miso: Dad... who left that giant cookie in the sky?","visual":"character","story_beat":"hook","character_action":"Miso stares up at a huge full moon reflected in the pond, jaw dropping as if she has discovered treasure."},
                {"speaker":"Ren","dialogue":"That is the moon.","speech":"Ren: That is the moon.","visual":"character","story_beat":"setup","character_action":"Ren looks from Miso to the moon, already suspicious of what she is planning."},
                {"speaker":"Miso","dialogue":"Then why does it look delicious?","speech":"Miso: Then why does it look delicious?","visual":"character","story_beat":"escalation","character_action":"Miso crouches beside the pond and studies the moon reflection like a hunter sizing up prey."},
                {"speaker":"Ren","dialogue":"Miso, don't—","speech":"Ren: Miso, don't—","visual":"character","story_beat":"launch","character_action":"Before Ren finishes, Miso leaps paws-first into the pond toward the reflected moon."},
                {"speaker":"Miso","dialogue":"It moved!","speech":"Miso: It moved!","visual":"character","story_beat":"chase","character_action":"Soaked Miso paddles after the rippling reflection while the moon keeps sliding away. Her expression shifts from confidence to betrayal."},
                {"speaker":"Ren","dialogue":"The moon is very good at escaping foxes.","speech":"Ren: The moon is very good at escaping foxes.","visual":"character","story_beat":"reversal","character_action":"Ren gently lifts dripping Miso from the pond by the scruff, trying not to smile."},
                {"speaker":"Miso","dialogue":"Worst cookie ever.","speech":"Miso: Worst cookie ever.","visual":"character","story_beat":"payoff","character_action":"Wrapped in a leaf blanket, Miso pouts while Ren places two real round cookies beside her."},
                {"speaker":"Ren","dialogue":"Try the ones that don't float.","speech":"Ren: Try the ones that don't float.","visual":"character","story_beat":"button","character_action":"Miso bites a cookie, looks at the moon suspiciously, then hides the second cookie from it. Ren laughs beside her."},
            ],
        }),
        _story_quality({
            "genre": "fiction",
            "kind": "character_comedy",
            "content_id": "penguin-red-button-v1",
            "character_story": True,
            "animal_character_story": True,
            "tone": "fast warm family-friendly cinematic animal comedy",
            "hook": "HE WAS TOLD NOT TO TOUCH ONE BUTTON",
            "question": "Can a curious penguin chick resist the biggest red button in the research station?",
            "answer": "No—and the terrifying machine he activates turns out to be the station's fish dispenser.",
            "title": "The Penguin and the Red Button",
            "voice_speed": 1.02,
            "character_bible": (
                "Main character: small emperor penguin chick named Pip, fluffy charcoal-and-white feathers, bright curious eyes. "
                "Older penguin caretaker named Toma, sleek black-and-white feathers, patient expression. "
                "Cozy Antarctic research hut interior with rounded machinery and frosted windows. "
                "Maintain the same button console, character markings and scale throughout."
            ),
            "story_beats": [
                {"speaker":"Toma","dialogue":"Pip. Anything but the red button.","speech":"Toma: Pip. Anything but the red button.","visual":"character","story_beat":"hook","character_action":"Toma points firmly at one enormous glowing red button. Pip stares at it, mesmerized."},
                {"speaker":"Pip","dialogue":"Why make it so... pressable?","speech":"Pip: Why make it so... pressable?","visual":"character","story_beat":"temptation","character_action":"Pip circles the console, tilting his head from different angles while the button glows invitingly."},
                {"speaker":"Toma","dialogue":"Because humans enjoy bad decisions.","speech":"Toma: Because humans enjoy bad decisions.","visual":"character","story_beat":"warning","character_action":"Toma walks away carrying a toolbox. Pip watches him leave, then slowly looks back at the button."},
                {"speaker":"Pip","dialogue":"Tiny press.","speech":"Pip: Tiny press.","visual":"character","story_beat":"launch","character_action":"Pip reaches one flipper toward the button millimeter by millimeter and taps it."},
                {"speaker":"Pip","dialogue":"That was not tiny.","speech":"Pip: That was not tiny.","visual":"character","story_beat":"chaos","character_action":"Lights flash, gears rumble and the floor vibrates. Pip's feathers puff out as he braces for disaster."},
                {"speaker":"Toma","dialogue":"What did you do?","speech":"Toma: What did you do?","visual":"character","story_beat":"pressure","character_action":"Toma rushes back as a ceiling hatch opens dramatically above them."},
                {"speaker":"Pip","dialogue":"I may have improved lunch.","speech":"Pip: I may have improved lunch.","visual":"character","story_beat":"payoff","character_action":"Instead of danger, dozens of fish slide neatly into a feeding tray. Pip beams with pride."},
                {"speaker":"Toma","dialogue":"Tomorrow, we're labeling the buttons.","speech":"Toma: Tomorrow, we're labeling the buttons.","visual":"character","story_beat":"button","character_action":"Toma gives Pip a deadpan stare while Pip happily eats a fish beneath the still-glowing red button."},
            ],
        }),
    ]


def pilot_story() -> dict:
    # Keep the first story as the explicit validation pilot. Production selection
    # can rotate the catalog after this lane clears quality review.
    return dict(catalog()[0])
