"""Mirror the existing creative lane assignment for reviewed-art preflight."""
import hashlib


def story_lane(story, lane_count):
    if not isinstance(story, dict) or not isinstance(story.get("content_id"), str):
        raise ValueError("invalid_reviewed_art_story")
    lane_count = int(lane_count)
    if lane_count < 1:
        raise ValueError("invalid_reviewed_art_lane_count")
    if story.get("series_id"):
        episode = int(story["episode"])
        if episode < 1:
            raise ValueError("invalid_reviewed_art_episode")
        return (episode - 1) % lane_count
    digest = hashlib.sha256(story["content_id"].encode()).digest()
    return int.from_bytes(digest[:8], "big") % lane_count


def validate_pinned_story_lane(story, lane, lane_count):
    lane = int(lane)
    lane_count = int(lane_count)
    if not 0 <= lane < lane_count:
        raise ValueError("invalid_reviewed_art_lane")
    return story_lane(story, lane_count) == lane
