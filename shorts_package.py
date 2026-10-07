from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ShortsPackage:
    title: str
    description: str
    tags: list[str]
    attribution: list[str]
    privacy_status: str
    thumbnail_scene_index: int


def build_shorts_package(story: dict, render_report: dict | None = None) -> ShortsPackage:
    title=str(story.get("title") or story.get("hook") or "RAYVAN Short").strip()
    hook=str(story.get("hook") or "").strip()
    source=str(story.get("source") or "").strip()
    keywords=[str(x).strip() for x in (story.get("keywords") or []) if str(x).strip()]

    attribution=[]
    if source:
        attribution.append(source)

    description_parts=[]
    if hook:
        description_parts.append(hook)
    description_parts.append("Source-backed short from RAYVAN.")
    if attribution:
        description_parts.append("Source: " + attribution[0])
    description="\n\n".join(description_parts)

    scenes=(render_report or {}).get("scenes") or []
    # Prefer payoff/reveal frames over mechanism frames for thumbnail candidates.
    preferred=None
    for s in scenes:
        if str(s.get("story_beat") or "") in {"payoff","reveal"}:
            preferred=int(s.get("index") or 0)
            if str(s.get("story_beat") or "")=="payoff":
                break
    if preferred is None:
        preferred=max(0,len(scenes)-1) if scenes else 0

    tags=list(dict.fromkeys(keywords + ["RAYVAN","shorts"]))

    return ShortsPackage(
        title=title[:100],
        description=description,
        tags=tags[:15],
        attribution=attribution,
        privacy_status="private",
        thumbnail_scene_index=preferred,
    )


def as_dict(pkg: ShortsPackage) -> dict:
    return {
        "title":pkg.title,
        "description":pkg.description,
        "tags":pkg.tags,
        "attribution":pkg.attribution,
        "privacy_status":pkg.privacy_status,
        "thumbnail_scene_index":pkg.thumbnail_scene_index,
    }
