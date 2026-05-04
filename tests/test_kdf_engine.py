"""Tests for KDFEngine module."""

import os
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

from phantasm.kdf_engine import KDFEngine


class KDFEngineTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.engine = KDFEngine(self.tmpdir)

    def test_derive_key_with_minimal_inputs(self):
        key = self.engine.derive_key(
            password="test_password",
            gesture_sequence=["a", "b"],
            mode="dummy",
            salt=b"x" * 16,
            password_role="open"
        )
        self.assertEqual(len(key), 32)
        self.assertIsInstance(key, bytes)

    def test_derive_key_with_hardware_secret_file(self):
        secret_file = os.path.join(self.tmpdir, "secret")
        with open(secret_file, "wb") as f:
            f.write(b"hardware_secret")

        with mock.patch.dict(os.environ, {"PHANTASM_HARDWARE_SECRET_FILE": secret_file}):
            key1 = self.engine.derive_key(
                password="test",
                gesture_sequence=["a"],
                mode="dummy",
                salt=b"x" * 16,
                password_role="open"
            )
            key2 = self.engine.derive_key(
                password="test",
                gesture_sequence=["a"],
                mode="dummy",
                salt=b"x" * 16,
                password_role="open"
            )
            self.assertEqual(key1, key2)  # Deterministic with same inputs

    def test_derive_key_with_hardware_secret_env(self):
        with mock.patch.dict(os.environ, {"PHANTASM_HARDWARE_SECRET": "env_secret"}):
            key = self.engine.derive_key(
                password="test",
                gesture_sequence=["a"],
                mode="dummy",
                salt=b"x" * 16,
                password_role="open"
            )
            self.assertEqual(len(key), 32)

    def test_get_or_create_access_key_creates_new(self):
        key1 = self.engine.get_or_create_access_key()
        self.assertEqual(len(key1), 32)

        # Second call should return same key
        key2 = self.engine.get_or_create_access_key()
        self.assertEqual(key1, key2)

    def test_destroy_access_keys_removes_file(self):
        self.engine.get_or_create_access_key()  # Create key
        key_path = os.path.join(self.tmpdir, "access.bin")
        self.assertTrue(os.path.exists(key_path))

        self.engine.destroy_access_keys()
        self.assertFalse(os.path.exists(key_path))

    def test_rotate_access_key_changes_key(self):
        key1 = self.engine.get_or_create_access_key()
        self.engine.rotate_access_key()
        key2 = self.engine.get_or_create_access_key()
        self.assertNotEqual(key1, key2)


if __name__ == "__main__":
    unittest.main()