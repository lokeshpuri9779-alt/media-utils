import json
import tempfile
import unittest
from pathlib import Path

from astra_v2.caption_batch_aggregator import aggregate_batch, validate_rendered_package


def write_package(root: Path, name: str, premise: str = "A distinct mystery premise with a hidden observatory and a careful investigator.") -> Path:
    folder = root / name
    folder.mkdir(parents=True)
    candidate = {
        "content_id": "rayvan-" + name,
        "content_type": "mystery",
        "title": "The Observatory Signal",
        "premise": premise,
        "premise_fingerprint": name,
        "approved": False,
        "production_ready": False,
        "published": False,
    }
    candidate_path = folder / "candidate.json"
    candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
    (folder / "rayvan-short.mp4").write_bytes(b"0" * 2048)
    review = {
        "candidate_id": candidate["content_id"],
        "approved": False,
        "production_ready": False,
        "published": False,
        "render": {
            "output": f"output/{name}/rayvan-short.mp4",
            "duration_seconds": 33.0,
            "quality_check": "passed",
            "published": False,
        },
    }
    (folder / "rayvan-short.review.json").write_text(json.dumps(review), encoding="utf-8")
    captions = {
        "schema_version": 1,
        "fps": 30,
        "duration_seconds": 33.0,
        "captions": [{"caption": "A caption", "start": 0.0, "end": 1.0}],
    }
    (folder / "rayvan-short.captions.json").write_text(json.dumps(captions), encoding="utf-8")
    return candidate_path


class CaptionBatchAggregatorTests(unittest.TestCase):
    def test_only_complete_reviewed_mp4_packages_enter_history(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            batch = root / "batch-output"
            valid = write_package(batch, "lane-one")
            broken = write_package(batch, "lane-two")
            (broken.parent / "rayvan-short.mp4").unlink()
            history = root / "history.jsonl"

            report = aggregate_batch(history, batch, 123, "failure")

            self.assertEqual(report["candidate_files_found"], 2)
            self.assertEqual(report["rendered_packages_verified"], 1)
            self.assertEqual(report["new_history_records"], 1)
            self.assertEqual(len(report["rejected_packages"]), 1)
            self.assertEqual(len(history.read_text(encoding="utf-8").splitlines()), 1)
            self.assertTrue((batch / "batch-report.json").is_file())

    def test_review_package_requires_matching_candidate_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            candidate_path = write_package(Path(temp), "lane-one")
            review_path = candidate_path.with_name("rayvan-short.review.json")
            review = json.loads(review_path.read_text(encoding="utf-8"))
            review["candidate_id"] = "different-candidate"
            review_path.write_text(json.dumps(review), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "candidate ID"):
                validate_rendered_package(candidate_path)

    def test_review_package_rejects_caption_duration_mismatch(self):
        with tempfile.TemporaryDirectory() as temp:
            candidate_path = write_package(Path(temp), "lane-one")
            captions_path = candidate_path.with_name("rayvan-short.captions.json")
            captions = json.loads(captions_path.read_text(encoding="utf-8"))
            captions["duration_seconds"] = 36.0
            captions_path.write_text(json.dumps(captions), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "durations do not match"):
                validate_rendered_package(candidate_path)


if __name__ == "__main__":
    unittest.main()
