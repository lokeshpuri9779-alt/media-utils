"""Deterministic zero-cost bank of 1,024 distinct story *drafts*.

These are writing prompts, NOT approved scripts, render-ready videos, or
publishable stories. Human/creative review and the existing gates are required.
"""
from __future__ import annotations
import hashlib
import itertools
import json

HEROES = ("otter","fox","badger","mole","rabbit","turtle","owl","hedgehog")
SETTINGS = ("harbor","forest","mountain","market","observatory","library","garden","railway")
OBJECTS = ("lantern","clock","letter","kite")
PROBLEMS = ("disappears before the celebration","breaks during a storm",
            "reveals a hidden message","ends up in the wrong hands")
# 8 x 8 x 4 x 4 = 1024 distinct premise tuples.

def draft_bank():
    drafts=[]
    for hero, setting, obj, problem in itertools.product(HEROES,SETTINGS,OBJECTS,PROBLEMS):
        seed=f"{hero}|{setting}|{obj}|{problem}"
        uid=hashlib.sha256(seed.encode()).hexdigest()[:20]
        drafts.append({
            "content_id":"astra-draft-"+uid,
            "title":f"The {hero.title()} and the {setting.title()} {obj.title()}",
            "premise":f"In the {setting}, a {hero} discovers that a {obj} {problem}.",
            "hero":hero,"setting":setting,"central_object":obj,"conflict":problem,
            "kind":"unreviewed_causal_draft",
            "production_ready":False,
            "review_status":"requires_individual_story_development",
            "publication_allowed":False,
            "required_development":[
                "write distinctive setup and stakes",
                "create character-specific causal setback",
                "write earned discovery and resolution",
                "verify originality against prior plots",
                "render and pass full audiovisual QA"
            ],
        })
    assert len(drafts)==1024
    assert len({d["content_id"] for d in drafts})==1024
    return drafts

def export(path):
    from pathlib import Path
    Path(path).write_text(json.dumps(draft_bank(),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--output",default="astra_1024_story_drafts.json")
    a=p.parse_args()
    export(a.output)
    print("Exported 1024 unapproved drafts to",a.output)
