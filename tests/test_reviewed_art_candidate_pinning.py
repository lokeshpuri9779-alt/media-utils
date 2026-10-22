"""Contract tests for pinned reviewed-art candidate selection."""
import ast
import unittest
from pathlib import Path


class ReviewedArtCandidatePinningTests(unittest.TestCase):
    def test_pinning_precedes_render(self):
        source = Path("astra_v2/creative.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                  and node.name == "make_candidate")
        body = ast.get_source_segment(source, fn)
        self.assertLess(body.index('pinned_reviewed_art_story_not_available_in_lane'),
                        body.index('story = attach_reviewed_art(story)'))
        self.assertIn('story.get("content_id") == pinned_id', body)
        self.assertIn('reviewed_art_content_id_required_for_candidate', body)


if __name__ == "__main__":
    unittest.main()
