"""Fetch a small public RSS evidence pack for ASTRA current/trending Shorts.

No API key or paid service. RSS items are leads, not proof; generated scripts remain
review-only and must retain their source metadata for human verification.
"""
from __future__ import annotations

import argparse
import json
from html.parser import HTMLParser
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

NEWS_URL = "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en"
TRENDS_URL = "https://trends.google.com/trending/rss?geo=IN"
BING_NEWS_URL = "https://www.bing.com/news/search"
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
        if child.tag.rsplit("}", 1)[-1].lower() == name.lower():
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
                if child.tag.rsplit("}", 1)[-1].lower() == "link":
                    link = child.attrib.get("href", "")
                    break
        published = _tag(item, "pubDate") or _tag(item, "published") or _tag(item, "updated")
        source_node = next((child for child in item if child.tag.rsplit("}", 1)[-1].lower() == "source"), None)
        source = (source_node.text or "").strip() if source_node is not None else ""
        source_url = source_node.attrib.get("url", "") if source_node is not None else ""
        publisher_domain = urllib.parse.urlsplit(source_url).hostname or ""
        publisher_domain = publisher_domain.lower().removeprefix("www.")
        description = (_tag(item, "description") or _tag(item, "summary")
                       or _tag(item, "encoded"))
        try:
            dt = parsedate_to_datetime(published)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            published_iso = dt.astimezone(timezone.utc).isoformat()
        except (TypeError, ValueError, OverflowError):
            published_iso = published
        if link.startswith("https://www.bing.com/news/apiclick.aspx"):
            destination = urllib.parse.parse_qs(urllib.parse.urlsplit(link).query).get("url", [])
            if destination and destination[0].startswith(("https://", "http://")):
                link = destination[0]
        if title and link:
            rows.append({
                "title": title,
                "url": link,
                "published": published_iso,
                "publisher": source or "RSS feed",
                "publisher_domain": publisher_domain,
                "summary": description[:500],
            })
        if len(rows) >= limit:
            break
    return rows




class _ArticleText(HTMLParser):
    """Extract publisher-provided descriptions and readable article paragraphs."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.meta = []
        self.paragraphs = []
        self._paragraph = []
        self._in_paragraph = False
        self._blocked = 0

    def handle_starttag(self, tag, attrs):
        attrs = {str(k).lower(): str(v or "") for k, v in attrs}
        if tag in {"script", "style", "noscript", "svg", "nav", "footer", "header"}:
            self._blocked += 1
        if tag == "meta":
            key = (attrs.get("name") or attrs.get("property") or "").lower()
            if key in {"description", "og:description", "twitter:description"}:
                value = " ".join(attrs.get("content", "").split())
                if value:
                    self.meta.append(value)
        if tag == "p" and not self._blocked:
            self._in_paragraph = True
            self._paragraph = []

    def handle_endtag(self, tag):
        if tag == "p" and self._in_paragraph:
            value = " ".join(" ".join(self._paragraph).split())
            if len(value) >= 55:
                self.paragraphs.append(value)
            self._paragraph = []
            self._in_paragraph = False
        if tag in {"script", "style", "noscript", "svg", "nav", "footer", "header"}:
            self._blocked = max(0, self._blocked - 1)

    def handle_data(self, data):
        if self._in_paragraph and not self._blocked:
            clean = " ".join(str(data or "").split())
            if clean:
                self._paragraph.append(clean)


def _publisher_page_summary(url: str) -> str:
    """Recover source-authored context when RSS supplies headlines only.

    This does not invent or paraphrase facts: it extracts publisher metadata or
    article paragraphs. Unavailable/paywalled pages remain summary-less.
    """
    if not isinstance(url, str) or not url.startswith(("https://", "http://")):
        return ""
    request = urllib.request.Request(url, headers={
        **HEADERS, "Accept": "text/html,application/xhtml+xml"})
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            content_type = str(response.headers.get("Content-Type", "")).lower()
            if "html" not in content_type:
                return ""
            raw = response.read(1_200_000)
        parser = _ArticleText()
        parser.feed(raw.decode("utf-8", errors="replace"))
        # Prefer the publisher's explicit summary; otherwise use a small,
        # ordered excerpt from visible article paragraphs.
        candidates = parser.meta + parser.paragraphs[:3]
        for value in candidates:
            value = " ".join(value.split())
            if len(value) >= 55:
                return value[:500]
    except Exception as exc:
        print(f"Skipping publisher article context: {type(exc).__name__}")
    return ""

def enrich_trends(trends: list[dict], max_topics: int = 4) -> list[dict]:
    """Attach bounded Google News RSS context to live trend items.

    RSS descriptions are source-provided leads, not verified facts. Keep the
    original Google Trends links and merge independent publisher records so
    the long-form renderer can preserve dates, summaries and provenance.
    """
    enriched = []
    for trend in trends or []:
        if not isinstance(trend, dict):
            continue
        item = dict(trend)
        item["news"] = list(item.get("news") or [])
        enriched.append(item)
    for item in enriched[:max(0, min(4, int(max_topics)))]:
        topic = str(item.get("title") or "").strip()
        if not topic:
            continue
        query = urllib.parse.urlencode({
            "q": topic, "hl": "en-IN", "gl": "IN", "ceid": "IN:en"
        })
        fetched = []
        try:
            fetched = _parse_feed("https://news.google.com/rss/search?" + query, 6)
        except Exception as exc:
            print(f"Skipping Google News trend context: {type(exc).__name__}")
        # Google News RSS frequently returns headlines without descriptions or
        # is unavailable to hosted runners. Bing's public RSS search includes
        # publisher snippets; treat those snippets as leads and retain source
        # identity/date/URL rather than inventing narration.
        if not any(len(str(row.get("summary") or "").strip()) >= 55 for row in fetched):
            bing_query = urllib.parse.urlencode({
                "q": topic, "format": "rss", "setmkt": "en-IN", "setlang": "en-IN"
            })
            try:
                bing = _parse_feed(BING_NEWS_URL + "?" + bing_query, 8)
                fetched.extend(row for row in bing if len(str(row.get("summary") or "").strip()) >= 55)
            except Exception as exc:
                print(f"Skipping Bing News trend context: {type(exc).__name__}")
        seen = {str(x.get("url") or "") for x in item["news"] if isinstance(x, dict)}
        for source in fetched:
            if source.get("url") in seen:
                continue
            seen.add(source.get("url"))
            item["news"].append({
                "title": source.get("title", ""),
                "url": source.get("url", ""),
                "source": source.get("publisher", ""),
                "publisher_domain": source.get("publisher_domain", ""),
                "published": source.get("published", ""),
                "summary": source.get("summary", ""),
            })
        # RSS may expose independent headlines but omit descriptions. Recover
        # actual publisher-authored context for at most two articles per topic.
        for source in item["news"][:2]:
            if isinstance(source, dict) and len(str(source.get("summary") or "").strip()) < 55:
                extracted = _publisher_page_summary(str(source.get("url") or ""))
                if extracted:
                    source["summary"] = extracted
    return enriched


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
        normalized_name = "".join(ch.lower() for ch in publisher if ch.isalnum())
        key = item.get("publisher_domain") or normalized_name
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
