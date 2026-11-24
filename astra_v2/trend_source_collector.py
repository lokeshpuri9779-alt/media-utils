"""Fetch a small public RSS evidence pack for ASTRA current/trending Shorts.

No API key or paid service. RSS items are leads, not proof; generated scripts remain
review-only and must retain their source metadata for human verification.
"""
from __future__ import annotations

import argparse
import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

NEWS_URL = "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en"
TRENDS_URL = "https://trends.google.com/trending/rss?geo=IN"
HEADERS = {"User-Agent": "ASTRA-RAYVAN-RSS-Reader/1.0 (+https://github.com/lokeshpuri9779-alt/media-utils)"}

TOPIC_QUERIES = {
    "science_explained": "science research discovery physics biology",
    "india_gk": "India history geography constitution culture facts",
    "money_business": "business economics markets companies India",
    "geography_gk": "geography climate earth borders oceans",
    "psychology": "psychology behavioural science research",
    "weird_facts": "verified science history unusual facts",
    "history_gk": "world history archaeology discovery",
    "world_gk": "world knowledge science culture civics",
    "myth_vs_fact": "fact check science history misconceptions",
    "tech_explained": "technology artificial intelligence engineering",
    "space_facts": "astronomy space science discovery",
    "nature_facts": "wildlife ecology nature research",
    "human_body": "human biology medical research health science",
    "inventions": "engineering inventions technology history",
    "mini_case_study": "business case study company innovation",
    "ranked_countdown": "science technology geography rankings data",
    "guess_the_number": "science statistics population geography data",
    "quick_quiz": "verified general knowledge science history geography facts",
    "what_if": "physics climate science engineering evidence research",
    "spot_the_lie": "science history fact check claims",
    "two_truths_one_lie": "science history verified facts",
    "current_news": "",
    "trending_topics": "",
}


def _fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read(2_000_000)


def _tag(element, name: str) -> str:
    for child in element:
        if child.tag.rsplit("}", 1)[-1] == name:
            return (child.text or "").strip()
    return ""


def _parse_feed(url: str, limit: int = 10) -> list[dict]:
    root = ET.fromstring(_fetch(url))
    rows = []
    for item in root.iter():
        if item.tag.rsplit("}", 1)[-1] not in {"item", "entry"}:
            continue
        title = _tag(item, "title")
        link = _tag(item, "link")
        if not link:
            for child in item:
                if child.tag.rsplit("}", 1)[-1] == "link":
                    link = child.attrib.get("href", "")
                    break
        published = _tag(item, "pubDate") or _tag(item, "published") or _tag(item, "updated")
        source = _tag(item, "source")
        description = _tag(item, "description") or _tag(item, "summary")
        try:
            dt = parsedate_to_datetime(published)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            published_iso = dt.astimezone(timezone.utc).isoformat()
        except (TypeError, ValueError, OverflowError):
            published_iso = published
        if title and link:
            rows.append({
                "title": title,
                "url": link,
                "published": published_iso,
                "publisher": source or "RSS feed",
                "summary": description[:500],
            })
        if len(rows) >= limit:
            break
    return rows


def collect(direction: str, output: str) -> list[dict]:
    if direction not in TOPIC_QUERIES:
        raise ValueError("Unsupported sourced direction")
    if direction == "current_news":
        sources = _parse_feed(NEWS_URL, 20)
    elif direction == "trending_topics":
        trends = _parse_feed(TRENDS_URL, 12)
        sources = list(trends)
        queries = [trend["title"] for trend in trends[:5]]
        for query_text in queries:
            query = urllib.parse.urlencode({"q": query_text, "hl": "en-IN", "gl": "IN", "ceid": "IN:en"})
            url = "https://news.google.com/rss/search?" + query
            try:
                sources.extend(_parse_feed(url, 4))
            except Exception as exc:  # Keep other independently retrieved feeds usable.
                print(f"Skipping one trend news lookup: {type(exc).__name__}")
    else:
        query = urllib.parse.urlencode({
            "q": TOPIC_QUERIES[direction], "hl": "en-IN", "gl": "IN", "ceid": "IN:en"
        })
        sources = _parse_feed("https://news.google.com/rss/search?" + query, 20)
    # Deduplicate by canonical feed URL while preserving order.
    unique = []
    seen = set()
    for item in sources:
        if item["url"] not in seen:
            seen.add(item["url"])
            unique.append(item)
    # Require distinct named publishers, not two URLs from one publisher or the
    # generic RSS-feed placeholder. The generator applies the full metadata gate.
    independent = []
    seen_publishers = set()
    for item in unique:
        publisher = str(item.get("publisher") or "").strip()
        key = "".join(ch.lower() for ch in publisher if ch.isalnum())
        if not key or key in {"rssfeed", "googletrends"} or key in seen_publishers:
            continue
        seen_publishers.add(key)
        independent.append(item)
    if len(independent) < 2:
        raise RuntimeError("RSS collection returned fewer than two distinct named publishers")
    unique = independent
    payload = {
        "direction": direction,
        "region": "IN",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "sources": unique[:20],
        "warning": "RSS headlines are leads, not independently verified facts. Human review required.",
    }
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload["sources"], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"direction": direction, "source_count": len(payload["sources"]),
                      "retrieved_at": payload["retrieved_at"]}, indent=2))
    return payload["sources"]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--direction", choices=sorted(TOPIC_QUERIES), required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    collect(args.direction, args.output)


if __name__ == "__main__":
    main()
