#!/usr/bin/env python3
"""Compare independently verified renderer reports without claiming subjective quality."""
import json
import sys
from pathlib import Path

def load(path):
    obj=json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(obj,dict) or obj.get("pass") is not True:
        raise ValueError("unverified benchmark: "+str(path))
    return obj

def main():
    if len(sys.argv)!=3:
        raise SystemExit("usage: compare.py verified-baseline.json verified-candidate.json")
    baseline,candidate=map(load,sys.argv[1:])
    def measure(obj):
        b=obj.get("baseline.json",{})
        return float(b.get("render",{}).get("seconds",0))
    b,c=measure(baseline),measure(candidate)
    if b<=0 or c<=0:
        raise SystemExit("missing positive render timings")
    result={"baseline_seconds":b,"candidate_seconds":c,
            "speed_ratio":round(b/c,3),
            "candidate_faster":c<b,
            "note":"Speed comparison only; no visual-quality, originality, or animation claims."}
    print(json.dumps(result,indent=2))
if __name__=="__main__":
    main()
