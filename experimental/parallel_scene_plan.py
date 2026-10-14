"""Plan independent scene-rendering jobs for GitHub Actions.

Creates deterministic scene assignments; no credentials, publishing, or
automatic workflow triggers. Each worker writes only its own scene output.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path

def plan_jobs(scene_count=12,workers=4,duration=24,fps=30):
    if not 1<=scene_count<=100:raise ValueError("scene count must be 1..100")
    if not 1<=workers<=16:raise ValueError("workers must be 1..16")
    if not 20<=duration<=30 or fps not in (24,30):raise ValueError("unsupported video settings")
    total_frames=round(duration*fps)
    assignments=[]
    for i in range(scene_count):
        start=round(i*total_frames/scene_count)
        end=round((i+1)*total_frames/scene_count)
        assignments.append({"scene":i,"worker":i%workers,"start_frame":start,
                            "end_frame":end,"frames":end-start})
    assert sum(a["frames"] for a in assignments)==total_frames
    return {"duration":duration,"fps":fps,"frames":total_frames,
            "scene_count":scene_count,"workers":workers,
            "jobs":assignments,"publishing_enabled":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--scenes",type=int,default=12)
    p.add_argument("--workers",type=int,default=4)
    p.add_argument("--output",default="premium-demo/parallel-plan.json")
    args=p.parse_args()
    data=plan_jobs(args.scenes,args.workers)
    path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2)+"\n")
    print(json.dumps({"output":str(path),"scenes":data["scene_count"],"workers":data["workers"]}))

if __name__=="__main__":main()
