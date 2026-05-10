import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

from phasmid import config


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

    def test_purge_confirmation_defaults_to_required(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertTrue(config.purge_confirmation_required())

    def test_duress_mode_defaults_to_disabled(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertFalse(config.duress_mode_enabled())

    def test_field_mode_can_be_enabled(self):
        with mock.patch.dict(os.environ, {"PHASMID_FIELD_MODE": "1"}, clear=True):
            self.assertTrue(config.field_mode_enabled())

    def test_field_mode_defaults_to_disabled(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertFalse(config.field_mode_enabled())

    def test_experimental_object_model_defaults_to_disabled(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertFalse(config.experimental_object_model_enabled())

    def test_experimental_object_model_can_be_enabled(self):
        with mock.patch.dict(
            os.environ, {"PHASMID_EXPERIMENTAL_OBJECT_MODEL": "1"}, clear=True
        ):
            self.assertTrue(config.experimental_object_model_enabled())

    def test_object_model_path_defaults_to_empty(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(config.object_model_path(), "")

    def test_object_model_path_reads_env(self):
        with mock.patch.dict(
            os.environ,
            {"PHASMID_OBJECT_MODEL_PATH": "/tmp/object-gate/model.tflite"},
            clear=True,
        ):
            self.assertEqual(
                config.object_model_path(), "/tmp/object-gate/model.tflite"
            )

    def test_passphrase_min_length_defaults_and_handles_invalid_env(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(config.passphrase_min_length(), 10)
        with mock.patch.dict(
            os.environ, {"PHASMID_MIN_PASSPHRASE_LENGTH": "12"}, clear=True
        ):
            self.assertEqual(config.passphrase_min_length(), 12)
        with mock.patch.dict(
            os.environ, {"PHASMID_MIN_PASSPHRASE_LENGTH": "bad"}, clear=True
        ):
            self.assertEqual(config.passphrase_min_length(), 10)

    def test_access_attempt_limits_default_and_env(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(config.access_max_failures(), 5)
            self.assertEqual(config.access_lockout_seconds(), 60)
        with mock.patch.dict(
            os.environ,
            {
                "PHASMID_ACCESS_MAX_FAILURES": "2",
                "PHASMID_ACCESS_LOCKOUT_SECONDS": "9",
            },
            clear=True,
        ):
            self.assertEqual(config.access_max_failures(), 2)
            self.assertEqual(config.access_lockout_seconds(), 9)

    def test_web_host_and_port_defaults_and_invalid(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(config.web_host(), "127.0.0.1")
            self.assertEqual(config.web_port(), 8000)
        with mock.patch.dict(os.environ, {"PHASMID_PORT": "bad"}, clear=True):
            self.assertEqual(config.web_port(), 8000)
        with mock.patch.dict(os.environ, {"PHASMID_PORT": "0"}, clear=True):
            self.assertEqual(config.web_port(), 1)

    def test_runtime_flags_and_limits(self):
        with mock.patch.dict(
            os.environ,
            {
                "PHASMID_AUDIT": "1",
                "PHASMID_DEBUG": "true",
                "PHASMID_MAX_UPLOAD_BYTES": "8192",
                "PHASMID_RESTRICTED_SESSION_SECONDS": "42",
                "PHASMID_DOCTOR_RECENT_SECONDS": "120",
            },
            clear=True,
        ):
            self.assertTrue(config.audit_enabled())
            self.assertTrue(config.debug_enabled())
            self.assertEqual(config.max_upload_bytes(), 8192)
            self.assertEqual(config.restricted_session_seconds(), 42)
            self.assertEqual(config.doctor_recent_seconds(), 120)

    def test_dummy_plausibility_threshold_config(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(config.dummy_min_size_mb(), 50)
            self.assertEqual(config.dummy_min_file_count(), 20)
            self.assertEqual(config.dummy_occupancy_warn(), 0.10)
        with mock.patch.dict(
            os.environ,
            {
                "PHASMID_DUMMY_MIN_SIZE_MB": "7",
                "PHASMID_DUMMY_MIN_FILE_COUNT": "42",
                "PHASMID_DUMMY_OCCUPANCY_WARN": "0.25",
            },
            clear=True,
        ):
            self.assertEqual(config.dummy_min_size_mb(), 7)
            self.assertEqual(config.dummy_min_file_count(), 42)
            self.assertEqual(config.dummy_occupancy_warn(), 0.25)

    def test_no_direct_phasmid_env_reads_outside_config(self):
        root = Path(ROOT) / "src" / "phasmid"
        offenders: list[str] = []
        for path in root.rglob("*.py"):
            if path.name == "config.py":
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if 'os.environ.get("PHASMID_' in text:
                offenders.append(str(path.relative_to(root)))
        self.assertFalse(
            offenders,
            "Direct PHASMID_* env reads outside config.py:\n" + "\n".join(offenders),
        )


if __name__ == "__main__":
    unittest.main()
