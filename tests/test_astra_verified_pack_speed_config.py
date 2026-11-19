"""Guard the verified-pack speed path without relaxing any publishing gates.

The runtime cache is valid only because the restored media pack has passed full
validation and is not modified for the rest of this render job.
"""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
FLAG = "ASTRA_ASSET_PACK_IMMUTABLE: '1'"


def step_block(workflow: str, name: str) -> str:
    marker = f"      - name: {name}"
    if workflow.count(marker) != 1:
        raise AssertionError(f"Expected exactly one step: {name}")
    tail = workflow[workflow.index(marker):]
    next_step = tail.find("\n      - ", len(marker))
    return tail if next_step < 0 else tail[:next_step]


class VerifiedPackSpeedConfigTests(unittest.TestCase):
    def test_publisher_only_caches_after_verified_restore(self):
        workflow = (ROOT / ".github/workflows/astra-v2-publish.yml").read_text()
        validated = workflow.index("      - name: Validate production asset pack")
        rendering = workflow.index("      - name: Generate, validate, publish, and verify")
        self.assertLess(validated, rendering)
        self.assertNotIn(FLAG, workflow[:rendering])
        self.assertIn(FLAG, step_block(workflow, "Generate, validate, publish, and verify"))
        self.assertIn("ASTRA_ASSET_PACK_AUDIT: '1'", step_block(workflow, "Generate, validate, publish, and verify"))
        self.assertIn("python -m tools.astra_restore_visual_pack", step_block(workflow, "Validate production asset pack"))

    def test_preload_only_caches_after_verified_restore(self):
        workflow = (ROOT / ".github/workflows/astra-v2-preload.yml").read_text()
        validated = workflow.index("      - name: Verify restored reusable visual pack")
        rendering = workflow.index("      - name: Render and approve next original video")
        self.assertLess(validated, rendering)
        self.assertNotIn(FLAG, workflow[:rendering])
        self.assertIn(FLAG, step_block(workflow, "Render and approve next original video"))
        self.assertIn("python -m tools.astra_restore_visual_pack", step_block(workflow, "Verify restored reusable visual pack"))


if __name__ == "__main__":
    unittest.main()
