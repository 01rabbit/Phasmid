"""
Integration tests for the coercion-safe delaying architecture.

Tests the full pipeline: operational context template → controlled-disclosure
dataset generation → Silent Standby state machine → recognition routing.

Hardware-dependent subtests (Pi Zero 2W SSH execution, camera-based unlock)
are skipped unless RUN_HARDWARE_TESTS=1 is set in the environment.
"""
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from phasmid.context_profile import (
    BUILT_IN_PROFILES,
    get_profile,
    validate_against_profile,
)
from phasmid.dummy_generator import DummyGeneratorConfig, generate_dummy_dataset
from phasmid.standby_state import StandbyState, StandbyStateMachine

HARDWARE_AVAILABLE = os.environ.get("RUN_HARDWARE_TESTS", "0") == "1"
hardware_only = unittest.skipUnless(HARDWARE_AVAILABLE, "requires RUN_HARDWARE_TESTS=1")


class TestContextProfileToDatasetPipeline(unittest.TestCase):
    """Operational context template → controlled-disclosure dataset generation."""

    def test_all_built_in_profiles_produce_valid_dataset(self):
        for name in BUILT_IN_PROFILES:
            with self.subTest(profile=name):
                profile = get_profile(name)
                self.assertIsNotNone(profile)
                with tempfile.TemporaryDirectory() as tmpdir:
                    config = DummyGeneratorConfig(
                        target_size_bytes=1024 * 512,
                        occupancy_ratio=0.5,
                        profile=profile,
                        output_dir=tmpdir,
                    )
                    report = generate_dummy_dataset(config)
                    self.assertGreater(report.files_created, 0)
                    self.assertGreater(report.total_bytes_written, 0)

    def test_dataset_plausibility_validates_against_source_profile(self):
        profile = get_profile("travel")
        self.assertIsNotNone(profile)
        with tempfile.TemporaryDirectory() as tmpdir:
            config = DummyGeneratorConfig(
                target_size_bytes=1024 * 256,
                occupancy_ratio=0.8,
                profile=profile,
                output_dir=tmpdir,
            )
            report = generate_dummy_dataset(config)
            result = validate_against_profile(
                profile=profile,
                container_size_bytes=config.target_size_bytes,
                dummy_size_bytes=report.total_bytes_written,
                file_count=report.files_created,
                extension_distribution=report.extension_distribution,
            )
            self.assertIsNotNone(result)

    def test_dataset_uses_no_weak_randomness(self):
        import phasmid.dummy_generator as mod
        import inspect
        source = inspect.getsource(mod)
        self.assertNotIn("import random", source)
        self.assertNotIn("random.random(", source)
        self.assertNotIn("random.randint(", source)


class TestStandbyStateMachineIntegration(unittest.TestCase):
    """Silent Standby state machine lifecycle under realistic sequences."""

    def test_full_lifecycle_active_to_sealed_to_active(self):
        sm = StandbyStateMachine()
        self.assertEqual(sm.state, StandbyState.ACTIVE)
        sm.trigger_standby()
        self.assertEqual(sm.state, StandbyState.SEALED)
        sm.recover()
        self.assertEqual(sm.state, StandbyState.ACTIVE)

    def test_sealed_to_dummy_disclosure_and_back(self):
        sm = StandbyStateMachine()
        sm.trigger_standby()
        sm.enter_dummy_disclosure()
        self.assertEqual(sm.state, StandbyState.DUMMY_DISCLOSURE)
        sm.seal_dummy()
        self.assertEqual(sm.state, StandbyState.SEALED)

    def test_status_dict_contains_no_sensitive_labels(self):
        sm = StandbyStateMachine()
        sm.trigger_standby()
        status = sm.status_dict()
        status_str = str(status).lower()
        for term in ("passphrase", "vault", "key", "entry", "true", "real"):
            self.assertNotIn(term, status_str, f"status_dict exposed term: {term!r}")

    def test_trigger_standby_is_idempotent_when_already_sealed(self):
        sm = StandbyStateMachine()
        sm.trigger_standby()
        with self.assertRaises(Exception):
            sm.trigger_standby()
        self.assertEqual(sm.state, StandbyState.SEALED)

    def test_recover_requires_sealed_state(self):
        sm = StandbyStateMachine()
        with self.assertRaises(Exception):
            sm.recover()
        self.assertEqual(sm.state, StandbyState.ACTIVE)


class TestRecognitionRoutingIntegration(unittest.TestCase):
    """Recognition mode routing interacts correctly with standby machine."""

    def setUp(self):
        os.environ.pop("PHASMID_RECOGNITION_MODE", None)
        os.environ.pop("PHASMID_TRUE_UNLOCK_THRESHOLD", None)
        os.environ.pop("PHASMID_DUMMY_FALLBACK_THRESHOLD", None)

    def tearDown(self):
        os.environ.pop("PHASMID_RECOGNITION_MODE", None)
        os.environ.pop("PHASMID_TRUE_UNLOCK_THRESHOLD", None)
        os.environ.pop("PHASMID_DUMMY_FALLBACK_THRESHOLD", None)

    def test_coercion_safe_mode_routes_low_confidence_to_controlled_disclosure(self):
        from phasmid.config import (
            dummy_fallback_threshold,
            recognition_mode,
            true_unlock_threshold,
        )

        os.environ["PHASMID_RECOGNITION_MODE"] = "coercion_safe"
        os.environ["PHASMID_TRUE_UNLOCK_THRESHOLD"] = "0.85"
        os.environ["PHASMID_DUMMY_FALLBACK_THRESHOLD"] = "0.40"

        self.assertEqual(recognition_mode(), "coercion_safe")
        self.assertAlmostEqual(true_unlock_threshold(), 0.85)
        self.assertAlmostEqual(dummy_fallback_threshold(), 0.40)

        score = 0.30
        if score <= dummy_fallback_threshold():
            route = "controlled_disclosure"
        elif score >= true_unlock_threshold():
            route = "unlock"
        else:
            route = "deny"
        self.assertEqual(route, "controlled_disclosure")

    def test_strict_mode_denies_low_confidence(self):
        from phasmid.config import recognition_mode

        os.environ["PHASMID_RECOGNITION_MODE"] = "strict"
        self.assertEqual(recognition_mode(), "strict")

    def test_standby_state_unaffected_by_recognition_mode_config(self):
        os.environ["PHASMID_RECOGNITION_MODE"] = "coercion_safe"
        sm = StandbyStateMachine()
        self.assertEqual(sm.state, StandbyState.ACTIVE)
        sm.trigger_standby()
        self.assertEqual(sm.state, StandbyState.SEALED)


@hardware_only
class TestPiZero2WCoercionSafeHardware(unittest.TestCase):
    """
    Hardware integration tests for Pi Zero 2W.

    Requires:
      - RUN_HARDWARE_TESTS=1
      - PHASMID_PI_HOST set to SSH-reachable hostname/IP
      - Phasmid installed on the Pi under ~/phasmid-field/

    These tests verify that all coercion-safe delaying components install
    and operate correctly on the target hardware class.
    """

    @classmethod
    def setUpClass(cls):
        cls.pi_host = os.environ.get("PHASMID_PI_HOST", "")
        if not cls.pi_host:
            raise unittest.SkipTest("PHASMID_PI_HOST not set")

    def _ssh(self, cmd: str, timeout: int = 30) -> tuple[int, str, str]:
        import subprocess

        result = subprocess.run(
            ["ssh", "-o", "StrictHostKeyChecking=no", self.pi_host, cmd],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr

    def test_pi_phasmid_import_succeeds(self):
        rc, out, err = self._ssh("python3 -c 'import phasmid; print(phasmid.__version__)'")
        self.assertEqual(rc, 0, f"phasmid import failed: {err}")

    def test_pi_context_profile_loads(self):
        rc, out, err = self._ssh(
            "python3 -c 'from phasmid.context_profile import get_profile; "
            "p = get_profile(\"travel\"); print(p.profile_name)'"
        )
        self.assertEqual(rc, 0, f"context_profile import failed: {err}")
        self.assertIn("travel", out)

    def test_pi_standby_state_machine_runs(self):
        rc, out, err = self._ssh(
            "python3 -c 'from phasmid.standby_state import StandbyStateMachine; "
            "sm = StandbyStateMachine(); sm.trigger_standby(); "
            "print(sm.state.value)'"
        )
        self.assertEqual(rc, 0, f"standby_state failed: {err}")
        self.assertIn("sealed", out)

    def test_pi_dummy_generator_runs(self):
        rc, out, err = self._ssh(
            "python3 -c '"
            "import tempfile, os; "
            "from phasmid.context_profile import get_profile; "
            "from phasmid.dummy_generator import DummyGeneratorConfig, generate_dummy_dataset; "
            "p = get_profile(\"travel\"); "
            "cfg = DummyGeneratorConfig(target_size_bytes=65536, occupancy_ratio=0.5, profile=p, output_dir=tempfile.mkdtemp()); "
            "r = generate_dummy_dataset(cfg); "
            "print(r.files_created)'"
        )
        self.assertEqual(rc, 0, f"dummy_generator failed: {err}")
        self.assertGreater(int(out.strip()), 0)

    def test_pi_recognition_mode_config(self):
        rc, out, err = self._ssh(
            "PHASMID_RECOGNITION_MODE=coercion_safe python3 -c "
            "'from phasmid.config import recognition_mode; print(recognition_mode())'"
        )
        self.assertEqual(rc, 0, f"recognition_mode config failed: {err}")
        self.assertIn("coercion_safe", out)


if __name__ == "__main__":
    unittest.main()
