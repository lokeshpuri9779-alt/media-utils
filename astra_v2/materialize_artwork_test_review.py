"""Materialize owner-authorized artwork-test review with exact story digest.

Approval is limited to staging images; this script never queues publication.
"""
import json
from pathlib import Path
from astra_v2.editorial_approval_manifest import story_digest

SOURCE = Path("editorial/artwork_test/reviewed_story.json")
OUTPUT = Path("runtime-artwork-test-editorial")

def materialize():
    story = json.loads(SOURCE.read_text(encoding="utf-8"))
    if (story.get("content_id") != "astra-candidate-lantern-beneath-ice-20261023"
            or story.get("status") != "approved_for_artwork_validation"
            or story.get("artwork_approval") != "owner_approved_for_artwork_testing_only"
            or story.get("production_ready") is not True):
        raise ValueError("artwork_test_owner_approval_not_valid")
    OUTPUT.mkdir(exist_ok=True)
    (OUTPUT / "stories.json").write_text(json.dumps({"stories": [story]}, indent=2) + "\n")
    record = {"content_id": story["content_id"], "story_sha256": story_digest(story),
              "decision": "approve", "reviewer": "Project owner (explicit chat approval, 2026-10-23)",
              "review_notes": "Approval only for Gemini artwork staging and visual review. No publication authorization; full historical novelty and downstream QA required."}
    (OUTPUT / "decisions.json").write_text(json.dumps({"reviews": [record]}, indent=2) + "\n")
    print("ASTRA_ARTWORK_TEST_REVIEW_MATERIALIZED=" + story["content_id"])

if __name__ == "__main__":
    materialize()
