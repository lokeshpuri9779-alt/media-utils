"""Isolated many-character Pillow compositor for ASTRA fiction experiments.

Supports 3..8 recognizable animals with individual actions and expressions.
No arbitrary same-action clones, no independent overlay competing with Studio.
A six-/eight-character ensemble uses foreground/background staging so all
characters are visible within the platform-safe 55..1025 x 485..1370 area.

Enabled only by ASTRA_EXPERIMENT_ENSEMBLE=1 in Studio; does not publish.
"""
from __future__ import annotations

import math
from functools import lru_cache

from PIL import Image, ImageDraw

from astra_v2.pillow_duo_scene import (
    ACTORS, _actor, _stage, _prop, scene_prop, scene_mood, FUR)
from astra_v2.procedural_visual_library import character_recipe, visual_identity

MIN_CAST=3
MAX_CAST=8
SCENE_STYLES=frozenset(("crowd","clue","confrontation","reaction","action","reveal","resolution"))

def cast_for_shot(shot):
    cast=shot.get("story_cast") or ()
    if not isinstance(cast,(tuple,list)) or not MIN_CAST<=len(cast)<=MAX_CAST:
        return ()
    cast=tuple(str(x).lower().strip() for x in cast)
    if any(name not in ACTORS for name in cast) or len(set(cast))!=len(cast):
        return ()
    return cast

def _positions(cast,style,t):
    """(actor_index, center x, top y, sprite width) from director style."""
    n=len(cast)
    if n<=4:
        centers=[int(145+790*(i+.5)/n) for i in range(n)]
        w=270 if n==3 else 230
        out=[(i,x,780+(i%2)*34,w) for i,x in enumerate(centers)]
    else:
        back=n//2
        front=n-back
        rear=[int(175+730*(i+.5)/back) for i in range(back)]
        fore=[int(115+845*(i+.5)/front) for i in range(front)]
        out=([(i,x,635,190) for i,x in enumerate(rear)] +
             [(back+i,x,825,210) for i,x in enumerate(fore)])
    if style in ("clue","reaction","confrontation","reveal"):
        # Spotlight the lead actor while still drawing each supporting cast.
        lead=next((i for i,a in enumerate(cast) if a in ("owl","mouse")),0)
        out=[(i,x,y+(60 if i!=lead else -60),
              int(w*(1.18 if i==lead else .85))) for i,x,y,w in out]
    elif style=="action":
        # Animated body position changes; no whole-scene camera jiggle.
        out=[(i,int(x+math.sin(t*2+i)*21),y,w) for i,x,y,w in out]
    elif style=="resolution":
        out=[(i,x, y-18+int(4*math.sin(t*3+i)),w) for i,x,y,w in out]
    return out

def _sprite(species, index, role, mood, t, style_seed):
    """Draw one rig to its own transparent layer, never a stock character icon."""
    im=Image.new("RGBA",(560,820),(0,0,0,0))
    d=ImageDraw.Draw(im)
    recipe=character_recipe(visual_identity(style_seed,species,index))
    _actor(d,species,280,365,t,role,mood,index,
           visual_recipe=recipe)
    return im

def _focus_actor(shot,cast):
    explicit=str(shot.get("focus_actor") or "").lower()
    if explicit in cast:
        return explicit
    roles=shot.get("acting_notes") or {}
    # The director's most decisive physical action gets camera emphasis.
    for action in ("push","pull","repair","pick","open","throw","run","point","wave"):
        for name in cast:
            if roles.get(name)==action:
                return name
    return cast[0]

def _stage_cue(d,shot,style,t,focus_x):
    """Genre-motivated spotlight/foreground accents, not repeated cards."""
    if style=="clue":
        d.ellipse((focus_x-95,630,focus_x+95,820),
                  outline=(225,201,143),width=7)
        for k in range(3):
            d.line((focus_x-110-k*12,710-k*10,
                    focus_x-145-k*12,678-k*10),fill=(217,205,166),width=4)
    elif style=="confrontation":
        d.line((540,660,540,1145),fill=(199,136,118),width=5)
    elif style=="reaction":
        for k in range(5):
            x=100+k*194
            d.arc((x,660,x+90,780),20,155,fill=(185,178,138),width=4)
    elif style=="reveal":
        d.ellipse((focus_x-165,575,focus_x+165,875),
                  outline=(246,208,130),width=8)
    elif style=="action":
        for k in range(5):
            y=650+k*120
            d.line((70,y,130,y-12),fill=(133,185,191),width=5)
    elif style=="resolution":
        d.arc((160,570,930,1170),202,335,fill=(226,197,125),width=6)

def _stable_moods(shot,cast):
    override=shot.get("mood_notes") or {}
    base=scene_mood(shot)
    return {name:override.get(name) or base if (override.get(name) or base)
            else "alert" for name in cast}

def ensemble_frame(im,shot,t):
    """True only if we rendered the complete explicit cast without substitution."""
    cast=cast_for_shot(shot)
    if not cast:
        return False
    if im.size!=(1080,1920):
        raise ValueError("ASTRA ensemble requires 1080x1920 Pillow frame")
    if not shot.get("experimental_ensemble"):
        return False

    d=ImageDraw.Draw(im)
    _stage(d,shot,t)
    style=str(shot.get("scene_style") or "crowd").lower()
    if style not in SCENE_STYLES:
        style="crowd"
    roles=shot.get("acting_notes") or {}
    if not isinstance(roles,dict):
        roles={}
    focus=_focus_actor(shot,cast)
    spots=_positions(cast,style,t)
    focus_x=next(x for i,x,y,w in spots if cast[i]==focus)
    _stage_cue(d,shot,style,t,focus_x)
    moods=_stable_moods(shot,cast)
    seed=str(shot.get("story_visual_seed") or "|".join(cast))
    # Actors in the distant row render first, then nearer, preserving depth.
    for i,x,y,width in spots:
        name=cast[i]
        action=str(roles.get(name) or "look")
        if action not in ("idle","walk","run","jump","wave","look","hide",
                          "repair","pick","carry","throw","dance",
                          "open","push","pull","point","hug","clap"):
            action="look"
        # Individual phase avoids cloned synchronous blinking/steps.
        sprite=_sprite(name,i,action,moods[name],t+i*.11,seed)
        height=int(sprite.height*width/sprite.width)
        sprite=sprite.resize((width,height),Image.Resampling.BILINEAR)
        left=int(x-width/2)
        # Clamp image within the subject stage before composite.
        left=max(55,min(1025-width,left))
        top=max(485,min(1370-height,y))
        im.paste(sprite,(left,top),sprite)
    obj=scene_prop(shot)
    if obj and style in ("clue","reveal","action","confrontation"):
        # The clue is prominent in evidence-centric scenes, rather than
        # dropping every object into the same bottom-center box.
        stage_obj_x=int(530+50*math.sin(t*1.5)) if style=="action" else 540
        _prop(d,obj,stage_obj_x,1142,t)
    return True
