"""Keep proposal visuals grounded and publication isolation intact."""
import re
import unittest

from astra_v2.autonomous_story_proposals import proposal
from astra_v2.publication_quality import publication_rejection
from astra_v2.story_subject_taxonomy import SUBJECTS


class ProposalVisualVarietyTests(unittest.TestCase):
    def test_sampled_proposal_visuals_are_supported_by_their_own_narration(self):
        subject_patterns = dict(SUBJECTS)
        for index in range(2000):
            story = proposal(index)
            for beat in story["story_beats"]:
                visual = beat["visual"]
                speech = beat["speech"]
                if visual == "story":
                    continue
                pattern = subject_patterns.get(visual)
                supported = bool(pattern and re.search(pattern, speech, re.I))
                if not supported:
                    supported = bool(re.search(
                        r"(?<!\\w)" + re.escape(visual) + r"(?!\\w)", speech, re.I
                    ))
                self.assertTrue(supported, (index, visual, speech))
            self.assertEqual(story, proposal(index))
            self.assertFalse(story["production_ready"])
            self.assertEqual(publication_rejection(story), "unreviewed_causal_draft")


if __name__ == "__main__":
    unittest.main()
