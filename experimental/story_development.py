"""Develop draft-bank premises into four-beat review candidates, never auto-approve.

This is a zero-cost deterministic *outline* builder. A review candidate is not
a finished screenplay, quality-approved story, or permission to publish.
"""
from experimental.story_draft_bank import draft_bank

INCIDENTS = {
    "disappears before the celebration": (
        "The object vanishes from its display just before the guests arrive.",
        "A misleading trail leads to an empty storage room.",
        "A fresh mark beside the display points toward the delivery cart.",
        "The object is recovered and returned before the celebration begins.",
    ),
    "breaks during a storm": (
        "The storm damages the object while everyone takes shelter.",
        "A hurried patch fails when the wind returns.",
        "A sheltered workshop offers the right tools and dry materials.",
        "The repair holds and the community can use the object again.",
    ),
    "reveals a hidden message": (
        "An unexpected marking appears on the object in the morning light.",
        "The first attempt to decode it points to the wrong building.",
        "A second clue matches a symbol on an old public map.",
        "The clue leads to a forgotten keepsake that can be returned to its owner.",
    ),
    "ends up in the wrong hands": (
        "A delivery mix-up puts the object with someone who was not expecting it.",
        "The first exchange fails because the packages have identical wrapping.",
        "A tiny identifying scratch helps trace the correct recipient.",
        "The owners exchange the packages and prevent the mistake recurring.",
    ),
}

def develop(draft):
    conflict=draft["conflict"]
    if conflict not in INCIDENTS:
        raise ValueError("Unknown conflict")
    hero=draft["hero"]
    setting=draft["setting"]
    obj=draft["central_object"]
    arc=INCIDENTS[conflict]
    scenes=[
        {"role":role,"headline":headline,
         "speech":f"In the {setting}, the {hero} faces a problem with the {obj}. {beat}",
         "visual":setting,"label":label}
        for role,headline,beat,label in zip(
            ("reveal","build","twist","payoff"),
            ("THE PROBLEM","THE SETBACK","THE DISCOVERY","THE RESOLUTION"),
            arc,("A NEW MYSTERY","NOT SO EASY","A REAL CLUE","THE PAYOFF"))
    ]
    return {
        "content_id":draft["content_id"],"title":draft["title"],
        "genre":"fiction","kind":"unreviewed_causal_draft",
        "production_ready":False,"publication_allowed":False,
        "development_status":"outline_requires_original_script_and_review",
        "story_beats":scenes,
        "quality_warning":"Shared conflict templates: NOT 1024 original finished scripts",
    }

def development_batch(limit=1024):
    if not 0 <= limit <= 1024:
        raise ValueError("limit must be 0..1024")
    return [develop(d) for d in draft_bank()[:limit]]
