"""Deliberately damage real frog frames to test image-evidence sensitivity.

No simulated passes: control input is the same actual CPU-rendered PNGs
uploaded for human review. Original image files are never mutated.
"""
import argparse
import json
from pathlib import Path
from tools.experimental_visual_motion_audit import SCENES,decode,score


def check(name,frames,report,expected):
    result=score(frames,report,"frog")
    failed=[k for k,v in result["checks"].items() if not v]
    if result["passed"] or expected not in failed:
        raise AssertionError(f"{name}: expected {expected} rejection; failed={failed}")
    if any(result[k] for k in ("approved","published","production_ready")):
        raise AssertionError("Unsafe gate opened")
    return {"case":name,"rejected":True,"failed_checks":failed}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--directory",type=Path,required=True)
    args=parser.parse_args()
    report=json.loads((args.directory/"review.json").read_text())
    frames=decode(args.directory,SCENES["frog"]["frames"])
    valid=score(frames,report,"frog")
    if not valid["passed"]:
        raise AssertionError(f"Source render failed pixel checks: {valid}")
    results=[]

    cast=frames.copy()
    cast[10]=frames[9]
    results.append(check("magnet_freezes_during_cast",cast,report,"magnet_cast"))

    lift=frames.copy()
    lift[17]=frames[16]
    results.append(check("paper_plane_lift_stalls",lift,report,"airplane_lift"))

    planting=frames.copy()
    planting[25]=frames[24]
    results.append(check("seed_planting_stalls",planting,report,"seed_planting"))

    wrong_cut=frames.copy()
    wrong_cut[10]=frames[22]
    results.append(check("unplanned_cut_during_rescue",wrong_cut,report,"magnet_cast"))

    no_sprout=frames.copy()
    for i in (29,30,31):
        no_sprout[i]=frames[28]
    results.append(check("sprout_never_visible",no_sprout,report,
                         "sprout_color_appears_after_planting"))

    premature=frames.copy()
    premature[28]=frames[31]
    results.append(check("sprout_visible_too_early",premature,report,
                         "sprout_color_appears_after_planting"))

    unsafe=dict(report)
    unsafe["production_ready"]=True
    results.append(check("production_flag_tampered",frames,unsafe,
                         "closed_review_gates"))

    result={
      "source_render_passed":True,
      "negative_case_count":len(results),
      "all_corruptions_rejected":all(x["rejected"] for x in results),
      "results":results,"approved":False,"published":False,
      "production_ready":False,"paid_apis_used":False,
      "manual_visual_review_required":True,
      "semantic_quality":"not_verified"
    }
    (args.directory/"visual_motion_negative_controls.json").write_text(
       json.dumps(result,indent=2)+"\n")
    print("ASTRA_FROG_IMAGE_NEGATIVE_CONTROLS="+json.dumps(result),flush=True)
    if not result["all_corruptions_rejected"] or len(results)!=7:
        raise SystemExit(1)


if __name__=="__main__":main()
