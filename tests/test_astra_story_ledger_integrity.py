import unittest
from astra_v2.episode_planner import fingerprint, known_fingerprints, plan_episode

SCENES = [
    {'cause': 'A gate jams', 'action': 'A fox inspects the hinge', 'consequence': 'A bent pin is found'},
    {'cause': 'The pin is bent', 'action': 'The fox straightens it', 'consequence': 'The hinge moves'},
    {'cause': 'The hinge moves', 'action': 'The fox opens the gate', 'consequence': 'The village can pass'},
]

class StoryLedgerIntegrityTests(unittest.TestCase):
    def test_archived_fingerprint_prevents_reuse(self):
        fp = fingerprint({'scenes': SCENES})
        state = {'fingerprint_ledger': {'archived': [fp]}}
        self.assertIn(fp, known_fingerprints(state))
        with self.assertRaisesRegex(ValueError, 'already_used'):
            plan_episode('village', 2, SCENES, state)

    def test_unreviewed_proposal_is_never_approved(self):
        proposal = plan_episode('village', 1, SCENES)
        self.assertIs(proposal['production_ready'], False)
        self.assertEqual(proposal['kind'], 'unreviewed_episode_plan')
