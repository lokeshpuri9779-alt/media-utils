#!/usr/bin/env python3
"""ASTRA unified CPU-first pipeline. No paid services; publishing opt-in."""
import argparse, json, os, shutil, subprocess, sys, time
from pathlib import Path

STAGES = ("story", "images", "consistency", "animation", "narration", "edit", "quality", "publish")
ENV = {
    "story": "ASTRA_STORY_CMD",
    "images": "ASTRA_IMAGES_CMD",
    "consistency": "ASTRA_CONSISTENCY_CMD",
    "animation": "ASTRA_ANIMATION_CMD",
    "narration": "ASTRA_NARRATION_CMD",
    "edit": "ASTRA_EDIT_CMD",
    "quality": "ASTRA_QUALITY_CMD",
    "publish": "ASTRA_PUBLISH_CMD",
}
def execute(stage, out, dry_run, allow_publish):
    if stage == "publish" and not allow_publish:
        return {"status": "skipped", "reason": "Publishing requires --publish"}
    command = os.getenv(ENV[stage])
    if not command:
        return {"status": "blocked", "reason": "Missing command configuration: " + ENV[stage]}
    if dry_run:
        return {"status": "planned", "command": command}
    started = time.monotonic()
    # shell commands are operator-configured; never interpolate story/user text into commands.
    result = subprocess.run(command, shell=True, cwd=out, capture_output=True, text=True, timeout=3600)
    return {"status": "passed" if result.returncode == 0 else "failed",
            "exit_code": result.returncode, "seconds": round(time.monotonic()-started, 2),
            "stdout_tail": result.stdout[-1200:], "stderr_tail": result.stderr[-1200:]}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output", default="astra_unified_output")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--production", action="store_true", help="Require evidence of real AI generation, character consistency, and narration")
    args=parser.parse_args()
    out=Path(args.output).resolve()
    out.mkdir(parents=True,exist_ok=True)
    report={"pipeline":"astra-unified-v1", "dry_run":args.dry_run,
            "stages":{}, "status":"running"}
    for stage in STAGES:
        try:
            result=execute(stage,out,args.dry_run,args.publish)
        except (subprocess.TimeoutExpired, OSError) as error:
            result={"status":"failed","reason":str(error)}
        report["stages"][stage]=result
        if result["status"] in ("blocked","failed"):
            report["status"]="blocked" if result["status"]=="blocked" else "failed"
            break
    else:
        report["status"]="planned" if args.dry_run else "completed"
    if args.production and not args.dry_run and report["status"]=="completed":
        evidence_path=out/"production_evidence.json"
        try:
            evidence=json.loads(evidence_path.read_text())
            required=("ai_images_generated","character_consistency_verified","narration_generated","video_quality_verified")
            missing=[key for key in required if evidence.get(key) is not True]
        except (OSError, ValueError, TypeError):
            missing=["valid production_evidence.json"]
        if missing:
            report["status"]="blocked"
            report["production_gate"]={"status":"blocked","missing":missing}
        else:
            report["production_gate"]={"status":"passed"}
    (out/"run_report.json").write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
    return 0 if report["status"] in ("planned","completed") else 1
if __name__=="__main__":
    sys.exit(main())
