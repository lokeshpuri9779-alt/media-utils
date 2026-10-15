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

def _acted_position(j, x, y, width, action, t):
    """Continuous blocking in all compositions, not just 'action' shots.

    A role can approach, recoil, jump or celebrate during an establishing,
    clue or reaction scene. Fixed ID + time gives stable, repeatable motion;
    the cast never appears/disappears to simulate activity.
    """
    action = str(action or "look")
    time = max(0.0, min(2.4, float(t)))
    progress = min(1.0, time / 1.6)
    progress = progress * progress * (3 - 2 * progress)
    phase = time * (5.0 if action == "run" else 2.7) + j * 1.13
    if action == "run":
        dx, dy = int(65 * progress), -int(9 * abs(math.sin(phase)))
    elif action == "walk":
        dx, dy = int(36 * progress), -int(6 * abs(math.sin(phase)))
    elif action in ("push", "carry"):
        dx, dy = int(28 * progress), -int(3 * abs(math.sin(phase)))
    elif action == "pull":
        dx, dy = -int(28 * progress), -int(3 * abs(math.sin(phase)))
    elif action == "jump":
        dx, dy = 0, -int(45 * abs(math.sin(time * 3.0)))
    elif action in ("clap", "dance", "wave", "hug"):
        dx, dy = int(8 * math.sin(phase)), -int(10 * abs(math.sin(phase)))
    elif action in ("pick", "repair", "open"):
        dx, dy = int(9 * progress), int(6 * progress)
    elif action == "hide":
        dx, dy = -int(9 * progress), int(18 * progress)
    else:
        dx, dy = int(3 * math.sin(time * 1.05 + j)), 0
    # Keep staging bounded; limb rig handles fine motion separately.
    return (j, max(65, min(1015, int(x + dx))),
            max(510, min(1030, int(y + dy))), int(width))


def _positions(cast,style,t,roles=None,focus=None):
    """Readable staging: full cast in wides, 1–3 leads larger in dramatic beats."""
    n=len(cast)
    roles=roles or {}
    if n<=4:
        centers=[int(145+790*(i+.5)/n) for i in range(n)]
        width=320 if n==3 else 270
        wide=[(i,x,765+(i%2)*29,width) for i,x in enumerate(centers)]
    else:
        back=n//2
        front=n-back
        rear=[int(155+760*(i+.5)/back) for i in range(back)]
        fore=[int(95+880*(i+.5)/front) for i in range(front)]
        # The foreground row gets enough screen area for expressions; rear
        # characters remain present without dominating the active story beat.
        wide=([(i,x,600,184) for i,x in enumerate(rear)] +
              [(back+i,x,815,250) for i,x in enumerate(fore)])
    if style=="crowd":
        return [_acted_position(j,x,y,w,roles.get(cast[j]),t)
                for j,x,y,w in wide]
    focused=cast.index(focus) if focus in cast else 0
    active=[i for i,name in enumerate(cast)
            if roles.get(name) in ("open","pick","carry","push","pull","repair",
                                    "throw","run","walk","jump","point","hide",
                                    "wave","dance","hug","clap")]
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
        return [_acted_position(j,x,y,w,roles.get(cast[j]),t)
                for j,x,y,w in out]
    if style=="confrontation":
        protagonists=[focused]+[j for j in range(n) if j!=focused][:1]
        others=[j for j in range(n) if j not in protagonists]
        out=[(j,int(130+800*(k+.5)/max(1,len(others))),615,145)
             for k,j in enumerate(others)]
        out.extend((j,310 if k==0 else 758,710,385)
                   for k,j in enumerate(protagonists))
        return [_acted_position(j,x,y,w,roles.get(cast[j]),t)
                for j,x,y,w in out]
    if style=="action":
        protagonists=active[:3]
        if focused not in protagonists:
            protagonists=[focused]+protagonists[:2]
        if len(protagonists)<3:
            protagonists += [j for j in range(n) if j not in protagonists][:3-len(protagonists)]
        xs={1:[540],2:[340,740],3:[230,540,850]}[len(protagonists)]
        others=[j for j in range(n) if j not in protagonists]
        def background_spot(k,j):
            x=int(130+800*(k+.5)/max(1,len(others)))
            act=roles.get(cast[j],"look")
            if act in ("dance","wave","clap","point"):
                x+=int(12*math.sin(t*4.2+j))
                y=590-int(10*abs(math.sin(t*5+j)))
            else:
                x+=int(5*math.sin(t*.7+j))
                y=590
            return (j,x,y,145)
        out=[background_spot(k,j) for k,j in enumerate(others)]
        # Stage real translational motion rather than cloning stationary poses.
        def action_spot(j,x):
            act=roles.get(cast[j],"look")
            travel=min(1.0,max(0.0,float(t))/1.35)
            eased=travel*travel*(3-2*travel)
            dx=(95*eased if act=="run" else
                48*eased if act in ("walk","push","carry") else
                -48*eased if act=="pull" else
                22*math.sin(t*3.5+j) if act=="dance" else
                11*math.sin(t*1.2+j))
            dy=(-57*abs(math.sin(t*3.5)) if act=="jump" else
                -11*abs(math.sin(t*6)) if act in ("dance","clap") else 0)
            return (j,int(x+dx),int(745+dy),320)
        out.extend(action_spot(j,x) for j,x in zip(protagonists,xs))
        return out
    if style=="resolution":
        # Each cast member responds on their own beat, no synchronized clones.
        return [_acted_position(j,x+int(11*math.sin(t*1.4+j)),
                 y-35+int(8*math.sin(t*2.1+j*.9)),w,
                 roles.get(cast[j]),t)
                for j,x,y,w in wide]
    return wide

def _sprite(species, index, role, mood, t, style_seed, hand_target=None,
            hand_strength=1.0):
    """Draw a rig with optional local hand-to-prop contact, never an icon."""
    im=Image.new("RGBA",(560,820),(0,0,0,0))
    d=ImageDraw.Draw(im)
    recipe=character_recipe(visual_identity(style_seed,species,index))
    _actor(d,species,280,365,t,role,mood,index,
           hand_target=hand_target, hand_strength=hand_strength,
           visual_recipe=recipe,ground_y=785)
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
    """Return (screen position, holder index, continuous grip strength).

    Object movement depends on the action. A box being opened or a clock
    repaired stays grounded, unlike a carried object. The holder is selected
    deterministically and world-space contact follows its current pose.
    """
    from astra_v2.pillow_duo_scene import _ease
    roles=shot.get("acting_notes") or {}
    if not isinstance(roles,dict):
        roles={}
    handlers=("pick","carry","repair","open","push","pull","throw")
    holder=next((i for i,name in enumerate(cast) if roles.get(name) in handlers),
                cast.index(focus))
    idx,x,y,width=next(spot for spot in spots if spot[0]==holder)
    style=str(shot.get("scene_style") or "crowd").lower()
    left,top,w,h,cx,cy,sw,sh=_composition_geometry(
        idx,x,y,width,cast.index(focus),style)
    # Transform the right-hand rig anchor to the projected actor coordinates.
    hand_x=left+(425-cx)*w/sw
    hand_y=top+(582-cy)*h/sh
    hand=(int(hand_x),int(hand_y))
    # Props begin on the floor beside their actual handler, not teleported in
    # from the arbitrary center of every scene.
    ground=(int(max(140,min(950,hand_x-32))),
            int(max(1110,min(1262,hand_y+148))))
    action=str(roles.get(cast[holder]) or "idle")
    now=max(0.0,float(t))
    move=_ease((now-.10)/1.0)

    if action in ("pick","carry"):
        position=(round(ground[0]+(hand[0]-ground[0])*move),
                  round(ground[1]+(hand[1]-ground[1])*move))
        return position,holder,_ease((move-.06)/.55)
    if action in ("repair","open"):
        # Repair/open require a stable work surface; only the actor reaches.
        work=(ground[0],max(1090,ground[1]-48))
        return work,holder,_ease((now-.10)/.60)
    if action in ("push","pull"):
        direction=1 if action=="push" else -1
        anchor=(ground[0],max(1090,ground[1]-44))
        position=(round(anchor[0]+direction*95*move),anchor[1])
        return position,holder,_ease((now-.03)/.42)
    if action=="throw":
        # The object starts in the grip. It separates only after release, and
        # the launch trajectory is C0 continuous (no teleporting at the cut).
        release=.56
        flight=_ease((now-release)/.82)
        position=(round(hand[0]+205*flight),
                  round(hand[1]-175*math.sin(math.pi*flight)))
        grip=1.0-_ease((now-release)/.24)
        return position,holder,grip
    return ground,holder,0.0

def _stable_moods(shot,cast):
    override=shot.get("mood_notes") or {}
    base=scene_mood(shot)
    return {name:override.get(name) or base if (override.get(name) or base)
            else "alert" for name in cast}

def directed_subshot(shot, t):
    """At most one motivated camera CUT per extended acted beat.

    Same cast, props, and environment survive the cut. No wipes, strobes,
    hue changes, or per-frame random style switching.
    """
    style=str(shot.get("scene_style") or "crowd").lower()
    duration=float(shot.get("duration") or 0)
    if not shot.get("experimental_subshots") or duration < 1.2:
        return style,0
    cut_at=duration * .53
    if float(t) < cut_at:
        return style,0
    alternate={
        "crowd":"reaction", "clue":"action",
        "confrontation":"reaction", "reaction":"action",
        "action":"clue", "reveal":"confrontation",
        "resolution":"clue",
    }
    return alternate.get(style,style),1


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
    style, subshot_index = directed_subshot(shot,t)
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
        if (prop_state and i==prop_state[1] and prop_state[2]>0 and
                action in ("pick","carry","repair","open","push","pull","throw")):
            left,top,w,h,cx,cy,sw,sh=_composition_geometry(
                i,x,y,width,focus_idx,style)
            px,py=prop_state[0]
            hand_local=(cx+(px-left)*sw/w,cy+(py-top)*sh/h)
        sprite=_sprite(name,i,action,moods[name],t+i*.11,seed,
                       hand_target=hand_local,
                       hand_strength=(prop_state[2] if hand_local is not None else 1.0))
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
    if prop_state:
        # Never make the same narrated object disappear on a camera cut.
        # The object is staged as real evidence and follows the active grip.
        handler=cast[prop_state[1]]
        action=str(roles.get(handler) or "idle")
        _prop(d,obj,*prop_state[0],t,action=action)
    return True
