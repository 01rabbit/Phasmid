import os
import sys
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

from phasmid.process_hardening import (
    HardeningStatus,
    apply_process_hardening,
    hardening_status,
)


class TestHardeningStatus(unittest.TestCase):
    def test_all_applied_true_when_all_true(self):
        s = HardeningStatus(
            umask_applied=True,
            core_dumps_disabled=True,
            dumpable_cleared=True,
            memory_locked=True,
        )
        self.assertTrue(s.all_applied())

    def test_all_applied_false_when_any_false(self):
        s = HardeningStatus(
            umask_applied=True,
            core_dumps_disabled=False,
            dumpable_cleared=True,
            memory_locked=True,
        )
        self.assertFalse(s.all_applied())

    def test_as_dict_contains_all_fields(self):
        s = HardeningStatus(
            umask_applied=True,
            core_dumps_disabled=False,
            dumpable_cleared=False,
            memory_locked=False,
        )
        d = s.as_dict()
        self.assertIn("umask_applied", d)
        self.assertIn("core_dumps_disabled", d)
        self.assertIn("dumpable_cleared", d)
        self.assertIn("memory_locked", d)

    def test_as_dict_values_are_bool(self):
        s = HardeningStatus(
            umask_applied=True,
            core_dumps_disabled=False,
            dumpable_cleared=True,
            memory_locked=False,
        )
        for v in s.as_dict().values():
            self.assertIsInstance(v, bool)


class TestApplyProcessHardening(unittest.TestCase):
    def setUp(self):
        import phasmid.process_hardening as mod
        mod._cached_status = None

    def tearDown(self):
        import phasmid.process_hardening as mod
        mod._cached_status = None

    def test_returns_hardening_status(self):
        result = apply_process_hardening()
        self.assertIsInstance(result, HardeningStatus)

    def test_umask_field_is_bool(self):
        result = apply_process_hardening()
        self.assertIsInstance(result.umask_applied, bool)

    def test_umask_applied_on_all_platforms(self):
        result = apply_process_hardening()
        self.assertTrue(result.umask_applied)

    def test_result_is_cached_on_second_call(self):
        first = apply_process_hardening()
        second = apply_process_hardening()
        self.assertIs(first, second)

    def test_hardening_status_returns_cached_after_apply(self):
        apply_process_hardening()
        self.assertIsNotNone(hardening_status())

    def test_hardening_status_returns_none_before_apply(self):
        self.assertIsNone(hardening_status())

    def test_non_linux_skips_dumpable_and_mlock(self):
        import phasmid.process_hardening as mod
        with mock.patch.object(mod.sys, "platform", "darwin"):
            mod._cached_status = None
            result = apply_process_hardening()
        self.assertFalse(result.dumpable_cleared)
        self.assertFalse(result.memory_locked)

    def test_core_dump_disable_is_bool(self):
        result = apply_process_hardening()
        self.assertIsInstance(result.core_dumps_disabled, bool)

    def test_dumpable_cleared_is_bool(self):
        result = apply_process_hardening()
        self.assertIsInstance(result.dumpable_cleared, bool)

    def test_memory_locked_is_bool(self):
        result = apply_process_hardening()
        self.assertIsInstance(result.memory_locked, bool)

    def test_resource_import_failure_does_not_raise(self):
        import phasmid.process_hardening as mod
        with mock.patch.dict("sys.modules", {"resource": None}):
            mod._cached_status = None
            result = apply_process_hardening()
        self.assertIsInstance(result, HardeningStatus)
        self.assertFalse(result.core_dumps_disabled)


if __name__ == "__main__":
    unittest.main()
