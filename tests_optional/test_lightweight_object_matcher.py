import os
import sys
import unittest

import numpy as np

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

from phasmid.lightweight_object_matcher import (
    LightweightObjectMatcher,
    ObjectMatchResult,
)


def _textured_bgr(h: int = 240, w: int = 320, seed: int = 0) -> np.ndarray:
    """Return a deterministic pseudo-random BGR frame with enough texture for ORB/AKAZE."""
    rng = np.random.default_rng(seed)
    base = rng.integers(0, 256, (h, w, 3), dtype=np.uint8)
    # Add structured edges so feature detectors find stable keypoints
    for i in range(0, h, 20):
        base[i, :] = 255
    for j in range(0, w, 20):
        base[:, j] = 255
    return base


class TestLightweightObjectMatcher(unittest.TestCase):
    def _make_matcher(self, algo="orb"):
        return LightweightObjectMatcher(
            algo=algo,
            min_reference_kp=5,
            min_frame_descriptors=2,
            min_good_matches=3,
            min_inliers=3,
        )

    # ------------------------------------------------------------------
    # ORB tests
    # ------------------------------------------------------------------

    def test_orb_match_returns_no_reference_before_enroll(self):
        matcher = self._make_matcher("orb")
        result = matcher.match(_textured_bgr())
        self.assertIsInstance(result, ObjectMatchResult)
        self.assertEqual(result.status, "no_reference")
        self.assertFalse(result.matched)
        self.assertEqual(result.algo, "orb")

    def test_orb_enroll_succeeds_on_textured_frame(self):
        matcher = self._make_matcher("orb")
        ok = matcher.enroll_reference(_textured_bgr(seed=1))
        self.assertTrue(ok)
        self.assertTrue(matcher.is_enrolled)

    def test_orb_match_same_frame_is_accepted(self):
        matcher = self._make_matcher("orb")
        frame = _textured_bgr(seed=42)
        self.assertTrue(matcher.enroll_reference(frame))
        result = matcher.match(frame)
        self.assertTrue(result.matched)
        self.assertEqual(result.status, "accepted")
        self.assertGreater(result.inliers, 0)

    def test_orb_clear_resets_reference(self):
        matcher = self._make_matcher("orb")
        matcher.enroll_reference(_textured_bgr())
        self.assertTrue(matcher.is_enrolled)
        matcher.clear()
        self.assertFalse(matcher.is_enrolled)

    def test_orb_match_returns_correct_algo_label(self):
        matcher = self._make_matcher("orb")
        result = matcher.match(_textured_bgr())
        self.assertEqual(result.algo, "orb")

    # ------------------------------------------------------------------
    # AKAZE tests
    # ------------------------------------------------------------------

    def test_akaze_enroll_succeeds_on_textured_frame(self):
        matcher = self._make_matcher("akaze")
        ok = matcher.enroll_reference(_textured_bgr(seed=1))
        self.assertTrue(ok)
        self.assertTrue(matcher.is_enrolled)

    def test_akaze_match_same_frame_is_accepted(self):
        matcher = self._make_matcher("akaze")
        frame = _textured_bgr(seed=42)
        self.assertTrue(matcher.enroll_reference(frame))
        result = matcher.match(frame)
        self.assertTrue(result.matched)
        self.assertEqual(result.status, "accepted")

    def test_akaze_match_returns_correct_algo_label(self):
        matcher = self._make_matcher("akaze")
        result = matcher.match(_textured_bgr())
        self.assertEqual(result.algo, "akaze")

    # ------------------------------------------------------------------
    # Shared behaviour
    # ------------------------------------------------------------------

    def test_confidence_is_zero_when_not_matched(self):
        matcher = self._make_matcher("orb")
        result = matcher.match(_textured_bgr())
        self.assertEqual(result.confidence, 0.0)

    def test_confidence_is_positive_when_matched(self):
        matcher = self._make_matcher("orb")
        frame = _textured_bgr(seed=7)
        matcher.enroll_reference(frame)
        result = matcher.match(frame)
        if result.matched:
            self.assertGreater(result.confidence, 0.0)

    def test_enroll_fails_on_blank_frame(self):
        matcher = self._make_matcher("orb")
        blank = np.zeros((240, 320, 3), dtype=np.uint8)
        ok = matcher.enroll_reference(blank)
        self.assertFalse(ok)

    def test_match_on_blank_frame_returns_no_descriptors_or_low_inliers(self):
        matcher = self._make_matcher("orb")
        frame = _textured_bgr(seed=99)
        self.assertTrue(matcher.enroll_reference(frame))
        blank = np.zeros((240, 320, 3), dtype=np.uint8)
        result = matcher.match(blank)
        self.assertFalse(result.matched)
        self.assertIn(result.status, ("no_descriptors", "low_inliers"))


if __name__ == "__main__":
    unittest.main()
