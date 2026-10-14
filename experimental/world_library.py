"""Extensible semantic world catalog for ASTRA experimental animation.

These are descriptive taxonomies, not finished visual assets. Each category has
a stable procedural variant selector and metadata for future renderer adapters.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib

TAXONOMY = {
 "animals": ("dog","cat","horse","cow","goat","sheep","pig","rabbit","fox","wolf","bear","deer","elephant","giraffe","lion","tiger","leopard","monkey","gorilla","panda","koala","kangaroo","otter","seal","dolphin","whale","shark","octopus","crab","turtle","frog","snake","lizard","crocodile","butterfly","bee","ant","spider","beetle","dragonfly","eagle","owl","parrot","pigeon","duck","goose","chicken","penguin","flamingo","peacock"),
 "flora": ("oak","pine","palm","bamboo","birch","maple","willow","mangrove","cactus","succulent","fern","moss","algae","mushroom","rose","sunflower","tulip","lotus","lily","orchid","daisy","lavender","hibiscus","jasmine","marigold","dandelion","wheat","rice","corn","sugarcane","banana","mango","apple","coconut","grape","strawberry","tomato","potato","carrot","pumpkin"),
 "products": ("phone","tablet","laptop","camera","television","speaker","headphones","watch","smartwatch","lamp","fan","refrigerator","oven","blender","kettle","vacuum","washing-machine","backpack","suitcase","shoe","shirt","jacket","hat","glasses","bottle","mug","plate","spoon","toy-car","doll","robot-toy","board-game","book","notebook","pen","pencil","paintbrush","toothbrush","soap","shampoo","perfume","medicine-box","first-aid-kit","bicycle","scooter","helmet","umbrella","tent","sleeping-bag","flashlight","toolbox"),
 "vehicles": ("car","bus","truck","van","taxi","ambulance","fire-engine","police-car","train","tram","subway","bicycle","motorcycle","scooter","skateboard","boat","canoe","sailboat","ship","submarine","airplane","helicopter","drone","rocket","tractor","bulldozer","excavator","forklift","spaceship"),
 "architecture": ("house","apartment","cottage","skyscraper","school","hospital","library","museum","castle","tower","bridge","tunnel","station","airport","harbor","stadium","theater","restaurant","cafe","shop","factory","warehouse","barn","greenhouse","lighthouse","temple","fountain","playground","windmill","dam","water-tower"),
 "nature": ("mountain","hill","cliff","canyon","cave","volcano","river","lake","waterfall","ocean","beach","island","glacier","desert","forest","meadow","swamp","reef","cloud","rainbow","star","moon","sun","meteor","crystal","rock","sand-dune","iceberg","geyser","hot-spring"),
 "food": ("bread","pizza","burger","sandwich","rice","noodles","pasta","soup","salad","cake","cookie","ice-cream","chocolate","apple","banana","orange","mango","strawberry","grape","carrot","potato","corn","tomato","egg","cheese","milk","juice","tea","coffee","water","honey"),
 "tools": ("hammer","screwdriver","wrench","pliers","saw","drill","paint-roller","shovel","rake","hoe","ladder","rope","pulley","tape-measure","scissors","needle","sewing-machine","flashlight","magnifier","microscope","telescope","compass","map","camera-tripod","fishing-rod","net","bucket","broom","mop","wheelbarrow"),
 "furniture": ("chair","stool","sofa","table","desk","bed","wardrobe","bookshelf","cabinet","drawer","bench","rocking-chair","lamp-stand","mirror","rug","curtain","shelf","counter","crib","hammock"),
 "fantasy": ("dragon","unicorn","griffin","phoenix","mermaid","fairy","giant","golem","slime","ghost","friendly-monster","wizard-staff","magic-book","enchanted-tree","floating-island","portal","treasure-chest","crystal-ball","magic-wand","flying-carpet"),
}
VARIANTS = ("classic","miniature","giant","stylized","rounded","angular","retro","futuristic")
MATERIALS = ("wood","metal","glass","plastic","fabric","stone","ceramic","organic")
COLORS = ("red","orange","yellow","green","cyan","blue","purple","pink","white","black","brown","gray")
STATES = ("new","used","damaged","repaired","wet","dirty","clean","glowing")
ANIMATION_TAGS = {
 "animals": ("idle","walk","run","jump","eat","sleep","react"),
 "flora": ("sway","grow","bloom","shed","wilt"),
 "products": ("rotate","open","close","activate","deactivate"),
 "vehicles": ("idle","drive","turn","brake","accelerate"),
 "architecture": ("door-open","door-close","light-on","light-off"),
 "nature": ("flow","erupt","drift","ripple"),
 "food": ("serve","slice","pour","mix"),
 "tools": ("pick-up","use","put-down"),
 "furniture": ("move","rotate","fold"),
 "fantasy": ("hover","glow","fly","transform"),
}
@dataclass(frozen=True)
class WorldAsset:
    category: str
    kind: str
    variant: str
    material: str
    color: str
    state: str
    supported_action_tags: tuple[str,...]

def _pick(seed: str, namespace: str, choices: tuple[str,...]) -> str:
    digest=hashlib.sha256((namespace+":"+seed).encode("utf-8")).digest()
    return choices[int.from_bytes(digest[:8],"big")%len(choices)]

def make_asset(category: str, seed: str) -> WorldAsset:
    if category not in TAXONOMY:
        raise ValueError(f"Unknown category: {category}")
    return WorldAsset(category, _pick(seed,category,TAXONOMY[category]),
                      _pick(seed,"variant",VARIANTS),
                      _pick(seed,"material",MATERIALS),
                      _pick(seed,"color",COLORS),
                      _pick(seed,"state",STATES),
                      ANIMATION_TAGS[category])

def counts() -> dict[str,int]:
    return {"categories":len(TAXONOMY),
            "base_kinds":sum(map(len,TAXONOMY.values())),
            "descriptive_combinations":sum(map(len,TAXONOMY.values()))*len(VARIANTS)*len(MATERIALS)*len(COLORS)*len(STATES)}
