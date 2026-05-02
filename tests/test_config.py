import os
import sys
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

from phantasm import config


class ConfigTests(unittest.TestCase):
    def test_default_state_names_are_neutral(self):
        self.assertEqual(config.DEFAULT_STATE_DIR, ".state")
        self.assertEqual(config.STATE_BLOB_NAME, "store.bin")
        self.assertEqual(config.STATE_KEY_NAME, "lock.bin")
        self.assertEqual(config.VAULT_KEY_NAME, "access.bin")
        self.assertEqual(config.PANIC_TOKEN_NAME, "signal.key")
        self.assertEqual(config.PANIC_TRIGGER_NAME, "signal.trigger")
        self.assertEqual(config.AUDIT_LOG_NAME, "events.log")
        self.assertEqual(config.AUDIT_AUTH_NAME, "events.auth")
        self.assertEqual(config.FACE_TEMPLATE_NAME, "face.bin")
        self.assertEqual(config.FACE_ENROLL_FLAG_NAME, "face.enroll")

    def test_purge_confirmation_defaults_to_required(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertTrue(config.purge_confirmation_required())

    def test_duress_mode_defaults_to_disabled(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertFalse(config.duress_mode_enabled())

    def test_face_enrollment_defaults_to_disabled(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertFalse(config.ui_face_enrollment_enabled())

    def test_face_enrollment_can_be_enabled(self):
        with mock.patch.dict(os.environ, {"PHANTASM_UI_FACE_ENROLL": "1"}, clear=True):
            self.assertTrue(config.ui_face_enrollment_enabled())

    def test_field_mode_can_be_enabled(self):
        with mock.patch.dict(os.environ, {"PHANTASM_FIELD_MODE": "1"}, clear=True):
            self.assertTrue(config.field_mode_enabled())

    def test_field_mode_defaults_to_disabled(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertFalse(config.field_mode_enabled())


if __name__ == "__main__":
    unittest.main()
