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

    def test_cosmetic_case_and_punctuation_do_not_change_fingerprint(self):
        altered = [{k: v.upper() + '!!!' for k, v in scene.items()} for scene in SCENES]
        self.assertEqual(fingerprint({'scenes': SCENES}), fingerprint({'scenes': altered}))

    def test_scene_order_changes_fingerprint(self):
        reordered = [SCENES[1], SCENES[0], SCENES[2]]
        self.assertNotEqual(fingerprint({'scenes': SCENES}), fingerprint({'scenes': reordered}))

    def test_malformed_ledger_does_not_crash_lookup(self):
        self.assertEqual(known_fingerprints({'fingerprint_ledger': {'archived': None}}), set())

    def test_explicit_scene_state_must_carry_forward(self):
        scenes = [
            {'cause': 'Gate jams', 'action': 'Inspect hinge', 'consequence': 'Pin bent',
             'state_before': 'gate jammed', 'state_after': 'pin bent'},
            {'cause': 'Pin bent', 'action': 'Straighten pin', 'consequence': 'Gate moves',
             'state_before': 'pin bent', 'state_after': 'pin straight'},
            {'cause': 'Gate moves', 'action': 'Open gate', 'consequence': 'Village passes',
             'state_before': 'pin straight', 'state_after': 'gate open'},
        ]
        self.assertFalse(plan_episode('village', 3, scenes)['production_ready'])

    def test_discontinuous_explicit_state_is_rejected(self):
        scenes = [
            {'cause': 'Gate jams', 'action': 'Inspect hinge', 'consequence': 'Pin bent',
             'state_before': 'gate jammed', 'state_after': 'pin bent'},
            {'cause': 'Pin bent', 'action': 'Straighten pin', 'consequence': 'Gate moves',
             'state_before': 'gate repaired', 'state_after': 'gate open'},
            {'cause': 'Gate moves', 'action': 'Open gate', 'consequence': 'Village passes'},
        ]
        with self.assertRaisesRegex(ValueError, 'scene_state_discontinuity'):
            plan_episode('village', 4, scenes)
