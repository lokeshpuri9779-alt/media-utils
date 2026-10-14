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
    ("run",r"\b(?:run|runs|ran|running|sprint|sprints|sprinted|chase|chased|chasing)\b"),
    ("jump",r"\b(?:jump|jumps|jumped|jumping|leap|leaps|leapt|leaped|hops|hopped|hop)\b"),
    ("dance",r"\b(?:dance|dances|danced|dancing|celebrat\w*)\b"),
    ("hide",r"\b(?:hide|hides|hid|hidden|hiding|crouch|crouched|ducked)\b"),
    ("walk",r"\b(?:walk|walks|walked|walking|approach|approaches|approached|approaching)\b"),
    ("look",r"\b(?:look|looks|looked|looking|watch|watches|watched|stare|stares|stared)\b"),
)
def choose_action(shot):
    text=" ".join(str(shot.get(k) or "") for k in ("action","visual_prompt","visual","speech")).lower()
    for name,pattern in ACTION_PATTERNS:
        if re.search(pattern,text):
            return name
    return "idle"

def offset(action,t,scale=1.0):
    if not math.isfinite(t) or not math.isfinite(scale) or scale<0:
        raise ValueError("invalid motion parameters")
    phase=t*2*math.pi
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
