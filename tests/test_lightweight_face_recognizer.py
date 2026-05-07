import os
import sys
import unittest
import unittest.mock

import numpy as np

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

from phasmid.lightweight_face_recognizer import (
    FaceRecognitionResult,
    LightweightFaceRecognizer,
)


def _bgr_frame(h: int = 96, w: int = 96, value: int = 128) -> np.ndarray:
    """Return a plain-colour BGR frame (no real face content)."""
    return np.full((h, w, 3), value, dtype=np.uint8)


def _face_frame() -> np.ndarray:
    """
    Synthesise a minimal frame that passes Haar Cascade detection by
    patching the recogniser's _extract_lbp_histogram directly in tests
    that need a face sample.
    """
    return _bgr_frame()


class TestLightweightFaceRecognizer(unittest.TestCase):
    def setUp(self):
        self.recognizer = LightweightFaceRecognizer()

    def test_not_enrolled_returns_not_enrolled_status(self):
        result = self.recognizer.predict(_bgr_frame())
        self.assertIsInstance(result, FaceRecognitionResult)
        self.assertEqual(result.status, "not_enrolled")
        self.assertFalse(result.face_detected)
        self.assertEqual(result.confidence, 0.0)

    def test_enroll_returns_false_when_no_face_in_frames(self):
        ok = self.recognizer.enroll([_bgr_frame(value=0), _bgr_frame(value=255)])
        self.assertFalse(ok)
        self.assertFalse(self.recognizer.is_enrolled)

    def test_enroll_with_patched_histogram_stores_templates(self):
        hist = np.ones(256, dtype=np.float32) / 256.0
        with unittest.mock.patch.object(
            self.recognizer, "_extract_lbp_histogram", return_value=hist
        ):
            ok = self.recognizer.enroll([_bgr_frame()])
        self.assertTrue(ok)
        self.assertTrue(self.recognizer.is_enrolled)
        self.assertEqual(len(self.recognizer._templates), 1)

    def test_predict_accepted_when_same_histogram(self):
        hist = np.ones(256, dtype=np.float32) / 256.0
        with unittest.mock.patch.object(
            self.recognizer, "_extract_lbp_histogram", return_value=hist
        ):
            self.recognizer.enroll([_bgr_frame()])
            result = self.recognizer.predict(_bgr_frame())
        self.assertEqual(result.status, "accepted")
        self.assertTrue(result.face_detected)
        self.assertGreater(result.confidence, 0.5)

    def test_predict_low_confidence_when_different_histogram(self):
        enroll_hist = np.zeros(256, dtype=np.float32)
        enroll_hist[0] = 1.0
        probe_hist = np.zeros(256, dtype=np.float32)
        probe_hist[255] = 1.0  # completely different distribution

        call_count = [0]

        def patched_extract(frame):
            call_count[0] += 1
            return enroll_hist if call_count[0] == 1 else probe_hist

        with unittest.mock.patch.object(
            self.recognizer, "_extract_lbp_histogram", side_effect=patched_extract
        ):
            self.recognizer.enroll([_bgr_frame()])
            result = self.recognizer.predict(_bgr_frame())

        self.assertEqual(result.status, "low_confidence")
        self.assertTrue(result.face_detected)
        self.assertLess(result.confidence, 0.5)

    def test_predict_no_face_when_extraction_returns_none(self):
        hist = np.ones(256, dtype=np.float32) / 256.0
        with unittest.mock.patch.object(
            self.recognizer, "_extract_lbp_histogram", return_value=hist
        ):
            self.recognizer.enroll([_bgr_frame()])
        with unittest.mock.patch.object(
            self.recognizer, "_extract_lbp_histogram", return_value=None
        ):
            result = self.recognizer.predict(_bgr_frame())
        self.assertEqual(result.status, "no_face")
        self.assertFalse(result.face_detected)

    def test_clear_removes_templates(self):
        hist = np.ones(256, dtype=np.float32) / 256.0
        with unittest.mock.patch.object(
            self.recognizer, "_extract_lbp_histogram", return_value=hist
        ):
            self.recognizer.enroll([_bgr_frame()])
        self.assertTrue(self.recognizer.is_enrolled)
        self.recognizer.clear()
        self.assertFalse(self.recognizer.is_enrolled)

    def test_lbp_histogram_returns_normalised_256bin_array(self):
        face_gray = np.random.randint(0, 256, (64, 64), dtype=np.uint8)
        hist = self.recognizer._lbp_histogram(face_gray)
        self.assertEqual(hist.shape, (256,))
        self.assertAlmostEqual(float(hist.sum()), 1.0, places=5)

    def test_chi_square_distance_zero_for_identical_histograms(self):
        h = np.ones(256, dtype=np.float32) / 256.0
        dist = self.recognizer._chi_square_distance(h, h)
        self.assertAlmostEqual(dist, 0.0, places=5)

    def test_chi_square_distance_positive_for_different_histograms(self):
        h1 = np.zeros(256, dtype=np.float32)
        h1[0] = 1.0
        h2 = np.zeros(256, dtype=np.float32)
        h2[255] = 1.0
        dist = self.recognizer._chi_square_distance(h1, h2)
        self.assertGreater(dist, 0.0)

    def test_distance_to_confidence_zero_distance_gives_max(self):
        conf = self.recognizer._distance_to_confidence(0.0)
        self.assertAlmostEqual(conf, 1.0, places=5)

    def test_distance_to_confidence_clamps_at_zero(self):
        conf = self.recognizer._distance_to_confidence(999.0)
        self.assertEqual(conf, 0.0)

    def test_max_enroll_templates_respected(self):
        hist = np.ones(256, dtype=np.float32) / 256.0
        frames = [_bgr_frame() for _ in range(LightweightFaceRecognizer.MAX_ENROLL_TEMPLATES + 5)]
        with unittest.mock.patch.object(
            self.recognizer, "_extract_lbp_histogram", return_value=hist
        ):
            self.recognizer.enroll(frames)
        self.assertLessEqual(
            len(self.recognizer._templates), LightweightFaceRecognizer.MAX_ENROLL_TEMPLATES
        )


if __name__ == "__main__":
    unittest.main()
