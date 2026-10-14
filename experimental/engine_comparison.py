"""Fail-closed ASTRA engine comparison report. Never changes publisher settings."""
from __future__ import annotations
import argparse,json
from pathlib import Path

REQUIRED=("render_success","decode_success","audio_present","captions_present","story_coherent","motion_gate_passed","assets_approved")

def evaluate(report):
    missing=[k for k in REQUIRED if k not in report]
    if missing: return {"eligible":False,"reason":"missing_evidence","missing":missing}
    failed=[k for k in REQUIRED if report[k] is not True]
    if failed:return {"eligible":False,"reason":"failed_quality_gates","failed":failed}
    if not isinstance(report.get("render_seconds"),(int,float)) or report["render_seconds"]<=0:
        return {"eligible":False,"reason":"missing_render_benchmark"}
    return {"eligible":True,"reason":"all_required_checks_passed","render_seconds":report["render_seconds"]}

def compare(main,experimental):
    baseline=evaluate(main)
    candidate=evaluate(experimental)
    return {"baseline":baseline,"experimental":candidate,
            "recommendation":"review_candidate" if candidate["eligible"] else "keep_main",
            "switch_main":False,"publish":False}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--main",required=True);p.add_argument("--experimental",required=True)
    p.add_argument("--output",default="engine_comparison.json")
    a=p.parse_args()
    result=compare(json.loads(Path(a.main).read_text()),json.loads(Path(a.experimental).read_text()))
    Path(a.output).write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
