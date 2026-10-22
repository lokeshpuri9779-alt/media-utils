"""Fail-closed lane check for a manually pinned reviewed-art story."""
import hashlib


def validate_pinned_story_lane(content_id, lane, lane_count):
    if not isinstance(content_id, str) or not content_id:
        raise ValueError("reviewed_art_content_id_required")
    try:
        lane = int(lane)
        lane_count = int(lane_count)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid_reviewed_art_lane") from exc
    if lane_count < 1 or not 0 <= lane < lane_count:
        raise ValueError("invalid_reviewed_art_lane")
    expected = int(hashlib.sha256(content_id.encode("utf-8")).hexdigest(), 16) % lane_count
    return expected == lane
