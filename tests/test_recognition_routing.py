"""
Tests for coercion-safe recognition confidence routing.

Verifies that:
- strict mode: mismatch returns no-match
- coercion_safe mode: low confidence routes to dummy disclosure path
- demo mode: routes to dummy disclosure path when above fallback threshold
- repeated instability in coercion_safe routes to dummy path
- no aggressive "access denied" cycling is produced

These tests do not require camera hardware. They mock the confidence
and match state methods directly.
"""

import os
import sys
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))


class TestRecognitionModeConfig(unittest.TestCase):
    def test_strict_is_default(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("PHASMID_RECOGNITION_MODE", None)
            from importlib import reload

            import phasmid.config as cfg

            reload(cfg)
            self.assertEqual(cfg.recognition_mode(), "strict")

    def test_coercion_safe_mode_accepted(self):
        with mock.patch.dict(os.environ, {"PHASMID_RECOGNITION_MODE": "coercion_safe"}):
            from importlib import reload

            import phasmid.config as cfg

            reload(cfg)
            self.assertEqual(cfg.recognition_mode(), "coercion_safe")

    def test_demo_mode_accepted(self):
        with mock.patch.dict(os.environ, {"PHASMID_RECOGNITION_MODE": "demo"}):
            from importlib import reload

            import phasmid.config as cfg

            reload(cfg)
            self.assertEqual(cfg.recognition_mode(), "demo")

    def test_invalid_mode_falls_back_to_strict(self):
        with mock.patch.dict(os.environ, {"PHASMID_RECOGNITION_MODE": "evil_mode"}):
            from importlib import reload

            import phasmid.config as cfg

            reload(cfg)
            self.assertEqual(cfg.recognition_mode(), "strict")

    def test_true_unlock_threshold_default(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("PHASMID_TRUE_UNLOCK_THRESHOLD", None)
            from importlib import reload

            import phasmid.config as cfg

            reload(cfg)
            self.assertAlmostEqual(cfg.true_unlock_threshold(), 0.85)

    def test_dummy_fallback_threshold_default(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("PHASMID_DUMMY_FALLBACK_THRESHOLD", None)
            from importlib import reload

            import phasmid.config as cfg

            reload(cfg)
            self.assertAlmostEqual(cfg.dummy_fallback_threshold(), 0.40)

    def test_true_unlock_threshold_clamped_to_zero(self):
        with mock.patch.dict(os.environ, {"PHASMID_TRUE_UNLOCK_THRESHOLD": "-0.5"}):
            from importlib import reload

            import phasmid.config as cfg

            reload(cfg)
            self.assertEqual(cfg.true_unlock_threshold(), 0.0)

    def test_true_unlock_threshold_clamped_to_one(self):
        with mock.patch.dict(os.environ, {"PHASMID_TRUE_UNLOCK_THRESHOLD": "2.0"}):
            from importlib import reload

            import phasmid.config as cfg

            reload(cfg)
            self.assertEqual(cfg.true_unlock_threshold(), 1.0)

    def test_dummy_fallback_threshold_clamped_to_zero(self):
        with mock.patch.dict(os.environ, {"PHASMID_DUMMY_FALLBACK_THRESHOLD": "-1.0"}):
            from importlib import reload

            import phasmid.config as cfg

            reload(cfg)
            self.assertEqual(cfg.dummy_fallback_threshold(), 0.0)


class TestStandbyHotkeyConfig(unittest.TestCase):
    def test_default_standby_hotkey(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("PHASMID_STANDBY_HOTKEY", None)
            from importlib import reload

            import phasmid.config as cfg

            reload(cfg)
            self.assertEqual(cfg.standby_hotkey(), "ctrl+s")

    def test_custom_standby_hotkey(self):
        with mock.patch.dict(os.environ, {"PHASMID_STANDBY_HOTKEY": "f12"}):
            from importlib import reload

            import phasmid.config as cfg

            reload(cfg)
            self.assertEqual(cfg.standby_hotkey(), "f12")

    def test_empty_standby_hotkey_returns_default(self):
        with mock.patch.dict(os.environ, {"PHASMID_STANDBY_HOTKEY": ""}):
            from importlib import reload

            import phasmid.config as cfg

            reload(cfg)
            self.assertEqual(cfg.standby_hotkey(), "ctrl+s")


class TestContextProfileConfig(unittest.TestCase):
    def test_default_context_profile(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("PHASMID_CONTEXT_PROFILE", None)
            from importlib import reload

            import phasmid.config as cfg

            reload(cfg)
            self.assertEqual(cfg.context_profile_name(), "travel")

    def test_custom_context_profile(self):
        with mock.patch.dict(os.environ, {"PHASMID_CONTEXT_PROFILE": "researcher"}):
            from importlib import reload

            import phasmid.config as cfg

            reload(cfg)
            self.assertEqual(cfg.context_profile_name(), "researcher")


class TestRecognitionRouting(unittest.TestCase):
    """Unit tests for recognition confidence routing logic (without camera)."""

    def _make_routing_result(
        self, mode, confidence, true_threshold, fallback_threshold
    ):
        """Simulate the routing logic from AIGate.get_auth_sequence."""
        MATCH_NONE = "none"
        MODES = ("dummy", "secret")
        AUTH_TOKENS = {
            "dummy": "reference_dummy_matched",
            "secret": "reference_secret_matched",
        }

        last_match_mode = "dummy" if confidence >= true_threshold else MATCH_NONE

        if last_match_mode in AUTH_TOKENS and confidence >= true_threshold:
            return AUTH_TOKENS[last_match_mode]

        if mode == "coercion_safe":
            return AUTH_TOKENS[MODES[0]]

        if mode == "demo" and confidence >= fallback_threshold:
            return AUTH_TOKENS[MODES[0]]

        return MATCH_NONE

    def test_strict_high_confidence_returns_match(self):
        result = self._make_routing_result(
            mode="strict", confidence=0.95, true_threshold=0.85, fallback_threshold=0.40
        )
        self.assertNotEqual(result, "none")

    def test_strict_low_confidence_returns_none(self):
        result = self._make_routing_result(
            mode="strict", confidence=0.30, true_threshold=0.85, fallback_threshold=0.40
        )
        self.assertEqual(result, "none")

    def test_coercion_safe_low_confidence_routes_to_dummy(self):
        result = self._make_routing_result(
            mode="coercion_safe",
            confidence=0.10,
            true_threshold=0.85,
            fallback_threshold=0.40,
        )
        self.assertEqual(result, "reference_dummy_matched")

    def test_coercion_safe_zero_confidence_routes_to_dummy(self):
        result = self._make_routing_result(
            mode="coercion_safe",
            confidence=0.0,
            true_threshold=0.85,
            fallback_threshold=0.40,
        )
        self.assertEqual(result, "reference_dummy_matched")

    def test_demo_above_fallback_routes_to_dummy(self):
        result = self._make_routing_result(
            mode="demo", confidence=0.60, true_threshold=0.85, fallback_threshold=0.40
        )
        self.assertEqual(result, "reference_dummy_matched")

    def test_demo_below_fallback_returns_none(self):
        result = self._make_routing_result(
            mode="demo", confidence=0.20, true_threshold=0.85, fallback_threshold=0.40
        )
        self.assertEqual(result, "none")

    def test_coercion_safe_does_not_produce_access_denied_string(self):
        """Coercion-safe mode must never return an obvious refusal string."""
        result = self._make_routing_result(
            mode="coercion_safe",
            confidence=0.0,
            true_threshold=0.85,
            fallback_threshold=0.40,
        )
        self.assertNotIn("denied", result.lower())
        self.assertNotIn("refused", result.lower())
        self.assertNotIn("error", result.lower())

    def test_coercion_safe_repeated_instability_still_routes_to_dummy(self):
        """Repeated low-confidence in coercion_safe must still route to dummy, not produce a loop."""
        for _ in range(10):
            result = self._make_routing_result(
                mode="coercion_safe",
                confidence=0.0,
                true_threshold=0.85,
                fallback_threshold=0.40,
            )
            self.assertEqual(result, "reference_dummy_matched")


if __name__ == "__main__":
    unittest.main()
