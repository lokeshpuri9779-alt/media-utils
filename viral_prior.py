from __future__ import annotations
import math, re

# Stage-0 priors: useful before the channel has enough clean audience data.
# These score structures, not copied videos or copyrighted wording.
POWER = re.compile(r"\b(why|how|what|can you|find|spot|before|never|last|first|secret|missing|odd|fast|seconds?|hottest|slower|extra|same)\b", re.I)
PAYOFF = re.compile(r"\b(answer|reveal|because|opens?|shows?|no |yes |same|finally|on the other side|years?|days?|row|col)\b", re.I)

def _clip(x, lo=0.0, hi=100.0):
    return max(lo, min(hi, float(x)))

def score_candidate(c: dict, *, trend_matches=None, channel_score=None) -> dict:
    hook=(c.get("hook") or "").strip()
    question=(c.get("question") or "").strip()
    answer=(c.get("answer") or "").strip()
    title=(c.get("title") or "").strip()
    trend_matches=trend_matches if trend_matches is not None else c.get("trend_matches") or []

    hook_score=45 + min(25, 5*len(POWER.findall(hook+" "+title)))
    if 4 <= len(hook.split()) <= 8: hook_score += 12
    if "?" in hook or "?" in title: hook_score += 6

    payoff=48
    if answer: payoff += 16
    if PAYOFF.search(answer): payoff += 12
    if question and answer and question.lower()!=answer.lower(): payoff += 8

    clarity=82
    if len(question)>180: clarity-=18
    if len(title)>75: clarity-=10
    if len(hook)>45: clarity-=10

    originality=78 if c.get("genre") in {"fiction","tech","space","football"} else 66
    if c.get("content_id","").startswith("quiz-"): originality=62

    demand=62
    if c.get("source"): demand+=8
    trend=min(100, 45 + 18*len(trend_matches)) if trend_matches else 45

    # Before sufficient clean channel evidence: 50% proven structural priors,
    # 30% live demand/trend, 20% exploration/channel learning.
    structural=(hook_score*.34 + payoff*.28 + clarity*.20 + originality*.18)
    channel=50 if channel_score is None else _clip(channel_score)
    total=.50*structural + .30*((demand+trend)/2) + .20*channel
    return {
        "total": round(_clip(total),2), "hook":round(_clip(hook_score),1),
        "payoff":round(_clip(payoff),1), "clarity":round(_clip(clarity),1),
        "originality":round(_clip(originality),1), "demand":round(_clip(demand),1),
        "trend":round(_clip(trend),1), "channel":round(channel,1),
        "weights":{"structural":.50,"live_demand":.30,"channel_or_exploration":.20},
    }

def calibration_weight(data: dict) -> float:
    """Increase reliance on channel evidence only after enough clean samples exist."""
    strategy=(data or {}).get("strategy") or {}
    evidence=strategy.get("evidence") or {}
    clean=sum(max(0,int(v)) for v in evidence.values())
    # 0 samples => 0; 30+ qualifying videos => full channel calibration.
    return min(1.0, clean/30.0)

def rank_candidates(candidates: list[dict], genre_scores: dict|None=None, data: dict|None=None) -> list[dict]:
    genre_scores=genre_scores or {}
    calibration=calibration_weight(data or {})
    ranked=[]
    for c in candidates:
        x=dict(c)
        raw=genre_scores.get(c.get("genre"))
        # Analytics scores are not naturally 0-100; gently normalize when present.
        channel=None if raw is None else _clip(50 + 12*math.log1p(max(0,float(raw))))
        x["prior_score"]=score_candidate(x, channel_score=channel)
        # Do not let tiny samples dominate. Channel adjustment ramps in gradually.
        if channel is not None:
            base=x["prior_score"]["total"]
            x["prior_score"]["total"]=round(_clip(base + calibration*(channel-50)*.20),2)
        x["prior_score"]["calibration_weight"]=round(calibration,3)
        ranked.append(x)
    return sorted(ranked, key=lambda x:x["prior_score"]["total"], reverse=True)


def adaptive_exploration(data: dict) -> float:
    """Bounded exploration schedule: learn broadly early, exploit more as evidence grows."""
    c=calibration_weight(data or {})
    # 25% at cold start -> 10% with mature clean evidence.
    return round(max(.10, min(.25, .25 - .15*c)), 3)

def policy_snapshot(data: dict) -> dict:
    c=calibration_weight(data or {})
    strategy=(data or {}).get("strategy") or {}
    return {
        "version": 1,
        "calibration_weight": round(c,3),
        "exploration_rate": adaptive_exploration(data or {}),
        "winner": strategy.get("winner"),
        "genre_scores": strategy.get("genre_scores") or {},
        "evidence": strategy.get("evidence") or {},
        "guardrails": {
            "min_exploration": .10,
            "max_exploration": .25,
            "arbitrary_code_rewrite": False,
            "platform_rule_bypass": False,
        },
    }
