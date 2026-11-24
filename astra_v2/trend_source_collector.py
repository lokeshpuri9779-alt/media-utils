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
    if direction not in {"current_news", "trending_topics"}:
        raise ValueError("Unsupported sourced direction")
    if direction == "current_news":
        sources = _parse_feed(NEWS_URL, 12)
    else:
        trends = _parse_feed(TRENDS_URL, 12)
        sources = list(trends)
        for trend in trends[:5]:
            query = urllib.parse.urlencode({"q": trend["title"], "hl": "en-IN", "gl": "IN", "ceid": "IN:en"})
            url = "https://news.google.com/rss/search?" + query
            try:
                sources.extend(_parse_feed(url, 2))
            except Exception as exc:  # Keep other independently retrieved feeds usable.
                print(f"Skipping one trend news lookup: {type(exc).__name__}")
    # Deduplicate by canonical feed URL while preserving order.
    unique = []
    seen = set()
    for item in sources:
        if item["url"] not in seen:
            seen.add(item["url"])
            unique.append(item)
    if len(unique) < 2:
        raise RuntimeError("RSS collection returned fewer than two usable sources")
    payload = {
        "direction": direction,
        "region": "IN",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "sources": unique[:20],
        "warning": "RSS headlines are leads, not independently verified facts. Human review required.",
    }
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload["sources"], indent=2, ensure_ascii=False) + "\\n", encoding="utf-8")
    print(json.dumps({"direction": direction, "source_count": len(payload["sources"]),
                      "retrieved_at": payload["retrieved_at"]}, indent=2))
    return payload["sources"]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--direction", choices=["current_news", "trending_topics"], required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    collect(args.direction, args.output)


if __name__ == "__main__":
    main()
