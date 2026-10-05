from __future__ import annotations

import hashlib, json, re
from pathlib import Path

POLICY_VERSION = "2026-10-ypp-v1"
BLOCK_THRESHOLD = 0.82
WARN_THRESHOLD = 0.68

def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", (text or "").lower())

def _tokens(text: str) -> set[str]:
    return {x for x in _norm(text).split() if len(x) > 2}

def similarity(a: str, b: str) -> float:
    x,y=_tokens(a),_tokens(b)
    return len(x&y)/max(1,len(x|y))

def disclosure_required(meta: dict) -> bool:
    # Conservative: realistic synthetic/altered people, places or events require disclosure.
    return bool(meta.get("realistic_synthetic") or meta.get("altered_real_event") or meta.get("synthetic_real_person"))

def evaluate(title: str, description: str, meta: dict, performance: dict) -> dict:
    script=" ".join(str(meta.get(k) or "") for k in ("hook","question","prompt","answer","script"))
    current=" ".join((title, description, script))
    worst=0.0; match=None
    for vid,row in (performance.get("videos") or {}).items():
        prior=" ".join(str(row.get(k) or "") for k in ("title","description","hook","question","prompt","answer","script"))
        s=similarity(current,prior)
        if s>worst: worst,match=s,vid
    source=str(meta.get("source") or "")
    genre=str(meta.get("genre") or "")
    original=genre=="fiction" or bool(script.strip()) or bool(source)
    reasons=[]
    if worst>=BLOCK_THRESHOLD: reasons.append("near_duplicate_existing_video")
    if not original: reasons.append("insufficient_original_narrative_or_sourcing")
    if meta.get("reused_third_party_media") and not meta.get("transformative_commentary"): reasons.append("untransformed_reused_media")
    if meta.get("copyright_unlicensed"): reasons.append("unlicensed_copyright_material")
    decision="block" if reasons else ("review" if worst>=WARN_THRESHOLD else "allow")
    required=disclosure_required(meta)
    report={"policy_version":POLICY_VERSION,"decision":decision,"reasons":reasons,
            "max_similarity":round(worst,3),"matched_video_id":match,
            "ai_disclosure_required":required,
            "checks":{"originality":original,"mass_production_similarity":worst<BLOCK_THRESHOLD,
                      "reused_content_safe":not bool(meta.get("reused_third_party_media")) or bool(meta.get("transformative_commentary")),
                      "copyright_safe":not bool(meta.get("copyright_unlicensed"))}}
    report["fingerprint"]=hashlib.sha256(json.dumps(report,sort_keys=True).encode()).hexdigest()[:16]
    return report

def enforce(title: str, description: str, meta: dict, performance: dict) -> dict:
    report=evaluate(title,description,meta,performance)
    if report["decision"]!="allow":
        raise RuntimeError("YPP safety gate refused automatic publication: "+json.dumps(report,ensure_ascii=False))
    return report
