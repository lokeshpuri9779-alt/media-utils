"""Fast pre-publication frame QA for known ASTRA fiction visual artifacts.

This guard detects the long thin amber stage-guide curves and large sudden
edge-panel flashes seen in production screenshots. It is deliberately narrow:
brief in-story lamps, golden scenery, dialogue cards, and deliberate actor
cuts are not grounds for rejecting a video.

Only sample rendered frames at a few fixed moments per authored beat. It does
not rely on source-code strings, and it never requires an external model/API.
"""
from __future__ import annotations

import numpy as np
from astra_errors import CreativeReject


def _rgb(im):
    if im.size != (1080, 1920):
        raise ValueError("Unexpected ASTRA fiction frame size")
    return np.asarray(im.convert("RGB"), dtype=np.uint8)


def long_amber_guide_arc(image):
    """Recognize a thin long curved golden stroke in the story sky.

    Gold objects are valid; the signature is *many* isolated thin gold
    columns spread across the sky at meaningfully different y coordinates.
    """
    arr=_rgb(image)
    # Exclude headlines (above 560), grounding/prop areas (below 950),
    # and UI edges. A physical lantern is too narrow to match.
    roi=arr[560:950:3, 100:980:5].astype(np.int16)
    r,g,b=roi[:,:,0],roi[:,:,1],roi[:,:,2]
    mask=((r>=180)&(g>=135)&(g<=225)&(b<=180)&
          ((r-b)>=35)&((g-b)>=20))
    # A line 4-10 px thick occupies a small number of sampled rows;
    # broad walls, lanterns, building roofs and warm rectangles do not.
    columns=mask.sum(axis=0)
    slender=(columns>=1)&(columns<=6)
    if slender.sum()<65:
        return False
    span=np.flatnonzero(slender)
    if span[-1]-span[0]<100:
        return False
    xs=np.flatnonzero(slender).astype(np.float64)*5 + 100.0
    ys=np.argmax(mask,axis=0)[slender].astype(np.float64)*3 + 560.0
    if np.percentile(ys,90)-np.percentile(ys,10)<=42:
        return False
    # Architectural trim, warm foliage and shelves may also occupy many
    # thin golden columns, but those marks do not form ONE smooth arch.
    # A real guide arc follows a continuous, convex quadratic trajectory
    # with a substantial rise at its center and a small fit residual.
    try:
        coeff=np.polyfit(xs,ys,2)
    except (np.linalg.LinAlgError,ValueError):
        return False
    fit=np.polyval(coeff,xs)
    error=np.abs(ys-fit)
    lo,hi=float(xs.min()),float(xs.max())
    mid=(lo+hi)/2
    sag=(float(np.polyval(coeff,lo))+
         float(np.polyval(coeff,hi)))/2-float(np.polyval(coeff,mid))
    return bool(coeff[0]>0 and sag>48 and
                np.median(error)<18 and np.percentile(error,85)<36)


def sudden_edge_panel(a,b):
    """Flag edge-wide purple or tinted transition flashing within a beat.

    Check only the non-narrative edges. Character gesture/camera push occurs
    inside the story stage. A real cut between beats is evaluated separately.
    """
    first=_rgb(a)
    second=_rgb(b)
    for left,right in ((0,64),(1016,1080)):
        src=first[650:1280:14,left:right:8].astype(np.int16)
        dst=second[650:1280:14,left:right:8].astype(np.int16)
        diff=np.max(np.abs(src-dst),axis=2)
        if float(np.mean(diff>42))>.75 and float(diff.mean())>42:
            return True
    return False


def validate_fiction_frames(plan, renderer, total, *, max_beats=48):
    """Sample final composited frames before voice+video publication.

    A Studio render should never reach the public queue if a sampled frame
    contains a story-spanning decorative amber guide or an edge-wide flash.
    Full Shorts are sampled beat-by-beat. Longer stories are sampled evenly
    at a bounded cost and never rejected merely for having more scenes.
    """
    if not plan:
        raise CreativeReject("Fiction visual validation needs scene beats")
    if max_beats<2:
        raise ValueError("max_beats must allow first and last scenes")
    count=len(plan)
    if count<=max_beats:
        scene_indices=range(count)
    else:
        scene_indices=sorted(set(
            round(j*(count-1)/(max_beats-1)) for j in range(max_beats)))
    checks=0
    for i in scene_indices:
        shot=plan[i]
        dur=float(shot.get("duration") or 0)
        if dur<=.16:
            raise CreativeReject("Fiction scene too brief for visual QA")
        start=float(shot.get("start") or 0)
        times=(start+min(.04,dur*.10),
               start+min(.29,dur*.48))
        earlier=renderer(plan,times[0],"fiction",total)
        later=renderer(plan,times[1],"fiction",total)
        checks+=2
        if long_amber_guide_arc(earlier) or long_amber_guide_arc(later):
            raise CreativeReject(f"Fiction amber-guide-arc artifact in beat {i+1}")
        if sudden_edge_panel(earlier,later):
            raise CreativeReject(f"Fiction edge-transition flash in beat {i+1}")
    return {"pass": True, "sampled_frames": checks,
            "sampled_beats":len(scene_indices), "total_beats":count,
            "artifact_rules":("amber_arc","edge_flash")}
