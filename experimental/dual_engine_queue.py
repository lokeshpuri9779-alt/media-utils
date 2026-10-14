"""Isolated dual-engine queue planning; no production publisher side effects."""
from __future__ import annotations
import hashlib,json
from experimental.dual_engine_policy import ENGINES,ENGINE_MAIN

def plan_jobs(episodes):
    if not isinstance(episodes,list):raise ValueError("Episodes must be a list")
    jobs=[];seen=set()
    for ep in episodes:
        if not isinstance(ep,dict):raise ValueError("Episode must be an object")
        story=str(ep.get("story_id","")).strip()
        engine=ep.get("engine",ENGINE_MAIN)
        if not story or engine not in ENGINES:raise ValueError("Invalid story or engine")
        key=(story,engine)
        if key in seen:raise ValueError("Duplicate story/engine job")
        seen.add(key)
        uid=hashlib.sha256(f"{story}:{engine}".encode()).hexdigest()[:16]
        jobs.append({"job_id":uid,"story_id":story,"engine":engine,
                     "queue":"shadow_main" if engine==ENGINE_MAIN else "shadow_cinematic",
                     "status":"pending","publish":False,"approved":False})
    return {"jobs":jobs,"publication_enabled":False,
            "engine_retirement_allowed":False,"main_workflow_modified":False}

if __name__=="__main__":
    import argparse
    from pathlib import Path
    p=argparse.ArgumentParser()
    p.add_argument("episodes");p.add_argument("--output",default="dual_engine_queue.json")
    a=p.parse_args()
    result=plan_jobs(json.loads(Path(a.episodes).read_text()))
    Path(a.output).write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
