"""Restore a pinned remote reviewed-art receipt for the preload worker.

Explicit opt-in only. Never interprets remote storage as editorial approval.
"""
import json
import os
from pathlib import Path

from astra_v2.remote_reviewed_art import restore


def restore_for_preload(*, environ=None, store=None):
    env = os.environ if environ is None else environ
    receipt_file = env.get("ASTRA_REVIEWED_ART_RECEIPT_FILE", "").strip()
    index_file = env.get("ASTRA_REVIEWED_ART_INDEX_RECEIPT_FILE", "").strip()
    if receipt_file and index_file:
        raise ValueError("conflicting_art_receipt_sources")
    if not receipt_file and not index_file:
        return None
    if env.get("ASTRA_PRELOAD_REVIEWED_ART_MANIFEST"):
        raise ValueError("conflicting_reviewed_art_sources")
    receipt_path = Path(receipt_file or index_file)
    if receipt_path.is_symlink() or not receipt_path.is_file() or receipt_path.stat().st_size > 4096:
        raise ValueError("invalid_reviewed_art_receipt_file")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if store is None:
        from astra_v2.adaptive_remote_store import store_from_environment
        store = store_from_environment(env.get("ASTRA_ARTIFACT_CACHE", "storage/artifacts"))
    if index_file:
        from astra_v2.reviewed_art_receipt_index import lookup
        story_id = env.get("ASTRA_REVIEWED_ART_CONTENT_ID", "").strip()
        if not story_id and env.get("ASTRA_REVIEWED_ART_AUTO_SELECT") == "1":
            # Use the same hash-bound editorial intake as the creative engine.
            # It includes both static and persisted AI-reviewed approval pairs,
            # while enforcing the complete publisher/story history.
            from astra_v2.editorial_creative_source import load_editorial_stories
            from astra_v2.reviewed_art_eligible_selection import select_eligible_art_story
            eligible = load_editorial_stories()
            story_id = select_eligible_art_story(
                receipt, store, eligible, env.get("ASTRA_PRELOAD_LANE", "0"),
                env.get("ASTRA_PRELOAD_LANES", "1"))
            if not story_id:
                raise ValueError("no_eligible_reviewed_art_story_in_lane")
            env["ASTRA_REVIEWED_ART_CONTENT_ID"] = story_id
            os.environ["ASTRA_REVIEWED_ART_CONTENT_ID"] = story_id
        if not story_id:
            raise ValueError("reviewed_art_content_id_required")
        receipt = lookup(receipt, story_id, store)
        if receipt is None:
            raise ValueError("reviewed_art_story_receipt_missing")
    target = Path(env.get("ASTRA_REVIEWED_ART_RESTORE_DIR", "runtime-reviewed-art"))
    manifest = restore(receipt, store, target)
    os.environ["ASTRA_PRELOAD_REVIEWED_ART_MANIFEST"] = str(manifest.resolve())
    print("ASTRA_REVIEWED_ART_RESTORED=" + json.dumps({
        "manifest": str(manifest), "publishing_triggered": False}, sort_keys=True))
    return manifest
