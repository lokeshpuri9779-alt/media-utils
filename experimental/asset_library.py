"""Deterministic procedural asset library for isolated ASTRA 2D experiments.

A compact combinatorial catalog: variants are descriptions, not pre-rendered sprites.
No external assets, licensing dependencies, or network calls.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib

SKIN_TONES = ("porcelain","peach","tan","brown","deep","olive","golden","rose")
BODY_TYPES = ("small","average","tall","round","athletic","wide","slender","compact")
HAIR_STYLES = ("short","long","curly","spiky","braided","bald","bob","ponytail")
OUTFITS = ("hoodie","overalls","jacket","dress","suit","sportswear","tunic","uniform")
PALETTES = ("coral","azure","mint","amber","violet","navy","lime","pink")
EXPRESSIONS = ("happy","sad","surprised","angry","curious","worried","sleepy","proud")
OBJECT_TYPES = ("ball","box","book","key","umbrella","flower","bag","cup","hat","toy",
                "tool","lamp","phone","gift","rope","kite","chair","wheel","map","bottle")
OBJECT_STATES = ("intact","damaged","open","closed","wet","dry","glowing","dirty","repaired","moving")
ENVIRONMENTS = ("park","beach","city","forest","kitchen","workshop","school","space",
                "desert","snow","cave","garden","market","castle","harbor","mountain",
                "library","museum","stadium","farm")
LIGHTING = ("dawn","day","sunset","night","overcast")
WEATHER = ("clear","rain","snow","wind","fog")
ACTIONS = ("idle","walk","run","jump","dance","wave","point","nod","shake","sit",
           "stand","crouch","reach","grab","carry","drop","throw","catch","push","pull",
           "repair","inspect","clap","cheer","turn","hide","peek","kick","roll","spin",
           "laugh","cry","surprise","greet","help","build","paint","sweep","read","write")

@dataclass(frozen=True)
class Character:
    skin: str
    body: str
    hair: str
    outfit: str
    palette: str
    expression: str

@dataclass(frozen=True)
class Prop:
    kind: str
    state: str

@dataclass(frozen=True)
class Scene:
    environment: str
    lighting: str
    weather: str

def _index(seed: str, namespace: str, n: int) -> int:
    digest=hashlib.sha256(f"{namespace}:{seed}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8],"big") % n

def character(seed: str) -> Character:
    dimensions=(SKIN_TONES,BODY_TYPES,HAIR_STYLES,OUTFITS,PALETTES,EXPRESSIONS)
    values=tuple(items[_index(seed,str(i),len(items))] for i,items in enumerate(dimensions))
    return Character(*values)

def prop(seed: str) -> Prop:
    return Prop(OBJECT_TYPES[_index(seed,"prop",len(OBJECT_TYPES))],
                OBJECT_STATES[_index(seed,"state",len(OBJECT_STATES))])

def scene(seed: str) -> Scene:
    return Scene(ENVIRONMENTS[_index(seed,"environment",len(ENVIRONMENTS))],
                 LIGHTING[_index(seed,"lighting",len(LIGHTING))],
                 WEATHER[_index(seed,"weather",len(WEATHER))])

def catalog_counts() -> dict[str,int]:
    from math import prod
    return {"character_combinations":prod(map(len,(SKIN_TONES,BODY_TYPES,HAIR_STYLES,OUTFITS,PALETTES,EXPRESSIONS))),
            "prop_combinations":len(OBJECT_TYPES)*len(OBJECT_STATES),
            "scene_combinations":len(ENVIRONMENTS)*len(LIGHTING)*len(WEATHER),
            "action_labels":len(ACTIONS)}
