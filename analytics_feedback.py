from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json
from typing import Iterable


@dataclass
class VideoMetrics:
    content_id: str
    views: int = 0
    likes: int = 0
    comments: int = 0
    avg_view_duration: float = 0.0
    avg_percentage_viewed: float = 0.0
    impressions: int = 0
    ctr: float = 0.0


def normalize_metric_row(row: dict) -> VideoMetrics:
    return VideoMetrics(
        content_id=str(row.get("content_id") or row.get("video_id") or "").strip(),
        views=max(0,int(row.get("views") or 0)),
        likes=max(0,int(row.get("likes") or 0)),
        comments=max(0,int(row.get("comments") or 0)),
        avg_view_duration=max(0.0,float(row.get("avg_view_duration") or row.get("averageViewDuration") or 0.0)),
        avg_percentage_viewed=max(0.0,float(row.get("avg_percentage_viewed") or row.get("averageViewPercentage") or 0.0)),
        impressions=max(0,int(row.get("impressions") or 0)),
        ctr=max(0.0,float(row.get("ctr") or row.get("impressionsCtr") or 0.0)),
    )


def performance_score(m: VideoMetrics) -> float:
    # Retention dominates; engagement and packaging act as supporting signals.
    retention=min(100.0,m.avg_percentage_viewed)
    engagement=(m.likes + 2*m.comments) / max(1,m.views) * 100.0
    ctr=min(20.0,m.ctr) * 5.0
    reach=min(100.0,(m.views ** 0.5))
    score=0.55*retention + 0.2*min(100.0,engagement*20.0) + 0.15*ctr + 0.10*reach
    return round(max(0.0,min(100.0,score)),2)


def build_feedback(rows: Iterable[dict]) -> dict:
    metrics=[normalize_metric_row(r) for r in rows]
    scored=[]
    for m in metrics:
        if not m.content_id:
            continue
        scored.append({**asdict(m),"performance_score":performance_score(m)})
    scored.sort(key=lambda x:x["performance_score"],reverse=True)
    return {
        "count":len(scored),
        "ranked":scored,
        "best_content_id":scored[0]["content_id"] if scored else None,
    }


def apply_feedback_to_stories(stories: list[dict], feedback: dict) -> list[dict]:
    by_id={x["content_id"]:x for x in (feedback.get("ranked") or [])}
    out=[]
    for story in stories:
        s=dict(story)
        metrics=by_id.get(str(s.get("content_id") or ""))
        if metrics:
            s["observed_performance_score"]=metrics["performance_score"]
            s["selection_weight"]=round(1.0 + metrics["performance_score"]/100.0,3)
        else:
            s["observed_performance_score"]=None
            s["selection_weight"]=1.0
        out.append(s)
    return out


def save_feedback(path: str | Path, feedback: dict) -> None:
    p=Path(path)
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(feedback,indent=2),encoding="utf-8")
