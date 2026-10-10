import unittest
from tools.engine_lanes import enqueue, eligible

class EngineLaneTests(unittest.TestCase):
    def setUp(self):
        self.state = {'version': 1, 'jobs': [], 'published': []}

    def test_independent_lanes(self):
        self.assertTrue(enqueue(self.state, 'current', 'short', 'current-1', 'a.mp4'))
        self.assertTrue(enqueue(self.state, 'meta', 'short', 'meta-1', 'b.mp4'))
        self.assertEqual([j['lane'] for j in self.state['jobs']], ['current', 'meta'])

    def test_duplicate_key(self):
        enqueue(self.state, 'meta', 'short', 'same', 'a.mp4')
        self.assertFalse(enqueue(self.state, 'current', 'short', 'same', 'b.mp4'))

    def test_long_cooldown_global(self):
        enqueue(self.state, 'meta', 'long', 'm-long', 'a.mp4')
        self.state['published'].append({'key': 'old', 'format': 'long', 'confirmed_at': 1000})
        self.assertFalse(eligible(self.state, self.state['jobs'][0], now=1000+86399))
        self.assertTrue(eligible(self.state, self.state['jobs'][0], now=1000+86400))

    def test_long_blocked_by_inflight_other_lane(self):
        enqueue(self.state, 'meta', 'long', 'meta-long', 'a.mp4')
        enqueue(self.state, 'current', 'long', 'current-long', 'b.mp4')
        self.state['jobs'][0]['status'] = 'awaiting_confirmation'
        self.assertFalse(eligible(self.state, self.state['jobs'][1], now=90000))

    def test_shorts_not_blocked_by_long(self):
        enqueue(self.state, 'current', 'short', 'short-1', 'a.mp4')
        self.state['published'].append({'key': 'old', 'format': 'long', 'confirmed_at': 1000})
        self.assertTrue(eligible(self.state, self.state['jobs'][0], now=1001))

if __name__ == '__main__':
    unittest.main()
