from __future__ import annotations

"""Curated character-animation stories for Astra's cinematic character lane.

These stories are original and designed around the user-approved reference
grammar. They do not copy characters, dialogue, branding, or exact shots from
the supplied reference videos.
"""


def catalog() -> list[dict]:
    return [
        {
            "genre": "fiction",
            "kind": "character_comedy",
            "content_id": "lion-cub-mango-mishap-v1",
            "production_ready": False,
            "character_story": True,
            "animal_character_story": True,
            "tone": "family-friendly funny cartoon animal comedy",
            "hook": "HE ONLY WANTED ONE MANGO",
            "question": "What happens when a tiny lion cub tries to steal the biggest mango?",
            "answer": "The mango is heavier than he expects, rolls downhill, and leads him straight back to the family he was hiding from.",
            "title": "The Lion Cub and the Giant Mango",
            "voice_speed": 1.03,
            "character_bible": (
                "Main character: small golden lion cub, oversized expressive amber eyes, "
                "rounded ears, short fluffy mane beginning to grow, no clothing. "
                "Mother lion: taller golden lioness with warm brown eyes. "
                "Keep fur markings, eye colors, body scale and facial proportions identical "
                "across every scene. Environment: lush sunny mango grove beside a small jungle path."
            ),
            "story_beats": [
                {
                    "headline": "",
                    "speech": "He only wanted one mango.",
                    "visual": "character",
                    "story_beat": "reveal",
                    "character_action": (
                        "A tiny golden lion cub sneaks toward an enormous ripe mango hanging low "
                        "from a tree, checking over both shoulders with an exaggerated guilty face."
                    ),
                },
                {
                    "headline": "",
                    "speech": "Then he picked the biggest one.",
                    "visual": "character",
                    "story_beat": "build",
                    "character_action": (
                        "The cub tugs the giant mango with both front paws; it drops into his arms, "
                        "squashes him slightly under the weight, and his eyes widen in comic panic."
                    ),
                },
                {
                    "headline": "",
                    "speech": "Bad idea.",
                    "visual": "character",
                    "story_beat": "escalation",
                    "character_action": (
                        "The mango slips free and rolls rapidly down the jungle path. The cub sprints "
                        "after it, paws scrambling, ears bouncing, nearly tripping as the camera tracks beside him."
                    ),
                },
                {
                    "headline": "",
                    "speech": "It rolled straight back to Mom.",
                    "visual": "character",
                    "story_beat": "payoff",
                    "character_action": (
                        "The giant mango stops gently at the mother lion's paws. The cub skids to a halt "
                        "behind it, freezes, then gives a tiny innocent smile while the mother raises one eyebrow."
                    ),
                },
                {
                    "headline": "",
                    "speech": "So much for the secret snack.",
                    "visual": "character",
                    "story_beat": "button",
                    "character_action": (
                        "Mother and cub sit together sharing slices of the mango. The cub takes an oversized bite, "
                        "cheeks puff out, and both characters laugh in a warm family-comedy ending."
                    ),
                },
            ],
        }
    ]


def pilot_story() -> dict:
    return dict(catalog()[0])
