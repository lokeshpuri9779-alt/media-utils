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
    ACTORS, _actor, _prop, scene_prop, scene_mood)
from astra_v2.ensemble_stage import draw_ensemble_stage
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

def _positions(cast,style,t,roles=None,focus=None):
    """Readable staging: full cast in wides, 1–3 leads larger in dramatic beats."""
    n=len(cast)
    roles=roles or {}
    if n<=4:
        centers=[int(145+790*(i+.5)/n) for i in range(n)]
        width=310 if n==3 else 260
        wide=[(i,x,765+(i%2)*29,width) for i,x in enumerate(centers)]
    else:
        back=n//2
        front=n-back
        rear=[int(155+760*(i+.5)/back) for i in range(back)]
        fore=[int(95+880*(i+.5)/front) for i in range(front)]
        wide=([(i,x,600,170) for i,x in enumerate(rear)] +
              [(back+i,x,815,225) for i,x in enumerate(fore)])
    if style=="crowd":
        return wide
    focused=cast.index(focus) if focus in cast else 0
    active=[i for i,name in enumerate(cast)
            if roles.get(name) in ("open","pick","push","pull","repair","throw",
                                    "run","jump","point","hide","wave")]
    if style in ("clue","reaction","reveal"):
        protagonists=[focused]+[j for j in active if j!=focused][:2]
        if len(protagonists)<2:
            protagonists+= [j for j in range(n) if j not in protagonists][:2]
        if len(protagonists)>3:
            protagonists=protagonists[:3]
        main_x={1:[540],2:[330,745],3:[265,540,805]}[len(protagonists)]
        centers={j:x for j,x in zip(protagonists,main_x)}
        others=[j for j in range(n) if j not in protagonists]
        rear_x=[int(165+735*(j+.5)/max(1,len(others))) for j in range(len(others))]
        out=[(idx,rear_x[k],600,138) for k,idx in enumerate(others)]
        # A slow optical push toward the active hero changes framing without
        # toggling scene assets or abruptly switching character visibility.
        push=min(1.0,max(0.0,float(t))/1.5)
        push=push*push*(3-2*push)
        out.extend((j,centers[j],692+(k%2)*32,
                    445+int(9*push) if j==focused else 285)
                   for k,j in enumerate(protagonists))
        return out
    if style=="confrontation":
        protagonists=[focused]+[j for j in range(n) if j!=focused][:1]
        others=[j for j in range(n) if j not in protagonists]
        out=[(j,int(130+800*(k+.5)/max(1,len(others))),615,145)
             for k,j in enumerate(others)]
        out.extend((j,310 if k==0 else 758,710,385)
                   for k,j in enumerate(protagonists))
        return out
    if style=="action":
        protagonists=active[:3]
        if focused not in protagonists:
            protagonists=[focused]+protagonists[:2]
        if len(protagonists)<3:
            protagonists += [j for j in range(n) if j not in protagonists][:3-len(protagonists)]
        xs={1:[540],2:[340,740],3:[230,540,850]}[len(protagonists)]
        others=[j for j in range(n) if j not in protagonists]
        out=[(j,int(130+800*(k+.5)/max(1,len(others))),590,145)
             for k,j in enumerate(others)]
        # Stage real translational motion rather than cloning stationary poses.
        def action_spot(j,x):
            act=roles.get(cast[j],"look")
            travel=min(1.0,max(0.0,float(t))/1.35)
            eased=travel*travel*(3-2*travel)
            dx=(80*eased if act=="run" else
                42*eased if act=="push" else
                -42*eased if act=="pull" else
                8*math.sin(t*1.2+j))
            dy=(-48*abs(math.sin(t*3.5)) if act=="jump" else 0)
            return (j,int(x+dx),int(745+dy),290)
        out.extend(action_spot(j,x) for j,x in zip(protagonists,xs))
        return out
    if style=="resolution":
        return [(j,x,y-35+int(5*math.sin(t*3+j)),w)
                for j,x,y,w in wide]
    return wide

def _sprite(species, index, role, mood, t, style_seed, hand_target=None):
    """Draw a rig with optional local hand-to-prop contact, never an icon."""
    im=Image.new("RGBA",(560,820),(0,0,0,0))
    d=ImageDraw.Draw(im)
    recipe=character_recipe(visual_identity(style_seed,species,index))
    _actor(d,species,280,365,t,role,mood,index,
           hand_target=hand_target, visual_recipe=recipe)
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

def _stage_cue(d, shot, style, t, focus_x):
    """Story-driven focus without guide arcs, rings, or repeated swooshes."""
    if style in ("clue","reveal"):
        # A grounded shadow gives evidence scenes depth without flashing.
        d.ellipse((focus_x-160,1200,focus_x+160,1275),
                  fill=(42,78,85))
    elif style=="action":
        # Short ground-level motion streaks, never across the characters.
        for j in range(3):
            x=180+j*90+int(8*math.sin(t*1.8+j))
            d.line((x,1264+j*7,x+60,1264+j*7),
                   fill=(103,149,151),width=4)


def _composition_geometry(idx, x, y, width, focus_idx, style):
    """Map 560x820 actor rig into final screen for accurate physical contact."""
    cropped=(idx==focus_idx and style in ("clue","reaction","reveal"))
    src_x,src_y,src_w,src_h=(94,175,372,517) if cropped else (0,0,560,820)
    h=int(src_h*width/src_w)
    left=max(55,min(1025-width,int(x-width/2)))
    top=max(485,min(1370-h,y))
    return (left,top,width,h,src_x,src_y,src_w,src_h)


def _prop_stage_position(shot, spots, cast, focus, t):
    """A narrated object follows the active actor's reachable hand or ground."""
    from astra_v2.pillow_duo_scene import _ease
    role=shot.get("acting_notes") or {}
    if not isinstance(role,dict):
        role={}
    handlers=("pick","carry","repair","open","push","pull","throw")
    holder=next((i for i,name in enumerate(cast) if role.get(name) in handlers),
                cast.index(focus))
    idx,x,y,width=next((spot for spot in spots if spot[0]==holder))
    style=str(shot.get("scene_style") or "crowd")
    geometry=_composition_geometry(idx,x,y,width,cast.index(focus),style)
    left,top,w,h,cx,cy,sw,sh=geometry
    # The hand at (425,582) in the original rig, transformed through crop.
    dest=(int(left+(425-cx)*w/sw),int(top+(582-cy)*h/sh))
    action=str(role.get(cast[holder]) or "idle")
    move=_ease((max(0.0,t)-.12)/.95)
    if action=="throw":
        # Release after first half, then follow a shallow believable arc.
        free=_ease((max(0.0,t)-.55)/.8)
        return (int(dest[0]+165*free),
                int(dest[1]-115*math.sin(free*math.pi))), holder, False
    if action in ("pick","carry","repair","open","push","pull"):
        # Smooth arrival at fingertips. No teleport on individual frames.
        target_x=dest[0]
        if action=="push":
            target_x+=int(65*move)
        elif action=="pull":
            target_x-=int(65*move)
        pos=(int(540*(1-move)+target_x*move),
             int(1190*(1-move)+dest[1]*move))
        return pos, holder, move>.2
    return (540,1140), holder, False


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
    draw_ensemble_stage(d,shot.get("story_environment"),t,shot)
    style=str(shot.get("scene_style") or "crowd").lower()
    if style not in SCENE_STYLES:
        style="crowd"
    roles=shot.get("acting_notes") or {}
    if not isinstance(roles,dict):
        roles={}
    focus=_focus_actor(shot,cast)
    spots=_positions(cast,style,t,roles,focus)
    focus_x=next(x for i,x,y,w in spots if cast[i]==focus)
    _stage_cue(d,shot,style,t,focus_x)
    moods=_stable_moods(shot,cast)
    seed=str(shot.get("story_visual_seed") or "|".join(cast))
    obj=scene_prop(shot)
    focus_idx=cast.index(focus)
    prop_state=(_prop_stage_position(shot,spots,cast,focus,t) if obj else None)
    # Actors in the distant row render first, then nearer, preserving depth.
    for i,x,y,width in spots:
        name=cast[i]
        action=str(roles.get(name) or "look")
        if action not in ("idle","walk","run","jump","wave","look","hide",
                          "repair","pick","carry","throw","dance",
                          "open","push","pull","point","hug","clap"):
            action="look"
        # Individual phase avoids cloned synchronous blinking/steps.
        hand_local=None
        if (prop_state and i==prop_state[1] and prop_state[2] and
                action in ("pick","carry","repair","open","push","pull")):
            left,top,w,h,cx,cy,sw,sh=_composition_geometry(
                i,x,y,width,focus_idx,style)
            px,py=prop_state[0]
            hand_local=(cx+(px-left)*sw/w,cy+(py-top)*sh/h)
        sprite=_sprite(name,i,action,moods[name],t+i*.11,seed,
                       hand_target=hand_local)
        # In a clue/reveal/reaction beat, switch from a tiny full-body group
        # sprite to a dramatic head-and-shoulders shot for the lead actor.
        if name==focus and style in ("clue","reaction","reveal"):
            sprite=sprite.crop((94,175,466,692))
        height=int(sprite.height*width/sprite.width)
        sprite=sprite.resize((width,height),Image.Resampling.BILINEAR)
        left=int(x-width/2)
        # Clamp image within the subject stage before composite.
        left=max(55,min(1025-width,left))
        top=max(485,min(1370-height,y))
        im.paste(sprite,(left,top),sprite)
    if prop_state and style in ("clue","reveal","action","confrontation","resolution"):
        # The object is staged as real evidence and follows the active grip.
        handler=cast[prop_state[1]]
        action=str(roles.get(handler) or "idle")
        _prop(d,obj,*prop_state[0],t,action=action)
    return True
