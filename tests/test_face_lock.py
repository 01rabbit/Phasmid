import os
import sys
import tempfile
import time
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

    def test_reset_removes_template_and_runtime_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock = self.make_lock(tmp)
            sample = np.full(lock.FACE_SIZE, 80, dtype=np.float32)
            lock._write_templates(np.array([sample], dtype=np.float32))
            lock.create_session("client", "token")
            lock.failures["client"] = 1

            ok, message = lock.reset()

            self.assertTrue(ok)
            self.assertIn("cleared", message)
            self.assertFalse(lock.is_enrolled())
            self.assertFalse(os.path.exists(lock.template_path))
            self.assertEqual(lock.sessions, {})
            self.assertEqual(lock.failures, {})

    def test_enrollment_request_expires_and_clears(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock = self.make_lock(tmp)
            lock.ENROLLMENT_TTL_SECONDS = 1

            ok, message = lock.arm_enrollment()
            self.assertTrue(ok)
            self.assertIn("armed", message)
            self.assertTrue(lock.enrollment_pending())

            old_time = int(time.time()) - 10
            os.utime(lock.enrollment_path, (old_time, old_time))
            self.assertFalse(lock.enrollment_pending())
            self.assertFalse(os.path.exists(lock.enrollment_path))

    def test_clear_enrollment_request_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock = self.make_lock(tmp)
            self.assertTrue(lock.clear_enrollment_request()[0])


if __name__ == "__main__":
    unittest.main()
