"""Deterministic multi-scene story director for isolated Pillow experiments."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib,random
from experimental.scene_composer import SceneObject,ScenePlan
from experimental.interaction_engine import state_at

LOCATIONS={
 "garden":((120,171,193),(80,139,99)),
 "village":((187,207,221),(112,145,94)),
 "forest":((74,125,111),(44,104,76)),
 "desert":((222,190,145),(190,155,103)),
 "night_sky":((24,35,75),(59,75,98)),
 "workshop":((107,126,151),(91,96,104)),
}
PLOTS=("repair","rescue","discovery","delivery","celebration","transformation")
ACTORS=("dog","cat","rabbit","bird","fish")
PROPS=("apple","shoe","backpack","flower","house","watch","umbrella","hat")
BEATS={
 "repair":("problem","investigate","repair","celebrate"),
 "rescue":("danger","search","rescue","reunion"),
 "discovery":("mystery","explore","discover","share"),
 "delivery":("request","travel","deliver","thank"),
 "celebration":("invitation","prepare","gather","dance"),
 "transformation":("ordinary","experiment","transform","reveal"),
}
ACTIONS={
 "problem":"idle","investigate":"sway","repair":"pulse","celebrate":"bounce",
 "danger":"sway","search":"slide","rescue":"float","reunion":"bounce",
 "mystery":"idle","explore":"slide","discover":"pulse","share":"float",
 "request":"idle","travel":"slide","deliver":"float","thank":"bounce",
 "invitation":"idle","prepare":"sway","gather":"float","dance":"spin",
 "ordinary":"idle","experiment":"spin","transform":"pulse","reveal":"bounce",
}
@dataclass(frozen=True)
class Story:
    seed: int
    plot: str
    location: str
    actor: str
    prop: str
    beats: tuple[str,...]
    title: str

def generate(seed: int, plot: str|None=None, location: str|None=None) -> Story:
    rng=random.Random(seed)
    plot=plot or rng.choice(PLOTS)
    location=location or rng.choice(tuple(LOCATIONS))
    if plot not in PLOTS or location not in LOCATIONS: raise ValueError("unknown plot or location")
    actor=rng.choice(ACTORS)
    prop=rng.choice(PROPS)
    return Story(seed,plot,location,actor,prop,BEATS[plot],
                 f"The {actor} and the {prop}: {plot.title()}")

def plan_for(story: Story, beat_index: int, width: int=360,height: int=640) -> ScenePlan:
    if not 0<=beat_index<len(story.beats): raise ValueError("invalid beat")
    beat=story.beats[beat_index]
    bg,_=LOCATIONS[story.location]
    # State is derived from timeline, never reset by a subsequent beat.
    events=((0,"damage"),(2,"repair")) if story.plot=="repair" else ()
    condition=state_at("intact",events,beat_index)
    prop_action=ACTIONS[beat]
    # Stable spatial identities across beats; motion is evaluated by composer.
    objects=[
      SceneObject(story.actor,"animals",105,435,112,"bounce" if beat_index==3 else "sway",story.seed%7),
      SceneObject(story.prop,"food" if story.prop=="apple" else "products",
                  246,456,105,prop_action),
    ]
    if story.location=="night_sky":
        objects.append(SceneObject("moon","nature",275,105,88,"float"))
        objects.append(SceneObject("star","nature",73,117,60,"pulse"))
    else:
        objects.append(SceneObject("sun","nature",286,102,88,"pulse"))
        objects.append(SceneObject("cloud","nature",88,164,104,"slide"))
    return ScenePlan(tuple(objects),width,height,bg)

def signature(story: Story) -> str:
    return hashlib.sha256(repr((story.plot,story.location,story.actor,story.prop,story.beats)).encode()).hexdigest()

def batch(count: int, seed: int=0) -> tuple[Story,...]:
    if not 1<=count<=1000: raise ValueError("batch size must be 1..1000")
    stories=[]
    seen=set()
    for offset in range(count*20):
        story=generate(seed+offset)
        sig=signature(story)
        if sig not in seen:
            stories.append(story);seen.add(sig)
            if len(stories)==count: return tuple(stories)
    raise ValueError("not enough distinct stories in selection space")
