import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
import tempfile
import unittest
from pathlib import Path

from astra_v2.story_ledger import StoryLedgerError, archive_fingerprints, archive_lifecycle_record, read_ledger


FP_A = "a" * 64
FP_B = "b" * 64


class DurableStoryLedgerTests(unittest.TestCase):
    def test_archive_is_durable_and_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "story-ledger.json"
            archive_fingerprints(path, [FP_A])
            archive_fingerprints(path, [FP_A, FP_B])
            self.assertEqual(read_ledger(path)["archived"], [FP_A, FP_B])

    def test_existing_archive_is_never_dropped(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "story-ledger.json"
            path.write_text(json.dumps({"version": 1, "archived": [FP_A]}), encoding="utf-8")
            archive_fingerprints(path, [FP_B])
            self.assertEqual(read_ledger(path)["archived"], [FP_A, FP_B])

    def test_corrupt_ledger_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "story-ledger.json"
            path.write_text("{broken", encoding="utf-8")
            with self.assertRaisesRegex(StoryLedgerError, "unreadable"):
                archive_fingerprints(path, [FP_A])
            self.assertEqual(path.read_text(encoding="utf-8"), "{broken")

    def test_invalid_fingerprint_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "story-ledger.json"
            with self.assertRaisesRegex(StoryLedgerError, "invalid_fingerprint"):
                archive_fingerprints(path, ["not-a-sha256"])
            self.assertFalse(path.exists())


    def test_episode_planner_excludes_archived_fingerprint_after_restart(self):
        from astra_v2.episode_planner import fingerprint, plan_episode_with_ledger

        scenes = [
            {"cause": "Gate jams", "action": "Inspect hinge", "consequence": "Pin bent"},
            {"cause": "Pin bent", "action": "Straighten pin", "consequence": "Hinge moves"},
            {"cause": "Hinge moves", "action": "Open gate", "consequence": "Village passes"},
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "story-ledger.json"
            archive_fingerprints(path, [fingerprint({"scenes": scenes})])
            with self.assertRaisesRegex(ValueError, "already_used"):
                plan_episode_with_ledger("village", 2, scenes, path)

    def test_episode_planner_fails_closed_if_ledger_corrupt(self):
        from astra_v2.episode_planner import plan_episode_with_ledger

        scenes = [
            {"cause": "Gate jams", "action": "Inspect hinge", "consequence": "Pin bent"},
            {"cause": "Pin bent", "action": "Straighten pin", "consequence": "Hinge moves"},
            {"cause": "Hinge moves", "action": "Open gate", "consequence": "Village passes"},
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "story-ledger.json"
            path.write_text("{broken", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "ledger_unavailable"):
                plan_episode_with_ledger("village", 2, scenes, path)


    def test_only_explicit_consumed_lifecycle_states_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "story-ledger.json"
            with self.assertRaisesRegex(StoryLedgerError, "not_archivable"):
                archive_lifecycle_record(path, {"plot_fingerprint": FP_A}, "draft")
            self.assertFalse(path.exists())
            archive_lifecycle_record(path, {"plot_fingerprint": FP_A}, "reserved")
            self.assertEqual(read_ledger(path)["archived"], [FP_A])

    def test_lifecycle_archival_rejects_missing_fingerprint(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "story-ledger.json"
            with self.assertRaisesRegex(StoryLedgerError, "fingerprint_missing"):
                archive_lifecycle_record(path, {}, "published")

    def test_invalid_existing_archive_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "story-ledger.json"
            original = json.dumps({"version": 1, "archived": ["not-a-sha256"]})
            path.write_text(original, encoding="utf-8")
            with self.assertRaisesRegex(StoryLedgerError, "invalid_archive"):
                archive_fingerprints(path, [FP_A])
            self.assertEqual(path.read_text(encoding="utf-8"), original)

    def test_parallel_archival_does_not_lose_updates(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "story-ledger.json"
            fingerprints = [format(index, "064x") for index in range(32)]
            with ThreadPoolExecutor(max_workers=8) as pool:
                list(pool.map(lambda fp: archive_fingerprints(path, [fp]), fingerprints))
            self.assertEqual(set(read_ledger(path)["archived"]), set(fingerprints))

    def test_publisher_record_identity_roundtrip_blocks_reuse(self):
        from astra_v2.episode_planner import plan_episode, plan_episode_with_ledger

        scenes = [
            {"cause": "Bell cracks", "action": "Find brass", "consequence": "Metal acquired"},
            {"cause": "Metal acquired", "action": "Repair bell", "consequence": "Bell rings"},
            {"cause": "Bell rings", "action": "Call neighbors", "consequence": "Town gathers"},
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "story-ledger.json"
            proposal = plan_episode("bell-town", 1, scenes)
            publisher_record = {"content_id": "episode-1", "plot_fingerprint": proposal["plot_fingerprint"]}
            archive_lifecycle_record(path, publisher_record, "published")
            with self.assertRaisesRegex(ValueError, "already_used"):
                plan_episode_with_ledger("bell-town", 2, scenes, path)
            self.assertFalse(proposal["production_ready"])

    def test_memory_archive_is_not_lost_when_disk_archive_is_empty(self):
        from astra_v2.episode_planner import fingerprint, plan_episode_with_ledger
        scenes = [
            {"cause": "Door sticks", "action": "Check frame", "consequence": "Warp discovered"},
            {"cause": "Warp discovered", "action": "Plane wood", "consequence": "Frame aligns"},
            {"cause": "Frame aligns", "action": "Open door", "consequence": "Room accessible"},
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "story-ledger.json"
            previous = fingerprint({"scenes": scenes})
            with self.assertRaisesRegex(ValueError, "already_used"):
                plan_episode_with_ledger("repair-room", 2, scenes, path, state={
                    "fingerprint_ledger": {"archived": [previous]}
                })

    def test_invalid_memory_archive_fails_closed(self):
        from astra_v2.episode_planner import plan_episode_with_ledger
        scenes = [
            {"cause": "Rain starts", "action": "Find shelter", "consequence": "Tent found"},
            {"cause": "Tent found", "action": "Raise tent", "consequence": "Cover ready"},
            {"cause": "Cover ready", "action": "Enter tent", "consequence": "Dry inside"},
        ]
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "invalid_state"):
                plan_episode_with_ledger("rain-camp", 1, scenes, Path(directory) / "ledger.json", state={
                    "fingerprint_ledger": {"archived": ["broken"]}
                })

    def test_separate_processes_preserve_all_fingerprints(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "story-ledger.json"
            script = (
                "import sys; from astra_v2.story_ledger import archive_fingerprints; "
                "archive_fingerprints(sys.argv[1], [sys.argv[2]])"
            )
            fingerprints = [format(index + 100, "064x") for index in range(12)]
            processes = [
                subprocess.Popen([sys.executable, "-c", script, str(path), fp])
                for fp in fingerprints
            ]
            for process in processes:
                self.assertEqual(process.wait(timeout=20), 0)
            self.assertEqual(set(read_ledger(path)["archived"]), set(fingerprints))

    def test_source_production_fingerprint_is_checked_separately(self):
        from astra_v2.episode_planner import plan_episode_with_ledger
        scenes = [
            {"cause": "Storm arrives", "action": "Find rope", "consequence": "Rope secured"},
            {"cause": "Rope secured", "action": "Tie boat", "consequence": "Boat stays"},
            {"cause": "Boat stays", "action": "Wait safely", "consequence": "Storm passes"},
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "story-ledger.json"
            archive_fingerprints(path, [FP_A])
            with self.assertRaisesRegex(ValueError, "already_used"):
                plan_episode_with_ledger("harbor", 1, scenes, path, source_plot_fingerprint=FP_A)
            proposal = plan_episode_with_ledger("harbor", 1, scenes, path, source_plot_fingerprint=FP_B)
            self.assertEqual(proposal["source_plot_fingerprint"], FP_B)
            self.assertNotEqual(proposal["plot_fingerprint"], FP_B)
            self.assertFalse(proposal["production_ready"])

    def test_invalid_source_fingerprint_is_rejected(self):
        from astra_v2.episode_planner import plan_episode
        scenes = [
            {"cause": "Wind rises", "action": "Close shutters", "consequence": "House safe"},
            {"cause": "House safe", "action": "Light lantern", "consequence": "Room bright"},
            {"cause": "Room bright", "action": "Read story", "consequence": "Night passes"},
        ]
        with self.assertRaisesRegex(ValueError, "invalid_source_plot_fingerprint"):
            plan_episode("wind-house", 1, scenes, source_plot_fingerprint="invalid")

    def test_story_forge_bridge_preserves_production_identity(self):
        from astra_v2.story_forge import propose_episode_from_story
        story = {"content_id": "sample-forge-1", "plot_fingerprint": FP_A,
                 "story_beats": [
                     {"speech": "Bridge breaks", "headline": "Problem", "label": "Bridge down"},
                     {"speech": "Team finds timber", "headline": "Plan", "label": "Materials ready"},
                     {"speech": "Team repairs bridge", "headline": "Repair", "label": "Bridge open"},
                 ]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.json"
            proposal = propose_episode_from_story(story, "bridge-series", 1, ledger_path=path)
            self.assertEqual(proposal["source_plot_fingerprint"], FP_A)
            self.assertEqual(proposal["source_content_id"], "sample-forge-1")
            self.assertFalse(proposal["production_ready"])
            archive_fingerprints(path, [FP_A])
            with self.assertRaisesRegex(ValueError, "already_used"):
                propose_episode_from_story(story, "bridge-series", 2, ledger_path=path)

    def test_story_forge_bridge_requires_production_identity(self):
        from astra_v2.story_forge import propose_episode_from_story
        story = {"content_id": "missing-fingerprint", "story_beats": [
            {"speech": "A boat drifts"},
            {"speech": "A rope is found"},
            {"speech": "The boat is secured"},
        ]}
        with self.assertRaisesRegex(ValueError, "source_fingerprint_required"):
            propose_episode_from_story(story, "boat-series", 1)
