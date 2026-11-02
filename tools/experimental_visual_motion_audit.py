"""Review-only image evidence from fixed-camera story shots.

Reusable pixel functions, explicit per-scene thresholds. This is NOT
semantic validation, approval, production routing, or publishing.
"""
import argparse
import json
import subprocess
from pathlib import Path

W,H,FPS=384,576,8
SIZE=W*H*3
SCENES={
 "frog":{
  "frames":32,
  "fixed_camera":[[8,21],[22,27]],
  "motion":[
   {"name":"magnet_cast","roi":[5,250,280,395],"pairs":[[9,10],[10,11],[11,12]],"min":250,"max":8000},
   {"name":"airplane_lift","roi":[5,250,280,395],"pairs":[[13,14],[16,17],[20,21]],"min":450,"max":10000},
   {"name":"seed_planting","roi":[115,245,375,440],"pairs":[[23,24],[24,25],[26,27]],"min":700,"max":12000},
  ],
  "sprout":{"roi":[195,242,325,292],"limits":[[28,0,5],[29,80,500],[30,150,800],[31,800,5000]]},
 }
}


def decode(path,n):
    r=subprocess.run(["ffmpeg","-hide_banner","-loglevel","error",
       "-framerate",str(FPS),"-start_number","0",
       "-i",str(path/"frame_%03d.png"),"-frames:v",str(n),
       "-f","rawvideo","-pix_fmt","rgb24","pipe:1"],
       stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
    if len(r.stdout)!=n*SIZE:raise ValueError("Wrong frame count/size")
    raw=memoryview(r.stdout)
    return [raw[i*SIZE:(i+1)*SIZE] for i in range(n)]


def roi_valid(roi):
    return (len(roi)==4 and
      0<=roi[0]<roi[2]<=W and 0<=roi[1]<roi[3]<=H)


def changed_pixels(a,b,roi,threshold=28):
    if not roi_valid(roi) or len(a)!=SIZE or len(b)!=SIZE:
        raise ValueError("Invalid RGB frame or ROI")
    left,top,right,bottom=roi
    count=0
    for y in range(top,bottom):
        for x in range(left,right):
            i=3*(y*W+x)
            if (abs(a[i]-b[i])>threshold or
                abs(a[i+1]-b[i+1])>threshold or
                abs(a[i+2]-b[i+2])>threshold):
                count+=1
    return count


def green_pixels(frame,roi):
    if not roi_valid(roi) or len(frame)!=SIZE:
        raise ValueError("Invalid RGB frame or ROI")
    left,top,right,bottom=roi
    count=0
    for y in range(top,bottom):
        for x in range(left,right):
            i=3*(y*W+x)
            r,g,b=frame[i],frame[i+1],frame[i+2]
            if g>80 and 2*g>3*r and 100*g>113*b:
                count+=1
    return count


def score(frames,report,profile):
    if profile not in SCENES:raise ValueError("Unknown story profile")
    cfg=SCENES[profile]
    n=cfg["frames"]
    safe=(len(frames)==n and len(report.get("frames",[]))==n
          and report.get("success") is True
          and report.get("editorial_review_required") is True
          and report.get("semantic_quality")=="not_verified"
          and all(report.get(k) is False for k in
            ("approved","published","production_ready","paid_apis_used"))
          and [f.get("frame") for f in report["frames"]]==list(range(n)))
    checks={"closed_review_gates":safe}
    evidence={}
    if safe:
        for a,b in cfg["fixed_camera"]:
            pts=[report["frames"][i]["camera_xyz"] for i in range(a,b+1)]
            checks[f"camera_stable_{a}_{b}"]=all(
                len(p)==3 and all(abs(x-y)<.0001 for x,y in zip(pts[0],p))
                for p in pts[1:])
        for item in cfg["motion"]:
            measurements=[changed_pixels(frames[i],frames[j],item["roi"])
                          for i,j in item["pairs"]]
            evidence[item["name"]]=measurements
            checks[item["name"]]=all(item["min"]<=v<=item["max"]
                                     for v in measurements)
        sprout=cfg["sprout"]
        greens={str(i):green_pixels(frames[i],sprout["roi"])
                for i,_,_ in sprout["limits"]}
        evidence["sprout_green_pixels"]=greens
        checks["sprout_color_appears_after_planting"]=all(
            lo<=greens[str(i)]<=hi for i,lo,hi in sprout["limits"])
    return {"profile":profile,"passed":all(checks.values()),
       "checks":checks,"evidence":evidence,
       "evidence_scope":"fixed-ROI rendered-pixel motion/color only",
       "semantic_quality":"not_verified","cinematic_quality":"not_verified",
       "manual_visual_review_required":True,"approved":False,
       "published":False,"production_ready":False,"paid_apis_used":False}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--profile",choices=tuple(SCENES),required=True)
    p.add_argument("--directory",type=Path,required=True)
    args=p.parse_args()
    result=score(decode(args.directory,SCENES[args.profile]["frames"]),
       json.loads((args.directory/"review.json").read_text()),args.profile)
    (args.directory/"visual_motion_audit.json").write_text(
        json.dumps(result,indent=2)+"\n")
    print("ASTRA_VISUAL_MOTION_AUDIT="+json.dumps(result),flush=True)
    if not result["passed"]:raise SystemExit(1)


if __name__=="__main__":main()
