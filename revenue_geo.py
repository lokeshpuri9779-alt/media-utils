from __future__ import annotations
from collections import defaultdict

# Directional cold-start priors only; never represented as actual channel RPM.
# Actual monetized channel revenue/geography data overrides these once available.
PRIORS={"US":1.00,"GB":0.86,"CA":0.84,"AU":0.88,"DE":0.78,"IE":0.78,"NL":0.74,"SG":0.82,"IN":0.30}
MIN_COUNTRY_VIEWS=50

def _n(v):
    try:return float(v or 0)
    except (TypeError,ValueError):return 0.0

def geography_state(data:dict)->dict:
    agg=defaultdict(lambda:{"views":0.0,"minutes":0.0,"revenue":0.0,"revenue_seen":False})
    for entry in (data.get("videos") or {}).values():
        if entry.get("learning_excluded"): continue
        report=(entry.get("analytics_reports") or {}).get("geography") or {}
        if report.get("status")!="available": continue
        for row in report.get("rows") or []:
            c=str(row.get("country") or "").upper()
            if not c: continue
            a=agg[c]; a["views"]+=_n(row.get("views")); a["minutes"]+=_n(row.get("estimatedMinutesWatched"))
            if row.get("estimatedRevenue") is not None:
                a["revenue"]+=_n(row.get("estimatedRevenue")); a["revenue_seen"]=True
    ranked=[]
    for c,a in agg.items():
        if a["views"]<MIN_COUNTRY_VIEWS: continue
        retention=a["minutes"]/max(a["views"],1)
        actual_rpm=(a["revenue"]*1000/a["views"]) if a["revenue_seen"] else None
        confidence=min(1.0,a["views"]/500.0)
        prior=PRIORS.get(c,0.45)
        # Revenue wins when observed; otherwise use a weak directional prior plus measured watch quality.
        value=(actual_rpm if actual_rpm is not None else prior)*(0.5+0.5*confidence)*(0.5+min(retention,2.0)/4)
        ranked.append({"country":c,"views":int(a["views"]),"minutes_per_view":round(retention,4),
          "actual_rpm":round(actual_rpm,4) if actual_rpm is not None else None,
          "prior_index":prior,"confidence":round(confidence,3),"opportunity_score":round(value,4)})
    ranked.sort(key=lambda x:(x["opportunity_score"],x["views"]),reverse=True)
    return {"mode":"actual_revenue" if any(x["actual_rpm"] is not None for x in ranked) else ("measured_demand" if ranked else "cold_start"),
      "ranked_countries":ranked[:12],"cold_start_priors":PRIORS,
      "guardrails":{"fake_location":False,"vpn_manipulation":False,"bot_traffic":False},
      "note":"Priors are directional indices, not promised RPM. Actual channel revenue overrides priors."}

def trend_regions(data:dict)->list[str]:
    ranked=geography_state(data)["ranked_countries"]
    regions=[x["country"] for x in ranked[:2]]
    return regions or ["US","IN"]
