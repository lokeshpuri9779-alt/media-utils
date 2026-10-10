import tempfile
import unittest
from pathlib import Path
from tools.engine_lanes import enqueue, load, save
from tools.reserve_job import reserve

class ReservationTests(unittest.TestCase):
    def test_single_reservation(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'state.json'
            state = load(path)
            enqueue(state, 'meta', 'short', 'clip-1', 'clip.mp4')
            save(path, state)
            self.assertTrue(reserve(path, 'clip-1'))
            self.assertFalse(reserve(path, 'clip-1'))
            self.assertEqual(load(path)['jobs'][0]['status'], 'reserved')

    def test_existing_lock_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'state.json'
            Path(str(path) + '.lock').write_text('locked')
            with self.assertRaises(RuntimeError):
                reserve(path, 'missing')

    def test_long_inflight_prevents_second_reservation(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'state.json'
            state = load(path)
            enqueue(state, 'meta', 'long', 'm1', 'a.mp4')
            enqueue(state, 'current', 'long', 'c1', 'b.mp4')
            save(path, state)
            self.assertTrue(reserve(path, 'm1'))
            self.assertFalse(reserve(path, 'c1'))

if __name__ == '__main__':
    unittest.main()
