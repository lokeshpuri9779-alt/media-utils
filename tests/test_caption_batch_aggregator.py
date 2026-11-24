import json
import tempfile
import unittest
from pathlib import Path

from astra_v2.caption_batch_aggregator import aggregate_batch, validate_rendered_package, main
from astra_v2.github_local_story_generator import ROLES, _fingerprint


def write_package(root: Path, name: str, premise: str = (
    "A student investigating an abandoned observatory discovers that its telescope is flashing "
    "without electricity. Old star charts reveal the flashes track an approaching asteroid, "
    "not distant stars. She restores the forgotten warning system and gives the village time "
    "to prepare before impact."
)) -> Path:
    folder = root / name
    folder.mkdir(parents=True)
    fingerprint = _fingerprint(premise)
    lines = [
        "The observatory flashed once despite having no electricity.",
        "Its caretaker vanished decades earlier, leaving the telescope locked.",
        "A student noticed flashes matched stars missing from tonight's sky.",
        "She compared old charts and found one star had shifted.",
        "The telescope was tracking an asteroid approaching the village.",
        "Its warning system could alert residents hours before an impact.",
        "She restored the signal, giving the town time to prepare.",
    ]
    question = "Would you have understood the signal before the final flash?"
    candidate = {
        "content_id": "rayvan-" + fingerprint[:20],
        "content_type": "mystery",
        "title": "The Observatory Signal",
        "premise": premise,
        "premise_fingerprint": fingerprint,
        "question": question,
        "performance_scenes": [
            {"role": role, "speech": speech} for role, speech in zip(ROLES, lines)
        ],
        "word_count": sum(len(line.split()) for line in lines) + len(question.split()),
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
            "resolution": "1080x1920",
            "caption_count": 1,
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

    def test_review_package_rejects_tampered_premise_fingerprint(self):
        with tempfile.TemporaryDirectory() as temp:
            candidate_path = write_package(Path(temp), "lane-one")
            candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
            candidate["premise_fingerprint"] = "tampered"
            candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "fingerprint does not match"):
                validate_rendered_package(candidate_path)

    def test_review_package_requires_matching_candidate_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            candidate_path = write_package(Path(temp), "lane-one")
            review_path = candidate_path.with_name("rayvan-short.review.json")
            review = json.loads(review_path.read_text(encoding="utf-8"))
            review["candidate_id"] = "different-candidate"
            review_path.write_text(json.dumps(review), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "candidate ID"):
                validate_rendered_package(candidate_path)

    def test_review_package_rejects_invalid_caption_timing(self):
        with tempfile.TemporaryDirectory() as temp:
            candidate_path = write_package(Path(temp), "lane-one")
            captions_path = candidate_path.with_name("rayvan-short.captions.json")
            captions = json.loads(captions_path.read_text(encoding="utf-8"))
            captions["captions"][0]["start"] = 2.0
            captions["captions"][0]["end"] = 1.0
            captions_path.write_text(json.dumps(captions), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "out-of-order timing"):
                validate_rendered_package(candidate_path)

    def test_cli_entrypoint_executes_aggregation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            batch = root / "batch"
            write_package(batch, "lane-one")
            history = root / "history.jsonl"
            main([
                "--history", str(history),
                "--batch-dir", str(batch),
                "--run-id", "456",
                "--batch-result", "success",
            ])
            report = json.loads((batch / "batch-report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["run_id"], "456")
            self.assertEqual(report["new_history_records"], 1)

    def test_review_package_rejects_wrong_portrait_resolution(self):
        with tempfile.TemporaryDirectory() as temp:
            candidate_path = write_package(Path(temp), "lane-one")
            review_path = candidate_path.with_name("rayvan-short.review.json")
            review = json.loads(review_path.read_text(encoding="utf-8"))
            review["render"]["resolution"] = "1920x1080"
            review_path.write_text(json.dumps(review), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "1080x1920"):
                validate_rendered_package(candidate_path)

    def test_review_package_rejects_caption_count_mismatch(self):
        with tempfile.TemporaryDirectory() as temp:
            candidate_path = write_package(Path(temp), "lane-one")
            review_path = candidate_path.with_name("rayvan-short.review.json")
            review = json.loads(review_path.read_text(encoding="utf-8"))
            review["render"]["caption_count"] = 2
            review_path.write_text(json.dumps(review), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "counts do not match"):
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
