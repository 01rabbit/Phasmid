import json
import os
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

from phasmid import config
from phasmid.roles import RoleStore
from phasmid.state_store import LocalStateStore, StateRecord, StateStoreError


class DualApprovalSupportTests(unittest.TestCase):
    def test_role_store_init_tolerates_directory_chmod_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch("phasmid.roles.os.chmod", side_effect=OSError):
                store = RoleStore(state_path=tmp)
        self.assertEqual(store._state_dir, tmp)

    def test_configure_supervisor_returns_store_failure_on_write_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = RoleStore(state_path=tmp)
            with mock.patch("phasmid.roles.open", side_effect=OSError):
                ok, message = store.configure_supervisor("supervisor-passphrase")
        self.assertFalse(ok)
        self.assertEqual(message, "Store operation failed.")

    def test_verify_supervisor_returns_store_error_on_invalid_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = RoleStore(state_path=tmp)
            store.configure_supervisor("supervisor-passphrase")
            with mock.patch.object(store, "_read_supervisor", side_effect=ValueError):
                result = store.verify_supervisor("supervisor-passphrase")
        self.assertFalse(result.verified)
        self.assertEqual(result.reason, "store_error")

    def test_clear_returns_failure_when_overwrite_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = RoleStore(state_path=tmp)
            store.configure_supervisor("supervisor-passphrase")
            with mock.patch("phasmid.roles.open", side_effect=OSError):
                ok, message = store.clear()
        self.assertFalse(ok)
        self.assertEqual(message, "Failed to clear supervisor passphrase.")

    def test_read_supervisor_rejects_non_dict_supervisor_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = RoleStore(state_path=tmp)
            store.configure_supervisor("supervisor-passphrase")
            with mock.patch.object(
                store._cipher,
                "decrypt",
                return_value=b'{"schema": 1, "supervisor": []}',
            ):
                with self.assertRaises(ValueError):
                    store._read_supervisor()

    def test_access_limits_use_defaults_for_invalid_environment_values(self):
        with mock.patch.dict(
            os.environ,
            {
                "PHASMID_ACCESS_MAX_FAILURES": "bad",
                "PHASMID_ACCESS_LOCKOUT_SECONDS": "bad",
            },
            clear=True,
        ):
            self.assertEqual(config.access_max_failures(), 5)
            self.assertEqual(config.access_lockout_seconds(), 60)

    def test_dual_approval_flag_defaults_to_disabled(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertFalse(config.dual_approval_enabled())

    def test_dual_approval_flag_can_be_enabled(self):
        with mock.patch.dict(os.environ, {"PHASMID_DUAL_APPROVAL": "1"}, clear=True):
            self.assertTrue(config.dual_approval_enabled())

    def test_state_record_rejects_non_mapping(self):
        with self.assertRaises(StateStoreError):
            StateRecord.from_dict("not-a-dict")

    def test_state_record_rejects_unsupported_schema(self):
        payload = {
            "schema_version": 99,
            "category": "local_state",
            "phase": "initialized",
            "attributes": {},
        }
        with self.assertRaises(StateStoreError):
            StateRecord.from_dict(payload)

    def test_state_record_rejects_non_dict_attributes(self):
        payload = {
            "schema_version": 1,
            "category": "local_state",
            "phase": "initialized",
            "attributes": [],
        }
        with self.assertRaises(StateStoreError):
            StateRecord.from_dict(payload)

    def test_local_state_store_tolerates_directory_chmod_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalStateStore(tmp)
            with mock.patch("phasmid.state_store.os.chmod", side_effect=OSError):
                store.ensure_root()
            self.assertTrue(os.path.isdir(tmp))

    def test_write_json_atomic_cleans_up_temp_file_after_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalStateStore(tmp)
            with mock.patch("phasmid.state_store.os.replace", side_effect=OSError):
                with self.assertRaises(OSError):
                    store.write_json_atomic("state.json", {"ok": True})
            leftovers = [name for name in os.listdir(tmp) if name.endswith(".tmp")]
        self.assertEqual(leftovers, [])

    def test_sync_root_tolerates_oserror(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalStateStore(tmp)
            with mock.patch("phasmid.state_store.os.open", side_effect=OSError):
                store._sync_root()

    def test_read_json_returns_saved_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalStateStore(tmp)
            store.ensure_root()
            path = store.path_for("payload.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump({"ok": True}, handle)
            self.assertEqual(store.read_json("payload.json"), {"ok": True})


if __name__ == "__main__":
    unittest.main()
