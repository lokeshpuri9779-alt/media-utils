"""Read-only story supply audit for the experimental pipeline.

No publication, render, or production-state mutation occurs here.
"""
from collections import Counter
from experimental.story_draft_bank import draft_bank
from experimental.story_development import development_batch
from astra_v2.publication_quality import publication_rejection

def audit():
    drafts=draft_bank()
    outlines=development_batch()
    reasons=Counter(publication_rejection(x) or "eligible" for x in outlines)
    repeated_speeches=Counter(
        tuple(beat["speech"] for beat in item["story_beats"]) for item in outlines
    )
    return {
        "draft_count":len(drafts),
        "outline_count":len(outlines),
        "unique_titles":len({x["title"] for x in drafts}),
        "unique_ids":len({x["content_id"] for x in outlines}),
        "publication_rejections":dict(reasons),
        "identical_four_beat_scripts":sum(n-1 for n in repeated_speeches.values() if n>1),
        "approved_for_publication":reasons.get("eligible",0),
        "assessment":"premise bank only; full original scripts and audiovisual QA required",
    }

if __name__=="__main__":
    import json
    print(json.dumps(audit(),indent=2,sort_keys=True))
