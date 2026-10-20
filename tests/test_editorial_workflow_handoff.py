"""Exercise the editorial files configured on the actual Shorts render steps."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from astra_v2.creative import CreativeSkip
from astra_v2.editorial_creative_source import load_editorial_stories
from astra_v2.editorial_review_packet import export_packet
from astra_v2.production_story_gate import candidate_issues
from astra_v2.story_forge import catalog


WORKFLOWS = (
    (".github/workflows/astra-v2-publish.yml", "publish", "publish_video"),
    (".github/workflows/astra-v2-preload.yml", "preload", "render"),
)
REQUIRED = {
    "ASTRA_EDITORIAL_STORIES_FILE": "editorial/reviewed_stories.json",
    "ASTRA_EDITORIAL_REVIEWS_FILE": "editorial/reviewed_decisions.json",
    "ASTRA_PUBLISHER_STATE_PATH": "astra_v2_state.json",
    "ASTRA_STORY_HISTORY_PATH": "astra_story_history.json",
}


def workflow_environments():
    for filename, job_name, step_id in WORKFLOWS:
        document = yaml.safe_load(Path(filename).read_text(encoding="utf-8"))
        job = document["jobs"][job_name]
        steps = [step for step in job["steps"] if step.get("id") == step_id]
        if len(steps) != 1:
            raise ValueError("Expected one production render step: " + filename)
        env = {**job.get("env", {}), **steps[0].get("env", {})}
        yield filename, {key: env[key] for key in REQUIRED}


class EditorialWorkflowHandoffTests(unittest.TestCase):
    def test_workflows_use_the_checked_in_review_pair(self):
        for filename, env in workflow_environments():
            with self.subTest(workflow=filename):
                self.assertEqual(env, REQUIRED)
                source = json.loads(Path(env["ASTRA_EDITORIAL_STORIES_FILE"]).read_text())
                decisions = json.loads(Path(env["ASTRA_EDITORIAL_REVIEWS_FILE"]).read_text())
                self.assertIsInstance(source["stories"], list)
                self.assertIsInstance(decisions["reviews"], list)

    def test_configured_paths_accept_only_content_bound_authored_approvals(self):
        story = next((s for s in catalog(limit=128) if not candidate_issues(s)), None)
        self.assertIsNotNone(story, "A passing authored fixture is required; do not skip intake validation")
        for filename, configured in workflow_environments():
            with self.subTest(workflow=filename), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                env = {key: str(root / value) for key, value in configured.items()}
                stories = Path(env["ASTRA_EDITORIAL_STORIES_FILE"])
                reviews = Path(env["ASTRA_EDITORIAL_REVIEWS_FILE"])
                state = Path(env["ASTRA_PUBLISHER_STATE_PATH"])
                history = Path(env["ASTRA_STORY_HISTORY_PATH"])
                state.write_text('{"published":{},"pending":{},"reserved":{},"rejected":{}}')
                history.write_text('{"stories":[]}')
                export_packet([story], root / "packet.json", stories, reviews)
                with patch.dict(os.environ, env):
                    self.assertEqual(load_editorial_stories(), [])
                    decisions = json.loads(reviews.read_text())
                    decisions["reviews"][0].update(
                        decision="approve", reviewer="ci-fixture",
                        review_notes="Synthetic workflow test only; no production decision")
                    reviews.write_text(json.dumps(decisions))
                    self.assertEqual(load_editorial_stories(), [story])
                    changed = dict(story, title=story["title"] + " changed")
                    stories.write_text(json.dumps({"stories": [changed]}))
                    self.assertEqual(load_editorial_stories(), [])
                    stories.write_text(json.dumps({"stories": [story]}))
                    history.write_text(json.dumps({"stories": [
                        {"content_id": "prior", "plot_fingerprint": story["plot_fingerprint"]}
                    ]}))
                    self.assertEqual(load_editorial_stories(), [])
                    history.unlink()
                    with self.assertRaises(CreativeSkip):
                        load_editorial_stories()
                    history.write_text('{"stories":[]}')
                    reviews.unlink()
                    with self.assertRaises(CreativeSkip):
                        load_editorial_stories()


if __name__ == "__main__":
    unittest.main()
