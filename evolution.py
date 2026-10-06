from __future__ import annotations
from datetime import datetime

MIN_VIEWS=50
MIN_ATTRIBUTED=25

def _f(x, default=0.0):
    try:return float(x)
    except (TypeError,ValueError):return default

def diagnose_video(entry:dict)->dict:
    a=entry.get("analytics") or {}
    reports=entry.get("analytics_reports") or {}
    traffic=reports.get("traffic_sources") or {}
    views=_f(a.get("views"))
    attributed=sum(_f(r.get("views")) for r in traffic.get("rows",[]))
    avp=_f(a.get("averageViewPercentage"))
    likes=_f(a.get("likes")); shares=_f(a.get("shares")); subs=_f(a.get("subscribersGained"))
    if reports.get("basic",{}).get("status")!="available" or traffic.get("status")!="available":
        return {"status":"insufficient_evidence","reason":"analytics reports incomplete"}
    if views<MIN_VIEWS or attributed<MIN_ATTRIBUTED:
        return {"status":"insufficient_evidence","reason":"sample below clean-learning threshold","views":views,"attributed_views":attributed}
    engage=(likes+2*shares+2*subs)/max(views,1)
    if avp<55:
        failure="hook_or_retention"
    elif avp>=80 and engage<.01:
        failure="payoff_or_shareability"
    elif avp>=70 and engage>=.01:
        failure="healthy"
    else:
        failure="mixed"
    return {"status":"diagnosed","failure":failure,"views":views,"attributed_views":attributed,
            "average_view_percentage":avp,"engagement_signal":round(engage,4)}

def winner_blueprints(data:dict,limit=3)->list[dict]:
    rows=[]
    for vid,e in (data.get("videos") or {}).items():
        if e.get("learning_excluded") or e.get("format")=="long": continue
        d=diagnose_video(e)
        if d.get("failure")!="healthy": continue
        score=d["average_view_percentage"] + min(20,d["engagement_signal"]*400)
        rows.append((score,vid,e,d))
    rows.sort(reverse=True,key=lambda x:x[0])
    out=[]
    for score,vid,e,d in rows[:limit]:
        out.append({"video_id":vid,"genre":e.get("genre"),"content_id":e.get("content_id"),
                    "score":round(score,2),"diagnosis":d,
                    "structure":{"genre":e.get("genre"),"selection_reason":e.get("selection_reason"),
                                 "stage0_score":e.get("stage0_score")}})
    return out

def evolution_state(data:dict)->dict:
    diagnoses={}
    counts={}
    for vid,e in (data.get("videos") or {}).items():
        if e.get("learning_excluded"): continue
        d=diagnose_video(e); diagnoses[vid]=d
        key=d.get("failure",d.get("status","unknown")); counts[key]=counts.get(key,0)+1
    return {"version":1,"diagnosis_counts":counts,"winner_blueprints":winner_blueprints(data),
            "rule":"reuse abstract winning structure only; never copy finished scripts/assets"}


OPTIMIZATION_DEFAULTS={"min_publish_score":58.0,"packaging_weight":0.10,"story_weight":0.10,"winner_genre_bonus":5.0}
OPTIMIZATION_BOUNDS={"min_publish_score":(52.0,75.0),"packaging_weight":(.08,.18),"story_weight":(.08,.18),"winner_genre_bonus":(0.0,8.0)}

def _bound(name,value):
    lo,hi=OPTIMIZATION_BOUNDS[name]
    return round(max(lo,min(hi,float(value))),3)

def optimization_policy(data:dict)->dict:
    """Bounded self-optimization from qualified analytics; never rewrites code."""
    current=dict(OPTIMIZATION_DEFAULTS)
    current.update({k:v for k,v in (data.get("optimization_policy") or {}).items() if k in current})
    strategy=data.get("strategy") or {}
    clean=sum(max(0,int(v)) for v in (strategy.get("evidence") or {}).values())
    counts=(data.get("evolution") or {}).get("diagnosis_counts") or {}
    healthy=int(counts.get("healthy") or 0)
    weak=int(counts.get("hook_or_retention") or 0)+int(counts.get("payoff_or_shareability") or 0)
    proposal=dict(current); reasons=[]
    if clean>=6 and weak>healthy:
        proposal["min_publish_score"]=_bound("min_publish_score",current["min_publish_score"]+1)
        proposal["packaging_weight"]=_bound("packaging_weight",current["packaging_weight"]+.01)
        proposal["story_weight"]=_bound("story_weight",current["story_weight"]+.01)
        reasons.append("qualified evidence favors a stricter retention/payoff gate")
    elif clean>=6 and healthy>=3 and healthy>weak:
        proposal["min_publish_score"]=_bound("min_publish_score",current["min_publish_score"]-.5)
        reasons.append("multiple qualified videos are healthy; cautiously widen acceptance")
    proposal.update({"evidence_count":clean,"reason":"; ".join(reasons) if reasons else "hold: insufficient or balanced evidence",
        "guardrails":{"bounded_parameters_only":True,"arbitrary_code_rewrite":False,"credential_changes":False,
        "workflow_changes":False,"privacy_changes":False,"safety_rule_changes":False,"platform_bypass":False}})
    return proposal
