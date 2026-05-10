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
from phasmid.observability_probe import (
    ObservabilityProbe,
    ObservabilityReport,
    PathObservation,
    RecoveryPath,
)
from phasmid.restricted_actions import (
    RestrictedActionPolicy,
    RestrictedActionRejected,
    evaluate_restricted_action,
)
from phasmid.state_store import LocalStateStore, StateRecord, StateStoreError


def _fast_kdf(password: bytes, salt: bytes) -> bytes:
    """Minimal stand-in KDF for unit tests (no iteration cost)."""
    import hashlib

    return hashlib.sha256(password + salt).digest()


class TestPathObservation(unittest.TestCase):
    def _make(
        self,
        path_type,
        kdf_ms=10.0,
        total_ms=20.0,
        outcome="success",
        bytes_written=0,
        exception_raised=False,
    ):
        return PathObservation(
            path_type=path_type,
            kdf_wall_ms=kdf_ms,
            total_wall_ms=total_ms,
            outcome=outcome,
            bytes_written=bytes_written,
            exception_raised=exception_raised,
        )

    def test_fields_are_accessible(self):
        obs = self._make(RecoveryPath.NORMAL)
        self.assertEqual(obs.path_type, RecoveryPath.NORMAL)
        self.assertEqual(obs.outcome, "success")
        self.assertFalse(obs.exception_raised)

    def test_failed_path_marks_exception(self):
        obs = self._make(
            RecoveryPath.FAILED, exception_raised=True, outcome="auth_failure"
        )
        self.assertTrue(obs.exception_raised)
        self.assertEqual(obs.outcome, "auth_failure")


class TestObservabilityReport(unittest.TestCase):
    def _report(self):
        return ObservabilityReport(
            observations=[
                PathObservation(RecoveryPath.NORMAL, 50.0, 60.0, "success", 256, False),
                PathObservation(
                    RecoveryPath.FAILED, 50.0, 51.0, "auth_failure", 0, True
                ),
                PathObservation(
                    RecoveryPath.RESTRICTED, 50.0, 80.0, "restricted_clear", 768, False
                ),
            ]
        )

    def test_summary_contains_all_paths(self):
        report = self._report()
        s = report.summary()
        self.assertIn("normal", s)
        self.assertIn("failed", s)
        self.assertIn("restricted", s)

    def test_summary_outcome_values(self):
        s = self._report().summary()
        self.assertEqual(s["normal"]["outcome"], "success")
        self.assertEqual(s["failed"]["outcome"], "auth_failure")
        self.assertEqual(s["restricted"]["outcome"], "restricted_clear")

    def test_max_timing_delta(self):
        report = self._report()
        delta = report.max_timing_delta_ms()
        self.assertAlmostEqual(delta, 80.0 - 51.0, places=1)

    def test_paths_with_filesystem_writes(self):
        report = self._report()
        writers = report.paths_with_filesystem_writes()
        self.assertIn("normal", writers)
        self.assertIn("restricted", writers)
        self.assertNotIn("failed", writers)

    def test_empty_report_delta_is_zero(self):
        report = ObservabilityReport()
        self.assertEqual(report.max_timing_delta_ms(), 0.0)

    def test_empty_report_no_writers(self):
        report = ObservabilityReport()
        self.assertEqual(report.paths_with_filesystem_writes(), [])


class TestObservabilityProbe(unittest.TestCase):
    def setUp(self):
        self.probe = ObservabilityProbe(kdf_fn=_fast_kdf)

    # ------------------------------------------------------------------
    # Individual path outcomes
    # ------------------------------------------------------------------

    def test_normal_path_returns_success(self):
        obs = self.probe.measure_path(RecoveryPath.NORMAL)
        self.assertEqual(obs.path_type, RecoveryPath.NORMAL)
        self.assertEqual(obs.outcome, "success")
        self.assertFalse(obs.exception_raised)
        self.assertGreater(obs.bytes_written, 0)

    def test_failed_path_returns_auth_failure(self):
        obs = self.probe.measure_path(RecoveryPath.FAILED)
        self.assertEqual(obs.path_type, RecoveryPath.FAILED)
        self.assertEqual(obs.outcome, "auth_failure")
        self.assertTrue(obs.exception_raised)
        self.assertEqual(obs.bytes_written, 0)

    def test_restricted_path_returns_restricted_clear(self):
        obs = self.probe.measure_path(RecoveryPath.RESTRICTED)
        self.assertEqual(obs.path_type, RecoveryPath.RESTRICTED)
        self.assertEqual(obs.outcome, "restricted_clear")
        self.assertFalse(obs.exception_raised)
        self.assertGreater(obs.bytes_written, 0)

    # ------------------------------------------------------------------
    # Timing fields are non-negative
    # ------------------------------------------------------------------

    def test_all_paths_have_non_negative_timing(self):
        for path in RecoveryPath:
            obs = self.probe.measure_path(path)
            self.assertGreaterEqual(obs.kdf_wall_ms, 0.0, msg=path)
            self.assertGreaterEqual(obs.total_wall_ms, 0.0, msg=path)

    def test_total_ms_ge_kdf_ms(self):
        for path in RecoveryPath:
            obs = self.probe.measure_path(path)
            self.assertGreaterEqual(obs.total_wall_ms, obs.kdf_wall_ms, msg=path)

    # ------------------------------------------------------------------
    # Failed path writes no state
    # ------------------------------------------------------------------

    def test_failed_path_writes_no_bytes(self):
        obs = self.probe.measure_path(RecoveryPath.FAILED)
        self.assertEqual(obs.bytes_written, 0)

    # ------------------------------------------------------------------
    # Restricted path writes more than normal (local clear overhead)
    # ------------------------------------------------------------------

    def test_restricted_path_writes_more_than_normal(self):
        normal = self.probe.measure_path(RecoveryPath.NORMAL)
        restricted = self.probe.measure_path(RecoveryPath.RESTRICTED)
        self.assertGreater(restricted.bytes_written, normal.bytes_written)

    # ------------------------------------------------------------------
    # measure_all returns one observation per path
    # ------------------------------------------------------------------

    def test_measure_all_returns_three_observations(self):
        report = self.probe.measure_all()
        self.assertEqual(len(report.observations), 3)

    def test_measure_all_covers_all_path_types(self):
        report = self.probe.measure_all()
        types = {obs.path_type for obs in report.observations}
        self.assertEqual(types, set(RecoveryPath))

    # ------------------------------------------------------------------
    # Multi-run averaging
    # ------------------------------------------------------------------

    def test_measure_path_n_runs_returns_single_observation(self):
        obs = self.probe.measure_path(RecoveryPath.NORMAL, n=3)
        self.assertIsInstance(obs, PathObservation)

    def test_measure_all_n_runs_returns_report(self):
        report = self.probe.measure_all(n=2)
        self.assertIsInstance(report, ObservabilityReport)
        self.assertEqual(len(report.observations), 3)

    # ------------------------------------------------------------------
    # Report summary structure
    # ------------------------------------------------------------------

    def test_report_summary_has_expected_keys(self):
        report = self.probe.measure_all()
        summary = report.summary()
        for path in RecoveryPath:
            self.assertIn(path.value, summary)
            entry = summary[path.value]
            self.assertIn("kdf_wall_ms", entry)
            self.assertIn("total_wall_ms", entry)
            self.assertIn("outcome", entry)
            self.assertIn("bytes_written", entry)
            self.assertIn("exception_raised", entry)

    # ------------------------------------------------------------------
    # Custom KDF injection
    # ------------------------------------------------------------------

    def test_custom_kdf_is_called(self):
        called = []

        def recording_kdf(password: bytes, salt: bytes) -> bytes:
            called.append((password, salt))
            return b"\x00" * 32

        probe = ObservabilityProbe(kdf_fn=recording_kdf)
        probe.measure_all()
        self.assertGreater(len(called), 0)

    # ------------------------------------------------------------------
    # Default (PBKDF2) probe can be instantiated
    # ------------------------------------------------------------------

    def test_default_probe_instantiates(self):
        probe = ObservabilityProbe(pbkdf2_iterations=1)
        obs = probe.measure_path(RecoveryPath.FAILED)
        self.assertEqual(obs.outcome, "auth_failure")


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
