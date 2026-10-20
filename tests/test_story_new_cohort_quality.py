import json
import tempfile
from pathlib import Path
from astra_v2.story_new_cohort_quality import build


def test_new_cohort_excludes_historical_issues():
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        ledger = root / "ledger.json"
        review = root / "review.json"
        before = root / "before.json"
        output = root / "report.json"
        ledger.write_text(json.dumps({"proposals": [
            {"content_id": "old", "production_ready": False},
            {"content_id": "new", "production_ready": False},
        ]}))
        review.write_text(json.dumps({"proposals": [
            {"content_id": "old", "editorial_issues": ["narrative_duplicate"]},
            {"content_id": "new", "editorial_issues": ["insufficient_visual_variety"]},
        ]}))
        before.write_text(json.dumps(["old"]))
        result = build(ledger, review, before, output)
        assert result["new_proposals"] == 1
        assert result["new_editorial_reason_counts"] == {"insufficient_visual_variety": 1}
        assert result["approved_for_production"] == 0
        assert json.loads(output.read_text()) == result
