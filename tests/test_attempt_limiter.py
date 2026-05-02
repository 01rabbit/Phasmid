import os
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(__file__))
import sys

sys.path.insert(0, os.path.join(ROOT, "src"))

from phantasm.attempt_limiter import AttemptLimiter, FileAttemptLimiter
from phantasm.state_store import LocalStateStore


class AttemptLimiterTests(unittest.TestCase):
    def test_repeated_failures_trigger_lockout(self):
        now = [1000]
        limiter = AttemptLimiter(
            max_failures=2,
            lockout_seconds=30,
            clock=lambda: now[0],
        )

        self.assertTrue(limiter.check("local").allowed)
        limiter.record_failure("local")
        self.assertTrue(limiter.check("local").allowed)
        limiter.record_failure("local")

        decision = limiter.check("local")
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.wait_seconds, 30)

    def test_success_resets_attempt_state(self):
        limiter = AttemptLimiter(max_failures=1, lockout_seconds=30, clock=lambda: 1000)

        limiter.record_failure("local")
        self.assertFalse(limiter.check("local").allowed)
        limiter.record_success("local")

        self.assertTrue(limiter.check("local").allowed)

    def test_file_limiter_persists_state(self):
        tmpdir = tempfile.mkdtemp()
        store = LocalStateStore(tmpdir)
        limiter = FileAttemptLimiter(
            store=store,
            max_failures=1,
            lockout_seconds=30,
            clock=lambda: 1000,
        )
        limiter.record_failure("cli")

        restored = FileAttemptLimiter(
            store=store,
            max_failures=1,
            lockout_seconds=30,
            clock=lambda: 1000,
        )

        self.assertFalse(restored.check("cli").allowed)


if __name__ == "__main__":
    unittest.main()
