"""Deterministic action-aware animation cues for CPU-rendered characters.

This is an incremental animation vocabulary, not 3D skeletal animation.
"""
from __future__ import annotations
import math
import re

ACTION_PATTERNS=(
    ("run",r"\b(?:run|runs|running|sprint|sprints|chase|chasing)\b"),
    ("jump",r"\b(?:jump|jumps|jumping|leap|leaps|hops|hop)\b"),
    ("dance",r"\b(?:dance|dances|dancing|celebrat\w*)\b"),
    ("hide",r"\b(?:hide|hides|hiding|crouch|ducked)\b"),
    ("walk",r"\b(?:walk|walks|walking|approach|approaches|approaching)\b"),
    ("look",r"\b(?:look|looks|looking|watch|watches|stare|stares)\b"),
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
