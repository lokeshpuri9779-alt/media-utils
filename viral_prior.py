from __future__ import annotations
import math, re

# Stage-0 priors: useful before the channel has enough clean audience data.
# These score structures, not copied videos or copyrighted wording.
POWER = re.compile(r"\b(why|how|what|can you|find|spot|before|never|last|first|secret|missing|odd|fast|seconds?|hottest|slower|extra|same)\b", re.I)
PAYOFF = re.compile(r"\b(answer|reveal|because|opens?|shows?|no |yes |same|finally|on the other side|years?|days?|row|col)\b", re.I)
CURIOSITY = re.compile(r"\b(why|how|what|inside|behind|changed|really|surprising|strange|unexpected|secret|mystery)\b", re.I)

def creative_worthiness(c: dict) -> dict:
    """Fail closed when demand cannot support an interesting standalone story."""
    title=(c.get("title") or "").strip()
    hook=(c.get("hook") or "").strip()
    question=(c.get("question") or "").strip()
    answer=(c.get("answer") or "").strip()
    headline=(c.get("news_title") or "").strip()
    score=35.0
    reasons=[]
    if c.get("source"): score+=12
    if int(c.get("source_count") or 0)>=2: score+=8
    if question and answer and question.lower()!=answer.lower(): score+=12
    if CURIOSITY.search(title+" "+question): score+=10
    if headline and len(headline.split())>=5: score+=8
    if hook and len(hook.split())<=8: score+=5
    # Generic trend narration is not itself a story.
    generic=("drawing a fresh wave of search interest" in question.lower()
             and not re.search(r"\b(why|how|because|after|before|reveals?|changes?|first|last|new)\b",
                               headline+" "+answer,re.I))
    if generic:
        score-=25; reasons.append("trend signal lacks a standalone story angle")
    if len(answer.split())<10:
        score-=15; reasons.append("payoff too thin")
    score=_clip(score)
    return {"score":round(score,1),"pass":score>=65.0,
            "reasons":reasons or ["clear sourced question/payoff structure"]}

def packaging_score(c: dict) -> float:
    """Score the click promise without rewarding deception or empty clickbait."""
    title=(c.get("title") or "").strip()
    hook=(c.get("hook") or "").strip()
    payoff=(c.get("answer") or "").strip()
    score=52.0
    score += min(18, 4*len(CURIOSITY.findall(title+" "+hook)))
    if 28 <= len(title) <= 72: score += 10
    if hook and payoff: score += 8
    if c.get("source"): score += 7
    if re.search(r"\b(shocking|insane|you won't believe|must see)\b", title, re.I): score -= 18
    return _clip(score)

def story_score(c: dict) -> float:
    """Reward promise -> question -> sourced payoff structure."""
    hook=(c.get("hook") or "").strip()
    question=(c.get("question") or "").strip()
    answer=(c.get("answer") or "").strip()
    score=45.0 + (12 if hook else 0) + (12 if question else 0) + (18 if answer else 0)
    if c.get("source"): score += 8
    if question and answer and question.lower()!=answer.lower(): score += 5
    return _clip(score)

def _clip(x, lo=0.0, hi=100.0):
    return max(lo, min(hi, float(x)))

def score_candidate(c: dict, *, trend_matches=None, channel_score=None, packaging_weight=.10, story_weight=.10) -> dict:
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

    # RAYVAN should feel like a premium discovery/storytelling brand, not a
    # generic engagement-farm. Reward sourced discovery and original narrative;
    # strongly penalize game/challenge mechanics if they ever re-enter a pool.
    originality=82 if c.get("genre") in {"fiction","space","football","current"} else 70
    if c.get("source"): originality += 6
    if c.get("genre") == "challenge" or c.get("content_id","").startswith("quiz-"): originality=25

    demand=62
    if c.get("source"): demand+=8
    trend=min(100, 58 + 20*len(trend_matches)) if trend_matches else 25

    # Before sufficient clean channel evidence: 50% proven structural priors,
    # 30% live demand/trend, 20% exploration/channel learning.
    structural=(hook_score*.34 + payoff*.28 + clarity*.20 + originality*.18)
    channel=50 if channel_score is None else _clip(channel_score)
    package=packaging_score(c)
    story=story_score(c)
    # Case-study architecture: idea quality is necessary, but packaging and
    # narrative payoff are explicit gates rather than post-render decoration.
    pw=max(.08,min(.18,float(packaging_weight))); sw=max(.08,min(.18,float(story_weight)))
    remaining=max(.54,1.0-pw-sw)
    total=(remaining*.50)*structural + (remaining*.3125)*((demand+trend)/2) + (remaining*.1875)*channel + pw*package + sw*story
    return {
        "total": round(_clip(total),2), "hook":round(_clip(hook_score),1),
        "payoff":round(_clip(payoff),1), "clarity":round(_clip(clarity),1),
        "originality":round(_clip(originality),1), "demand":round(_clip(demand),1),
        "trend":round(_clip(trend),1), "channel":round(channel,1),
        "packaging":round(package,1), "story":round(story,1),
        "weights":{"structural":.40,"live_demand":.25,"channel_or_exploration":.15,"packaging":.10,"story":.10},
    }


def packaging_competition(c: dict) -> dict:
    """Choose the strongest truthful title/hook package before rendering.

    Variants may reframe a verified topic, but never add facts that are not
    already present in the candidate/source metadata.
    """
    x=dict(c)
    original_title=" ".join(str(x.get("title") or "").replace("#Shorts","").split()).strip()
    original_hook=" ".join(str(x.get("hook") or "").split()).strip()
    topic=" ".join(str(x.get("topic") or "").split()).strip()
    headline=" ".join(str(x.get("news_title") or "").split()).strip()
    if not topic:
        keys=x.get("keywords") or []
        topic=" ".join(str(keys[0] if keys else "").split()).strip()
    pretty=" ".join(w if w.isupper() else w.capitalize() for w in topic.split())
    def natural(value):
        value=" ".join(str(value or "").split())
        words=value.replace("?","").replace(":"," ").split()
        if len(words)>14: return False
        # Reject query-like noun piles and duplicated interrogative packaging.
        if re.search(r"(?i)\bwhat changed with\b.*\b(what changed|opposition|update)\b",value): return False
        if sum(1 for w in words if len(w)>14)>=3: return False
        return True

    titles=[]
    def add_title(value):
        value=" ".join(str(value or "").split()).strip(" -:|")
        value=re.sub(r"(?i)\s*#shorts\s*"," ",value).strip()
        if 10 <= len(value) <= 82 and natural(value) and value.lower() not in {t.lower() for t in titles}:
            titles.append(value)

    # For live/current stories, prefer the publisher's actual human-written angle.
    # Generic "What Changed?" packaging is a fallback, not the default.
    if x.get("genre")!="current":
        add_title(original_title)
    if 18 <= len(headline) <= 82:
        add_title(headline)
    elif x.get("genre")=="current":
        add_title(original_title)
    if pretty and x.get("genre")!="current":
        add_title(f"{pretty}: What Changed?")
        add_title(f"Why Is {pretty} Getting Attention?")
        add_title(f"What Changed With {pretty}?")

    hooks=[]
    def add_hook(value):
        value=" ".join(str(value or "").split()).strip()
        if 3 <= len(value) <= 52 and value.lower() not in {h.lower() for h in hooks}:
            hooks.append(value)
    add_hook(original_hook)
    if topic and x.get("genre")!="current":
        add_hook("WHAT CHANGED?")
        add_hook("WHY NOW?")
        add_hook(pretty.upper()[:52])
    elif topic:
        # Current stories should lead with the subject, not a reusable template phrase.
        add_hook(pretty.upper()[:52])

    if not titles:
        titles=[original_title or "RAYVAN Story"]
    if not hooks:
        hooks=[original_hook or "WHAT CHANGED?"]

    options=[]
    for title in titles[:5]:
        for hook in hooks[:4]:
            candidate=dict(x,title=title+" #Shorts",hook=hook)
            p=packaging_score(candidate)
            s=story_score(candidate)
            # Packaging leads, but the winner must still promise a real payoff.
            score=.70*p + .30*s
            # Penalize the exact generic packaging pattern that produced lame,
            # interchangeable trend Shorts.
            if x.get("genre")=="current" and re.search(r"(?i)what changed|getting attention|why now",title+" "+hook):
                score-=24
            options.append({"title":candidate["title"][:100],"hook":hook,"score":round(score,2)})
    options.sort(key=lambda row: row["score"], reverse=True)
    winner=options[0]
    x["title"]=winner["title"]
    x["hook"]=winner["hook"]
    x["packaging_winner_score"]=winner["score"]
    x["packaging_candidates"]=options[:6]
    return x

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
    policy=(data or {}).get("optimization_policy") or {}
    pw=policy.get("packaging_weight",.10); sw=policy.get("story_weight",.10)
    ranked=[]
    for c in candidates:
        x=dict(c)
        raw=genre_scores.get(c.get("genre"))
        # Analytics scores are not naturally 0-100; gently normalize when present.
        channel=None if raw is None else _clip(50 + 12*math.log1p(max(0,float(raw))))
        x["prior_score"]=score_candidate(x, channel_score=channel, packaging_weight=pw, story_weight=sw)
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
