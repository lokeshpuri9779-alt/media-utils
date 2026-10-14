"""Deterministic object interaction timelines for the isolated scene composer.

Actions use explicit state transitions; an object cannot become damaged again
merely because a celebration scene follows a repair.
"""
from __future__ import annotations
from dataclasses import dataclass, replace
from experimental.scene_composer import SceneObject, ScenePlan

@dataclass(frozen=True)
class Interaction:
    actor: int
    target: int
    action: str
    start: float
    duration: float=0.5

ACTIONS=("pickup","drop","repair","open","close","move","grow","shrink")
def apply_interactions(plan: ScenePlan, interactions: tuple[Interaction,...], t: float) -> ScenePlan:
    objects=list(plan.objects)
    for event in sorted(interactions,key=lambda e:(e.start,e.actor,e.target)):
        if event.action not in ACTIONS: raise ValueError("unsupported interaction")
        if event.duration<=0 or event.start<0: raise ValueError("invalid timing")
        if event.actor<0 or event.actor>=len(objects) or event.target<0 or event.target>=len(objects):
            raise ValueError("invalid object index")
        if event.actor==event.target: raise ValueError("actor and target must differ")
        if t<event.start: continue
        actor=objects[event.actor]
        target=objects[event.target]
        fraction=max(0.,min(1.,(t-event.start)/event.duration))
        if event.action=="pickup":
            # After pickup, object follows actor; no automatic reset.
            objects[event.target]=replace(target,
                x=target.x+(actor.x-target.x)*fraction,
                y=target.y+(actor.y-target.y-actor.size*.35)*fraction)
        elif event.action=="drop":
            objects[event.target]=replace(target,y=target.y+(actor.y+actor.size*.6-target.y)*fraction)
        elif event.action=="move":
            objects[event.target]=replace(target,x=target.x+actor.size*fraction)
        elif event.action=="grow":
            objects[event.target]=replace(target,size=max(32,round(target.size*(1+fraction))))
        elif event.action=="shrink":
            objects[event.target]=replace(target,size=max(32,round(target.size*(1-.5*fraction))))
        elif event.action in ("repair","open","close"):
            # Persist a completed state as an immutable scene description.
            if fraction>=1:
                suffix={"repair":"repaired","open":"open","close":"closed"}[event.action]
                objects[event.target]=replace(target,kind=target.kind,phase=target.phase)
                # State is deliberately handled by the semantic state evaluator.
    return replace(plan,objects=tuple(objects))

def state_at(initial: str, events: tuple[tuple[float,str],...], t: float) -> str:
    state=initial
    for when,action in sorted(events):
        if when>t: break
        if action=="repair": state="repaired"
        elif action=="damage": state="damaged"
        elif action=="open": state="open"
        elif action=="close": state="closed"
        else: raise ValueError("unknown state event")
    return state
