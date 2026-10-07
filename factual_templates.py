from __future__ import annotations

"""Reusable premium factual-story templates for Astra.

Templates define editorial structure, not facts. Every instantiated story must
supply a primary source, verified facts, and visual/media evidence before it can
be marked production_ready.
"""

CATEGORY_TEMPLATES = {
    "science": {
        "genre":"science",
        "beats":["reveal","mechanism","evidence","payoff"],
        "visual_roles":["subject","mechanism","source-evidence","scale"],
        "max_seconds":26,
        "requires_primary_source":True,
        "requires_verified_media":True,
    },
    "technology": {
        "genre":"technology",
        "beats":["reveal","how-it-works","evidence","impact","payoff"],
        "visual_roles":["product-or-system","mechanism","source-evidence","comparison","impact"],
        "max_seconds":26,
        "requires_primary_source":True,
        "requires_verified_media":True,
    },
    "history": {
        "genre":"history",
        "beats":["hook","timeline","evidence","turning-point","payoff"],
        "visual_roles":["period-context","timeline","primary-source","map-or-comparison","legacy"],
        "max_seconds":28,
        "requires_primary_source":True,
        "requires_verified_media":True,
    },
    "geography": {
        "genre":"geography",
        "beats":["reveal","location","scale","mechanism","payoff"],
        "visual_roles":["landmark-or-region","map","comparison","mechanism","takeaway"],
        "max_seconds":26,
        "requires_primary_source":True,
        "requires_verified_media":True,
    },
}


def template_for(category: str) -> dict:
    key=str(category or "").strip().lower()
    if key not in CATEGORY_TEMPLATES:
        raise KeyError(f"Unsupported factual category: {key}")
    return dict(CATEGORY_TEMPLATES[key])


def validate_factual_story(story: dict) -> dict:
    failures=[]
    category=str(story.get("factual_category") or story.get("genre") or "").lower()
    if category not in CATEGORY_TEMPLATES:
        failures.append("unsupported-factual-category")
        return {"pass":False,"failures":failures}

    required=("content_id","title","hook","question","answer","source","story_beats")
    for key in required:
        if not story.get(key):
            failures.append(f"missing:{key}")

    facts=[str(x).strip() for x in (story.get("verified_facts") or []) if str(x).strip()]
    if len(facts)<2:
        failures.append("fewer-than-two-verified-facts")

    beats=story.get("story_beats") or []
    if len(beats)<4:
        failures.append("fewer-than-four-story-beats")

    evidence=sum(1 for b in beats if str(b.get("story_beat") or "") in {"evidence","source","primary-source"})
    if evidence<1:
        failures.append("missing-evidence-beat")

    media=sum(1 for b in beats if b.get("media_file") or b.get("media_query"))
    if media<2:
        failures.append("insufficient-visual-evidence")

    return {
        "pass":not failures,
        "category":category,
        "verified_fact_count":len(facts),
        "beat_count":len(beats),
        "media_beats":media,
        "failures":failures,
    }
