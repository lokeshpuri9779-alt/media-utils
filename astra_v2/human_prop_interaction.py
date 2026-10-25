"""Wrist-anchored original story props for ASTRA's approved Mara episodes.

A radio carried while fleeing and the two halves of a broken glass key
follow *the very same screen-space skeletal wrists* painted by the actor
renderer. Earlier revisions moved props with unrelated hard-coded sinusoids,
making them float away from hands. This renderer is original CPU 2D graphics,
not physics simulation, general gesture inference, neural video or 3D.
"""
from __future__ import annotations

import math
from PIL import ImageDraw
from astra_errors import CreativeReject


def _wrist(value):
    if (not isinstance(value,(tuple,list)) or len(value)!=2
            or not all(isinstance(n,(int,float)) and math.isfinite(n) for n in value)):
        raise CreativeReject("Held prop requires a finite two-dimensional wrist")
    return (float(value[0]),float(value[1]))


def _ease(value):
    x=max(0.,min(1.,float(value)))
    return x*x*(3.-2.*x)


def carried_radio_center(hand):
    """The actor grips the upper-left rim of the portable radio."""
    x,y=_wrist(hand)
    return (round(x+58),round(y+35))


def draw_radio_in_hand(draw, hand, t, radio_draw):
    """Render the radio *after* the actor, then restore the foreground fingers."""
    x,y=_wrist(hand)
    if not isinstance(draw,ImageDraw.ImageDraw) or not math.isfinite(float(t)):
        raise CreativeReject("Invalid radio animation or drawing surface")
    center=carried_radio_center(hand)
    radio_draw(draw,center[0],center[1],t,portable=True)
    hx,hy=round(x),round(y)
    # Gripping thumb reappears in front of the receiver bezel.
    draw.ellipse((hx-18,hy-13,hx+18,hy+16),
                 fill=(198,142,111),outline=(24,34,49),width=3)
    draw.arc((hx-11,hy-8,hx+11,hy+10),210,340,
             fill=(240,193,158),width=3)
    return {"hand":(hx,hy),"radio_center":center,
            "grip_offset":(58,35),"attached":True}


def _lerp(a,b,q):
    return round(a+(b-a)*q)


def key_half_positions(progress, mara_hand, double_hand):
    """Compute continuous split and transfer from central prop to both wrists.

    There is no teleport when each half changes ownership. The intermediate
    positions move gradually from the break site to the actor hand position.
    At the end, each half has exactly its corresponding wrist as its anchor.
    """
    if not isinstance(progress,(int,float)) or not math.isfinite(progress):
        raise CreativeReject("Key separation progression must be finite")
    if progress<0 or progress>1:
        raise CreativeReject("Key separation progression outside action range")
    a=_wrist(mara_hand)
    b=_wrist(double_hand)
    fraction=_ease((progress-.04)/.66)
    left=(_lerp(510,a[0],fraction),_lerp(930,a[1],fraction))
    right=(_lerp(566,b[0],fraction),_lerp(930,b[1],fraction))
    return {"mara":left,"double":right,"attached":fraction>=1.,
            "transfer_progress":fraction}


def draw_split_key_in_hands(draw, progress, mara_hand, double_hand):
    """Two independently drawn glass fragments; their centers follow wrists."""
    if not isinstance(draw,ImageDraw.ImageDraw):
        raise CreativeReject("Glass key requires a drawing canvas")
    info=key_half_positions(progress,mara_hand,double_hand)
    color=(72,171,233)
    luminous=(190,235,255)
    dark=(22,68,121)
    lx,ly=info["mara"]
    rx,ry=info["double"]
    # Mara holds the ring and lower stem; her actor's fingers grip the ring.
    draw.ellipse((lx-29,ly-24,lx+23,ly+25),
                 fill=(52,129,198),outline=luminous,width=6)
    draw.ellipse((lx-11,ly-10,lx+7,ly+9),fill=dark)
    draw.line(((lx+2,ly+16),(lx+9,ly+102)),fill=color,width=15)
    draw.line(((lx+8,ly+81),(lx+30,ly+81)),fill=luminous,width=10)
    # The duplicate holds the jagged bit of the key with its two teeth.
    draw.polygon(((rx-24,ry-20),(rx+18,ry-25),(rx+12,ry+3),
                  (rx+27,ry+19),(rx-17,ry+26)),fill=color,
                 outline=luminous,width=6)
    draw.line(((rx+5,ry+18),(rx+5,ry+105)),fill=color,width=15)
    draw.line(((rx+5,ry+73),(rx+36,ry+73)),fill=luminous,width=10)
    # Foreground thumbs prove the fragments are actually held.
    for hand_x,hand_y in ((lx,ly),(rx,ry)):
        draw.arc((hand_x-18,hand_y-14,hand_x+17,hand_y+16),
                 0,167,fill=(198,142,111),width=8)
    return info
