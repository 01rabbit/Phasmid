import os
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

from phasmid import config
from phasmid.attempt_limiter import FileAttemptLimiter
from phasmid.capabilities import Capability
from phasmid.models.profile import Profile
from phasmid.restricted_actions import (
    RestrictedActionPolicy,
    RestrictedActionRejected,
    evaluate_restricted_action,
)
from phasmid.state_store import LocalStateStore, StateRecord, StateStoreError


class ObservabilitySupportTests(unittest.TestCase):
    def test_invalid_access_limit_environment_values_use_defaults(self):
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

    def test_file_attempt_limiter_persists_success_clear(self):
        with tempfile.TemporaryDirectory() as tmp:
            limiter = FileAttemptLimiter(
                store=LocalStateStore(tmp),
                max_failures=1,
                lockout_seconds=30,
                clock=lambda: 1000,
            )
            limiter.record_failure("cli")
            with mock.patch.object(limiter, "_save") as save:
                limiter.record_success("cli")
        save.assert_called_once()
        self.assertTrue(limiter.check("cli").allowed)

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

    def test_restricted_action_rejects_missing_object_cue(self):
        policy = RestrictedActionPolicy(
            action_id="test-action",
            capability=Capability.RESTRICTED_ACTION,
            confirmation_phrase="CONFIRM",
            require_object_cue=True,
        )
        with self.assertRaises(RestrictedActionRejected):
            evaluate_restricted_action(
                policy,
                capability_allowed=True,
                restricted_confirmed=True,
                confirmation="CONFIRM",
                object_cue_accepted=False,
            )

    def test_profile_from_dict_ignores_unknown_keys(self):
        profile = Profile.from_dict({"name": "field", "extra": "ignored"})
        self.assertEqual(profile.name, "field")
        self.assertFalse(hasattr(profile, "extra"))

    def test_profile_has_secrets_detects_forbidden_keys(self):
        profile = Profile()
        with mock.patch.object(Profile, "to_dict", return_value={"secret": "value"}):
            self.assertTrue(profile.has_secrets())


if __name__ == "__main__":
    unittest.main()
