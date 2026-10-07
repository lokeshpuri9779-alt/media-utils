from __future__ import annotations

import re
import json
import os


ENGINE_VERSION = "creative-engine-7.1-omniroute"

_STOP = {
    "the","a","an","and","or","of","to","in","on","for","with","from","at","by",
    "is","are","was","were","be","this","that","new","latest","update","news"
}
_GENERIC = re.compile(r"\b(what changed|why now|getting attention|fresh wave of search interest|subscribe for more)\b", re.I)

def _letters(text: str):
    return [c for c in str(text or "") if c.isalpha()]

def english_script_ratio(text: str) -> float:
    letters=_letters(text)
    if not letters:
        return 0.0
    latin=sum(("A" <= c <= "Z") or ("a" <= c <= "z") for c in letters)
    return latin/len(letters)

def _tokens(text: str) -> set[str]:
    return {x for x in re.findall(r"[a-z0-9]+", str(text or "").lower())
            if len(x) > 2 and x not in _STOP}

def topic_headline_alignment(topic: str, headline: str) -> float:
    t=_tokens(topic); h=_tokens(headline)
    if not t or not h:
        return 0.0
    return len(t & h)/len(t)

def _aligned_english_reports(c: dict) -> list[dict]:
    topic=str(c.get("topic") or "")
    reports=[]
    for match in c.get("trend_matches") or []:
        for item in match.get("news") or []:
            headline=" ".join(str(item.get("title") or "").split())
            if not headline or english_script_ratio(headline) < .92:
                continue
            if topic_headline_alignment(topic, headline) < .50:
                continue
            reports.append(item)
    return reports


def omniroute_enrich(c: dict) -> tuple[dict, dict]:
    """Optional quality-first intelligence pass.

    Fail-open to the existing deterministic Creative Engine: an unavailable
    gateway must never destroy a candidate or silently lower the release bar.
    """
    if str(os.getenv("ASTRA_OMNIROUTE_ENABLED", "1")).lower() in {"0","false","no"}:
        return dict(c), {"used": False, "reason": "disabled"}
    try:
        from omniroute_adapter import creative
        prompt = """Improve this Astra production candidate as a senior short-form creative director.
Return ONLY a JSON object. Preserve factual claims unless evidence is supplied.
Strengthen hook, coherent story causality, payoff, audiovisual continuity and originality.
Do not optimize for scene count. Do not add a generic CTA.
Allowed keys: title, hook, question, answer, creative_notes.
Candidate:
""" + json.dumps(c, ensure_ascii=False, default=str)
        raw=creative(prompt)
        data=json.loads(raw)
        x=dict(c)
        for key in ("title","hook","question","answer","creative_notes"):
            if key in data and data[key]:
                x[key]=data[key]
        x["omniroute_enriched"]=True
        return x, {"used": True, "pass": True}
    except Exception as exc:
        return dict(c), {"used": False, "pass": False, "reason": type(exc).__name__}

def creative_rebuild(c: dict) -> tuple[dict, dict]:
    """Convert a candidate into a viewer-first production brief.

    The engine deliberately rejects ideas that the current zero-cost pipeline cannot
    turn into a credible Short. Capacity is not a publication obligation.
    """
    x, omni_report=omniroute_enrich(c)
    genre=str(x.get("genre") or "")
    reasons=[]
    hard=[]
    if genre == "current":
        if not x.get("source"):
            hard.append("current story missing primary source")
    else:
        if not x.get("premium_story"):
            hard.append("legacy template disabled during creative-engine rebuild")
        elif not x.get("production_ready"):
            hard.append("premium story is awaiting visual curation")

    text=" ".join(str(x.get(k) or "") for k in ("title","hook","question","answer"))
    if genre != "fiction" and english_script_ratio(text) < .90:
        hard.append("spoken package is not reliably global-English")
    if _GENERIC.search(text):
        hard.append("generic trend/template language")
    hook_words=len(str(x.get("hook") or "").split())
    if hook_words > 10:
        reasons.append("opening hook is wordy")
    if len(str(x.get("answer") or "").split()) < 6:
        hard.append("payoff is too thin")

    if genre == "current":
        headline=" ".join(str(x.get("news_title") or "").split())
        topic=" ".join(str(x.get("topic") or "").split())
        if english_script_ratio(headline) < .92:
            hard.append("source-language mismatch for the global-English channel")
        if topic_headline_alignment(topic, headline) < .50:
            hard.append("trend subject is not the actual source story")
        aligned=_aligned_english_reports(x)
        if len(aligned) < 2:
            hard.append("current story lacks two aligned English reports")
        # Headlines/search metadata are discovery signals, not enough material for
        # a premium news explainer. A future research stage can populate these.
        facts=[str(v).strip() for v in (x.get("research_facts") or []) if str(v).strip()]
        if len(facts) < 2:
            hard.append("metadata-only current story: no researched fact set")
        x["aligned_reports"]=aligned[:3]

    duration_max={"tech":20,"football":22,"space":27,"fiction":32,"current":28}.get(genre,26)
    x.update(
        creative_engine_version=ENGINE_VERSION,
        language="en",
        target_duration_max=duration_max,
        target_duration_min=8,
        voice_profile="af_heart",
        cta_mode="none",
        creative_brief={
            "first_second":"show the subject or payoff immediately; no logo intro",
            "narration":"short natural sentences; one idea per sentence; no search-trend narration",
            "captions":"phrase captions only; never duplicate the whole screen with text",
            "visuals":"subject-first; evidence or useful animation; no decorative pseudo-CGI labels",
            "audio":"voice dominant; subtle music; sparse effects",
            "ending":"finish on the payoff, not a generic subscribe card",
        },
    )
    score=100
    score-=25*len(hard)
    score-=8*len(reasons)
    report={"version":ENGINE_VERSION,"score":max(0,score),"pass":not hard and score>=76,
            "hard_failures":hard,"notes":reasons,"omniroute":omni_report}
    x["creative_engine_report"]=report
    return x, report
