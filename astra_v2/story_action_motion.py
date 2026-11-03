"""Deterministic action-aware animation cues for CPU-rendered characters.

This is an incremental animation vocabulary, not 3D skeletal animation.
"""
from __future__ import annotations
import math
import re

ACTION_PATTERNS=(
    ("repair",r"\b(?:repair|repairs|repaired|repairing|fix|fixes|fixed|fixing|mend|mends|mended|mending)\b"),
    ("carry",r"\b(?:carry|carries|carried|carrying|lift|lifts|lifted|lifting|hold|holds|held|holding)\b"),
    ("throw",r"\b(?:throw|throws|threw|thrown|throwing|toss|tosses|tossed|tossing)\b"),
    ("pick",r"\b(?:pick up|picks up|picked up|picking up|grab|grabs|grabbed|grabbing)\b"),
    ("wave",r"\b(?:wave|waves|waved|waving|greet|greets|greeted|greeting)\b"),
    ("open",r"\b(?:open|opens|opened|opening|unseal|unsealed)\b"),
    ("push",r"\b(?:push|pushes|pushed|pushing|shove|shoves|shoved)\b"),
    ("pull",r"\b(?:pull|pulls|pulled|pulling|drag|drags|dragged)\b"),
    ("point",r"\b(?:point|points|pointed|pointing|signals|signaled|signalling|signaling)\b"),
    ("hug",r"\b(?:hug|hugs|hugged|hugging|embrace|embraced)\b"),
    ("clap",r"\b(?:clap|claps|clapped|clapping|applaud|applauded)\b"),
    ("catch",r"\b(?:catch|catches|caught|catching|intercept|intercepts|intercepted)\b"),
    ("chase",r"\b(?:chase|chases|chased|chasing|pursue|pursues|pursued|pursuing)\b"),
    ("swim",r"\b(?:swim|swims|swam|swimming|paddle|paddles|paddled|paddling)\b"),
    ("sneak",r"\b(?:sneak|sneaks|sneaked|sneaking|tiptoe|tiptoes|tiptoed|tiptoeing|creep|creeps|crept|creeping)\b"),
    ("run",r"\b(?:run|runs|ran|running|sprint|sprints|sprinted)\b"),
    ("jump",r"\b(?:jump|jumps|jumped|jumping|leap|leaps|leapt|leaped|hops|hopped|hop)\b"),
    ("dance",r"\b(?:dance|dances|danced|dancing|celebrat\w*)\b"),
    ("hide",r"\b(?:hide|hides|hid|hidden|hiding|crouch|crouched|ducked)\b"),
    ("walk",r"\b(?:walk|walks|walked|walking|approach|approaches|approached|approaching)\b"),
    ("look",r"\b(?:look|looks|looked|looking|watch|watches|watched|stare|stares|stared)\b"),
)
def choose_action(shot):
    """Choose a single animation cue using the authored source's priority.

    The directed action is authoritative; if absent, the visible storyboard
    direction beats supporting narration. Do NOT let an incidental word in
    speech (e.g. a "signal" noun) override the action requested for pixels.
    This is one pose/motion cue, not semantic confirmation of an MP4.
    """
    for field in ("action", "visual_prompt", "visual", "speech"):
        text = str(shot.get(field) or "").lower()
        for name, pattern in ACTION_PATTERNS:
            if re.search(pattern, text):
                return name
    return "idle"


# The animal puppet has ONE action track. It can walk while carrying a
# staged prop, but jump/swim poses do not keep prop-to-hand contact. Detect
# only explicitly co-temporal claims involving a tangible supported prop.
# This is an authoring/renderer capability check, NOT a pixel-level review.
_PROP_NAME = (
    r"(?:box|book|ball|flower|lantern|key|bell|compass|shield|"
    r"rocket|heart|wrench|clock)"
)
_CARRYING_PROP = re.compile(
    r"\b(?:carry|carries|carried|carrying|hold|holds|held|holding|"
    r"clutch|clutches|clutched|clutching)\b"
    r"(?:\s+(?:a|an|the|his|her|its|my|their|small|brass|wooden|"
    r"heavy|bright|old|red|blue|green|tiny|golden)){0,6}\s+"
    + _PROP_NAME + r"\b", re.I,
)
_MOUTH_GRIP = re.compile(
    r"\b" + _PROP_NAME
    + r"\s+(?:in|between)\s+(?:(?:his|her|its|the|their)\s+)?"
    r"(?:teeth|mouth|beak|paws)\b", re.I,
)
_JUMP_SWIM = re.compile(
    r"\b(?:jump|jumps|jumped|jumping|leap|leaps|leapt|leaped|"
    r"hop|hops|hopped|hopping|swim|swims|swam|swimming)\b", re.I,
)
_SEQUENTIAL_BREAK = re.compile(
    r"[.;!?]|\b(?:and\s+then|then|before|after|later|once)\b", re.I,
)


def unsupported_simultaneous_prop_motion(shot):
    """True for same-beat carrying+jump/swim, not sequential action lists.

    Only a single authored clause and a recognized tangible prop can trigger
    the gate. Narration and visual directions are checked independently;
    merely mentioning two different actions in different fields is not enough.
    """
    for field in ("action", "visual_prompt", "speech", "visual_intent"):
        value = shot.get(field)
        if not isinstance(value, str):
            continue
        for clause in _SEQUENTIAL_BREAK.split(value):
            # "carried a box and jumped" can be sequential and is not
            # enough. Require an ongoing carrying/holding gerund, explicit
            # "while/as" linkage, or a prop described in the character's mouth.
            carrying = _CARRYING_PROP.search(clause)
            simultaneous = (
                re.search(r"\b(?:while|whilst|as|carrying|holding|clutching)\b",
                          clause, re.I)
                or _MOUTH_GRIP.search(clause)
            )
            if _JUMP_SWIM.search(clause) and carrying and simultaneous:
                return True
            if _JUMP_SWIM.search(clause) and _MOUTH_GRIP.search(clause):
                return True
    return False


def _ease_progress(t, duration=1.2):
    """Clamped cubic ease-in/out for one-shot displacement."""
    u = min(1.0, max(0.0, t / duration))
    return u * u * (3.0 - 2.0 * u)


def offset(action,t,scale=1.0):
    if not math.isfinite(t) or not math.isfinite(scale) or scale<0:
        raise ValueError("invalid motion parameters")
    phase=t*2*math.pi
    if action=="open":
        return 0,round(4*math.sin(t*2)*scale)
    if action=="push":
        return round(36*_ease_progress(t)*scale),0
    if action=="pull":
        return round(-36*_ease_progress(t)*scale),0
    if action=="point":
        return round(7*math.sin(t*1.5)*scale),round(-8*scale)
    if action=="hug":
        return 0,round(-9*scale)
    if action=="clap":
        return 0,round(9*math.sin(t*7)*scale)
    if action=="repair":
        return round(9*math.sin(phase*2.1)*scale),round(15*math.sin(phase*2.1)*scale)
    if action=="carry":
        return round(12*math.sin(t*1.3)*scale),round(4*abs(math.sin(phase))*scale)
    if action=="throw":
        return round(24*math.sin(phase*.55)*scale),round(-38*max(0,math.sin(phase*.55))*scale)
    if action=="pick":
        return 0,round(36*(1-math.cos(phase*.5))*scale)
    if action=="wave":
        return round(17*math.sin(phase*1.8)*scale),round(-14*abs(math.sin(phase*1.8))*scale)
    if action=="catch":
        return round(13*math.sin(t*2.7)*scale),round(-19*_ease_progress(t,.9)*scale)
    if action=="chase":
        return round(68*math.sin(t*3.4)*scale),round(21*abs(math.sin(phase*3.1))*scale)
    if action=="swim":
        return round(28*math.sin(t*2.1)*scale),round(25*math.sin(phase*1.3)*scale)
    if action=="sneak":
        return round(12*math.sin(t*1.1)*scale),round(4*abs(math.sin(phase*.9))*scale)
    if action=="run":
        return round(48*math.sin(t*3.2)*scale),round(18*abs(math.sin(phase*3))*scale)
    if action=="jump":
        return 0,round(-90*abs(math.sin(phase*.7))*scale)
    if action=="dance":
        return round(30*math.sin(phase*1.2)*scale),round(25*math.sin(phase*2.4)*scale)
    if action=="hide":
        return 0,round(65*scale)
    if action=="walk":
        return round(20*math.sin(t*1.5)*scale),round(7*abs(math.sin(phase))*scale)
    if action=="look":
        return round(12*math.sin(t*.9)*scale),0
    return 0,0
