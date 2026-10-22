"""Select artwork only for already-approved, history-eligible stories in a lane.

An art index is transport metadata, never a source of editorial approval.
"""
import json
import re

from astra_v2.adaptive_artifact_store import validate_record
from astra_v2.reviewed_art_lane import validate_pinned_story_lane
from astra_v2.reviewed_art_receipt_index import INDEX_SCHEMA, _validate_receipt


def select_eligible_art_story(index_receipt, store, eligible_stories, lane, lane_count):
    if (not isinstance(index_receipt, dict)
            or index_receipt.get("schema") != INDEX_SCHEMA
            or index_receipt.get("publication_triggered") is not False):
        raise ValueError("invalid_art_index_receipt")
    validate_record(index_receipt.get("index"), 256 * 1024)
    payload = store.verify(index_receipt["index"])
    if payload.stat().st_size > 256 * 1024:
        raise ValueError("art_index_too_large")
    data = json.loads(payload.read_text(encoding="utf-8"))
    entries = data.get("entries")
    if data.get("schema") != INDEX_SCHEMA or not isinstance(entries, dict) or len(entries) > 500:
        raise ValueError("invalid_art_index")
    for content_id, receipt in entries.items():
        if not isinstance(content_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,200}", content_id):
            raise ValueError("invalid_art_content_id")
        _validate_receipt(receipt)
    if not isinstance(eligible_stories, list):
        raise ValueError("eligible_art_stories_required")
    for story in eligible_stories:
        if not isinstance(story, dict):
            raise ValueError("invalid_eligible_art_story")
        content_id = story.get("content_id")
        if (content_id in entries
                and (story.get("production_ready") or story.get("validation_candidate"))
                and validate_pinned_story_lane(story, lane, lane_count)):
            return content_id
    return None
