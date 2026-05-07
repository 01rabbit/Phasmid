import os
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

from phasmid.volatile_state import (
    check_volatile_state,
    require_volatile_state,
    volatile_state_path,
    volatile_state_summary,
)


class TestVolatileStatePath(unittest.TestCase):
    def test_returns_none_when_not_configured(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            os.environ.pop("PHASMID_TMPFS_STATE", None)
            self.assertIsNone(volatile_state_path())

    def test_returns_configured_path(self):
        with mock.patch.dict(os.environ, {"PHASMID_TMPFS_STATE": "/run/phasmid-keys"}):
            self.assertEqual(volatile_state_path(), "/run/phasmid-keys")

    def test_empty_string_returns_none(self):
        with mock.patch.dict(os.environ, {"PHASMID_TMPFS_STATE": ""}):
            self.assertIsNone(volatile_state_path())


class TestCheckVolatileState(unittest.TestCase):
    def test_missing_path_returns_false(self):
        ok, msg = check_volatile_state("/nonexistent/path/xyz")
        self.assertFalse(ok)
        self.assertIn("does not exist", msg)

    def test_accessible_dir_returns_true(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.chmod(tmp, 0o700)
            ok, msg = check_volatile_state(tmp)
            self.assertTrue(ok)

    def test_file_instead_of_dir_returns_false(self):
        with tempfile.NamedTemporaryFile() as f:
            ok, msg = check_volatile_state(f.name)
            self.assertFalse(ok)
            self.assertIn("not a directory", msg)

    def test_permissive_dir_returns_true_with_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.chmod(tmp, 0o755)
            ok, msg = check_volatile_state(tmp)
            self.assertTrue(ok)
            self.assertIn("0o", msg)

    def test_restricted_dir_returns_clean_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.chmod(tmp, 0o700)
            ok, msg = check_volatile_state(tmp)
            self.assertTrue(ok)
            self.assertIn("accessible", msg)


class TestRequireVolatileState(unittest.TestCase):
    def test_no_env_var_does_not_raise(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            os.environ.pop("PHASMID_TMPFS_STATE", None)
            require_volatile_state()  # should not raise

    def test_missing_path_raises_runtime_error(self):
        with mock.patch.dict(
            os.environ, {"PHASMID_TMPFS_STATE": "/nonexistent/xyz/abc"}
        ):
            with self.assertRaises(RuntimeError) as ctx:
                require_volatile_state()
            self.assertIn("PHASMID_TMPFS_STATE", str(ctx.exception))
            self.assertIn("unavailable", str(ctx.exception))

    def test_existing_path_does_not_raise(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"PHASMID_TMPFS_STATE": tmp}):
                require_volatile_state()  # should not raise


class TestVolatileStateSummary(unittest.TestCase):
    def test_not_configured_summary(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            os.environ.pop("PHASMID_TMPFS_STATE", None)
            s = volatile_state_summary()
        self.assertFalse(s["configured"])

    def test_configured_and_accessible_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"PHASMID_TMPFS_STATE": tmp}):
                s = volatile_state_summary()
        self.assertTrue(s["configured"])
        self.assertTrue(s["path_accessible"])
        self.assertIn("message", s)

    def test_configured_and_missing_summary(self):
        with mock.patch.dict(
            os.environ, {"PHASMID_TMPFS_STATE": "/nonexistent/abc"}
        ):
            s = volatile_state_summary()
        self.assertTrue(s["configured"])
        self.assertFalse(s["path_accessible"])


class TestStateDirIntegration(unittest.TestCase):
    def test_state_dir_prefers_tmpfs_state(self):
        from phasmid.config import state_dir

        with mock.patch.dict(
            os.environ,
            {"PHASMID_TMPFS_STATE": "/run/phasmid-keys", "PHASMID_STATE_DIR": "/var/lib/phasmid"},
        ):
            self.assertEqual(state_dir(), "/run/phasmid-keys")

    def test_state_dir_falls_back_to_state_dir_env(self):
        from phasmid.config import state_dir

        env = {"PHASMID_STATE_DIR": "/var/lib/phasmid"}
        env.pop("PHASMID_TMPFS_STATE", None)
        with mock.patch.dict(os.environ, env, clear=False):
            os.environ.pop("PHASMID_TMPFS_STATE", None)
            self.assertEqual(state_dir(), "/var/lib/phasmid")

    def test_state_dir_uses_default_when_nothing_configured(self):
        from phasmid.config import DEFAULT_STATE_DIR, state_dir

        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("PHASMID_TMPFS_STATE", None)
            os.environ.pop("PHASMID_STATE_DIR", None)
            self.assertEqual(state_dir(), DEFAULT_STATE_DIR)


if __name__ == "__main__":
    unittest.main()
