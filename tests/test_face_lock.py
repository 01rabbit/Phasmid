import os
import sys
import tempfile
import unittest

import numpy as np

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

from phantasm.face_lock import FaceUILock


class FaceUILockTests(unittest.TestCase):
    def make_lock(self, tmp):
        lock = FaceUILock(state_path=tmp)
        lock.VERIFY_MAX_FAILURES = 2
        return lock

    def test_template_round_trip_supports_multiple_samples(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock = self.make_lock(tmp)
            samples = np.stack([
                np.full(lock.FACE_SIZE, 80, dtype=np.float32),
                np.full(lock.FACE_SIZE, 92, dtype=np.float32),
            ])

            lock._write_templates(samples)

            loaded = lock._read_templates()
            self.assertEqual(loaded.shape, samples.shape)
            self.assertTrue(lock._matches_any_template(samples[0], loaded))

    def test_failed_verification_locks_after_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock = self.make_lock(tmp)
            sample = np.full(lock.FACE_SIZE, 80, dtype=np.float32)
            lock._write_templates(np.array([sample], dtype=np.float32))
            with unittest.mock.patch.object(lock, "_collect_samples", return_value=[]):
                self.assertFalse(lock.verify_from_frames([object()], "client")[0])
                self.assertFalse(lock.verify_from_frames([object()], "client")[0])
                ok, message = lock.verify_from_frames([object()], "client")
            self.assertFalse(ok)
            self.assertIn("temporarily unavailable", message)


if __name__ == "__main__":
    unittest.main()
