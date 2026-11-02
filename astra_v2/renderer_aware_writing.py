"""CPU-only prompt guidance drawn from ASTRA's current unified Studio capabilities.

This is authoring guidance, not renderer compatibility or video semantic approval.
No Pillow/Blender imports: Gemini generation runs before renderer dependencies install.
The regression suite ensures names remain a subset of the actual actor/prop library.
"""

SUPPORTED_ANIMALS = (
    "fox", "rabbit", "cat", "dog", "owl", "mouse", "otter", "squirrel",
    "tapir", "pangolin", "stoat", "lynx", "ferret", "marten",
)

SUPPORTED_PROPS = (
    "box", "book", "ball", "flower", "lantern", "key", "bell",
    "compass", "shield", "rocket", "heart", "wrench", "clock",
)

# Genre diversity without requesting the unsupported human/robot protagonists
# responsible for most failures in the 2026-11-02 production diagnostic.
RENDERER_AWARE_DOMAINS = (
    "mountain trail suspense with a lynx or fox protagonist",
    "river ecology mystery with an otter protagonist",
    "marketplace comedy with a cat or ferret protagonist",
    "village friendship dilemma with a dog or rabbit protagonist",
    "forest survival cooperation with a fox and rabbit",
    "night-time railway platform mystery with a mouse or owl protagonist",
    "woodland caretaking dilemma with a squirrel protagonist",
    "seaside celebration mystery with an otter protagonist",
    "dry-grassland navigation challenge with a pangolin protagonist",
    "community sports comedy with a dog and cat",
    "snowy forest rescue decision with a stoat protagonist",
    "observatory discovery with an owl protagonist",
)


def writing_guidance():
    """Constrain model proposals to existing renderable actors/props, not approval."""
    return (
        " Production feasibility is mandatory, not optional. This ASTRA Studio "
        "renderer currently has a limited illustrated animal puppet library. "
        "Choose exactly one or two recurring animal protagonist SPECIES from: "
        + ", ".join(SUPPORTED_ANIMALS) + ". Keep the species explicitly named "
        "in the title, narration, visual prompts, and character descriptions "
        "as appropriate, without adding an unrepresentable third protagonist. "
        "Do not create human protagonists, human helpers, robots acting as "
        "characters, badgers, unsupported animal species, or clothed human "
        "figures unless independently verified scene artwork exists; this "
        "generation path cannot assume such artwork. "
        "The currently reusable simple props are: "
        + ", ".join(SUPPORTED_PROPS) + ". Use only props the renderer can "
        "represent consistently. Prefer a concrete, small, physically legible "
        "cause-and-effect conflict that can be shown by the same animal cast "
        "in four beats. Avoid action claims requiring unsupported elaborate "
        "animation, crowded crowds, complex machines, or unseen interacting "
        "human bodies. A visual icon alone is NOT evidence that a depicted "
        "interaction happened. The visual_prompt must describe a scene "
        "the existing animal acting/prop library could plausibly depict. "
        "Keep a distinct, genuinely original causal mechanism, meaningful "
        "decision and consequence; don't recycle a misplaced-item or "
        "broken-lantern premise merely to satisfy this constraint. "
        "If the premise requires unsupported visuals, invent a different "
        "premise before returning JSON. Output is still an unreviewed proposal "
        "and must pass all independent editorial, artwork, and publisher gates."
    )
