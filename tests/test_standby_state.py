import os
import sys
import threading
import unittest

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

from phasmid.standby_state import (
    InvalidTransitionError,
    StandbyState,
    StandbyStateMachine,
)


class TestStandbyStateMachineInitial(unittest.TestCase):
    def test_initial_state_is_active(self):
        sm = StandbyStateMachine()
        self.assertEqual(sm.state, StandbyState.ACTIVE)

    def test_is_active_returns_true_initially(self):
        sm = StandbyStateMachine()
        self.assertTrue(sm.is_active())

    def test_is_sealed_returns_false_initially(self):
        sm = StandbyStateMachine()
        self.assertFalse(sm.is_sealed())

    def test_is_dummy_disclosure_returns_false_initially(self):
        sm = StandbyStateMachine()
        self.assertFalse(sm.is_dummy_disclosure())


class TestTriggerStandby(unittest.TestCase):
    def test_trigger_standby_transitions_to_sealed(self):
        sm = StandbyStateMachine()
        sm.trigger_standby()
        self.assertEqual(sm.state, StandbyState.SEALED)

    def test_trigger_standby_sets_is_sealed(self):
        sm = StandbyStateMachine()
        sm.trigger_standby()
        self.assertTrue(sm.is_sealed())

    def test_trigger_standby_clears_is_active(self):
        sm = StandbyStateMachine()
        sm.trigger_standby()
        self.assertFalse(sm.is_active())

    def test_trigger_standby_from_sealed_raises(self):
        sm = StandbyStateMachine()
        sm.trigger_standby()
        with self.assertRaises(InvalidTransitionError):
            sm.trigger_standby()

    def test_trigger_standby_from_dummy_disclosure_raises(self):
        sm = StandbyStateMachine()
        sm.trigger_standby()
        sm.enter_dummy_disclosure()
        with self.assertRaises(InvalidTransitionError):
            sm.trigger_standby()


class TestRecover(unittest.TestCase):
    def test_recover_from_sealed_returns_to_active(self):
        sm = StandbyStateMachine()
        sm.trigger_standby()
        sm.recover()
        self.assertEqual(sm.state, StandbyState.ACTIVE)

    def test_recover_from_active_raises(self):
        sm = StandbyStateMachine()
        with self.assertRaises(InvalidTransitionError):
            sm.recover()

    def test_recover_requires_re_authentication_conceptually(self):
        """Recovery from sealed back to active must go through recover(), not directly."""
        sm = StandbyStateMachine()
        sm.trigger_standby()
        self.assertTrue(sm.is_sealed())
        sm.recover()
        self.assertTrue(sm.is_active())

    def test_direct_restoration_of_previous_state_is_disallowed(self):
        """After standby, the state is sealed — direct active access without recover() is blocked."""
        sm = StandbyStateMachine()
        sm.trigger_standby()
        self.assertFalse(sm.is_active())


class TestDummyDisclosure(unittest.TestCase):
    def test_enter_dummy_disclosure_from_sealed(self):
        sm = StandbyStateMachine()
        sm.trigger_standby()
        sm.enter_dummy_disclosure()
        self.assertEqual(sm.state, StandbyState.DUMMY_DISCLOSURE)

    def test_enter_dummy_disclosure_from_active_raises(self):
        sm = StandbyStateMachine()
        with self.assertRaises(InvalidTransitionError):
            sm.enter_dummy_disclosure()

    def test_seal_dummy_returns_to_sealed(self):
        sm = StandbyStateMachine()
        sm.trigger_standby()
        sm.enter_dummy_disclosure()
        sm.seal_dummy()
        self.assertEqual(sm.state, StandbyState.SEALED)

    def test_seal_dummy_from_sealed_raises(self):
        sm = StandbyStateMachine()
        sm.trigger_standby()
        with self.assertRaises(InvalidTransitionError):
            sm.seal_dummy()

    def test_full_coercion_safe_flow(self):
        """sealed → dummy_disclosure → sealed → active (recover)."""
        sm = StandbyStateMachine()
        sm.trigger_standby()
        sm.enter_dummy_disclosure()
        sm.seal_dummy()
        sm.recover()
        self.assertEqual(sm.state, StandbyState.ACTIVE)


class TestStatusDict(unittest.TestCase):
    def test_status_dict_returns_state(self):
        sm = StandbyStateMachine()
        d = sm.status_dict()
        self.assertIn("state", d)
        self.assertEqual(d["state"], "active")

    def test_status_dict_after_standby(self):
        sm = StandbyStateMachine()
        sm.trigger_standby()
        d = sm.status_dict()
        self.assertEqual(d["state"], "sealed")

    def test_status_dict_contains_no_key_material(self):
        sm = StandbyStateMachine()
        d = sm.status_dict()
        for v in d.values():
            self.assertNotIsInstance(v, bytes)


class TestThreadSafety(unittest.TestCase):
    def test_concurrent_trigger_only_one_succeeds(self):
        sm = StandbyStateMachine()
        successes = []
        errors = []

        def try_trigger():
            try:
                sm.trigger_standby()
                successes.append(True)
            except InvalidTransitionError:
                errors.append(True)

        threads = [threading.Thread(target=try_trigger) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(successes), 1)
        self.assertEqual(len(successes) + len(errors), 10)

    def test_state_consistent_after_concurrent_access(self):
        sm = StandbyStateMachine()
        sm.trigger_standby()

        results = []

        def check_state():
            results.append(sm.state)

        threads = [threading.Thread(target=check_state) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        for r in results:
            self.assertEqual(r, StandbyState.SEALED)


class TestIsInStandbyOrSealed(unittest.TestCase):
    def test_active_is_not_standby_or_sealed(self):
        sm = StandbyStateMachine()
        self.assertFalse(sm.is_in_standby_or_sealed())

    def test_sealed_is_standby_or_sealed(self):
        sm = StandbyStateMachine()
        sm.trigger_standby()
        self.assertTrue(sm.is_in_standby_or_sealed())


if __name__ == "__main__":
    unittest.main()
