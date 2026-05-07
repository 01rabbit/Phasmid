import os
import sys
import unittest
import unittest.mock

import numpy as np

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

from phasmid.recognition_benchmark import (
    ComparisonReport,
    FaceBenchmarkSummary,
    ObjectBenchmarkSummary,
    RecognitionBenchmark,
)


def _textured_bgr(h: int = 240, w: int = 320, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    base = rng.integers(0, 256, (h, w, 3), dtype=np.uint8)
    for i in range(0, h, 20):
        base[i, :] = 255
    for j in range(0, w, 20):
        base[:, j] = 255
    return base


def _bgr_frame(value: int = 128) -> np.ndarray:
    return np.full((96, 96, 3), value, dtype=np.uint8)


class TestFaceBenchmarkSummary(unittest.TestCase):
    def _summary(self, accept=3, reject=1, no_face=1):
        return FaceBenchmarkSummary(
            algo="haar+lbp",
            n_enroll_frames=5,
            n_probe_frames=accept + reject + no_face,
            enroll_ok=True,
            accept_count=accept,
            reject_count=reject,
            no_face_count=no_face,
            latency_ms_mean=10.0,
            latency_ms_p50=9.0,
            latency_ms_p95=15.0,
            confidence_mean=0.7,
        )

    def test_accept_rate_correct(self):
        s = self._summary(accept=4, reject=1, no_face=0)
        self.assertAlmostEqual(s.accept_rate, 0.8)

    def test_false_reject_rate_correct(self):
        s = self._summary(accept=3, reject=1, no_face=0)
        self.assertAlmostEqual(s.false_reject_rate, 0.25)

    def test_all_zero_probe_frames_gives_zero_rates(self):
        s = self._summary(accept=0, reject=0, no_face=0)
        self.assertEqual(s.accept_rate, 0.0)
        self.assertEqual(s.false_reject_rate, 0.0)


class TestObjectBenchmarkSummary(unittest.TestCase):
    def _summary(self, accept=4, reject=1, no_desc=0):
        return ObjectBenchmarkSummary(
            algo="orb",
            n_probe_frames=accept + reject + no_desc,
            enroll_ok=True,
            accept_count=accept,
            reject_count=reject,
            no_descriptor_count=no_desc,
            latency_ms_mean=8.0,
            latency_ms_p50=7.5,
            latency_ms_p95=12.0,
            inliers_mean=25.0,
            inliers_p50=24.0,
            confidence_mean=0.8,
        )

    def test_accept_rate_correct(self):
        s = self._summary(accept=4, reject=1, no_desc=0)
        self.assertAlmostEqual(s.accept_rate, 0.8)


class TestRecognitionBenchmark(unittest.TestCase):
    def setUp(self):
        self.benchmark = RecognitionBenchmark()

    def test_face_benchmark_returns_summary(self):
        hist = np.ones(256, dtype=np.float32) / 256.0
        frames = [_bgr_frame() for _ in range(3)]
        recognizer_patch_target = (
            "phasmid.lightweight_face_recognizer.LightweightFaceRecognizer."
            "_extract_lbp_histogram"
        )
        with unittest.mock.patch(recognizer_patch_target, return_value=hist):
            summary = self.benchmark.run_face_benchmark(
                enroll_frames=frames[:1],
                probe_frames=frames,
            )
        self.assertIsInstance(summary, FaceBenchmarkSummary)
        self.assertTrue(summary.enroll_ok)
        self.assertEqual(summary.n_probe_frames, 3)
        self.assertGreaterEqual(summary.latency_ms_mean, 0.0)

    def test_object_benchmark_orb_returns_summary(self):
        frame = _textured_bgr(seed=5)
        summary = self.benchmark.run_object_benchmark(
            reference_frame=frame,
            probe_frames=[frame, frame],
            algo="orb",
        )
        self.assertIsInstance(summary, ObjectBenchmarkSummary)
        self.assertEqual(summary.algo, "orb")
        self.assertEqual(summary.n_probe_frames, 2)
        self.assertGreaterEqual(summary.latency_ms_mean, 0.0)

    def test_object_benchmark_akaze_returns_summary(self):
        frame = _textured_bgr(seed=6)
        summary = self.benchmark.run_object_benchmark(
            reference_frame=frame,
            probe_frames=[frame],
            algo="akaze",
        )
        self.assertIsInstance(summary, ObjectBenchmarkSummary)
        self.assertEqual(summary.algo, "akaze")

    def test_compare_object_algos_returns_comparison_report(self):
        frame = _textured_bgr(seed=10)
        report = self.benchmark.compare_object_algos(
            reference_frame=frame,
            probe_frames=[frame, frame],
        )
        self.assertIsInstance(report, ComparisonReport)
        self.assertIsInstance(report.baseline, ObjectBenchmarkSummary)
        self.assertIsInstance(report.candidate, ObjectBenchmarkSummary)
        self.assertIsInstance(report.recommendation(), str)
        self.assertGreater(len(report.recommendation()), 0)

    def test_face_benchmark_no_face_frames_are_counted(self):
        frames = [_bgr_frame() for _ in range(2)]
        with unittest.mock.patch(
            "phasmid.lightweight_face_recognizer.LightweightFaceRecognizer._extract_lbp_histogram",
            return_value=None,
        ):
            summary = self.benchmark.run_face_benchmark(
                enroll_frames=[_bgr_frame()],
                probe_frames=frames,
            )
        self.assertFalse(summary.enroll_ok)
        self.assertEqual(summary.no_face_count + summary.accept_count + summary.reject_count, 2)


class TestComparisonReport(unittest.TestCase):
    def _make_summary(self, algo, accept, reject, latency_mean):
        return ObjectBenchmarkSummary(
            algo=algo,
            n_probe_frames=accept + reject,
            enroll_ok=True,
            accept_count=accept,
            reject_count=reject,
            no_descriptor_count=0,
            latency_ms_mean=latency_mean,
            latency_ms_p50=latency_mean,
            latency_ms_p95=latency_mean,
            inliers_mean=20.0,
            inliers_p50=20.0,
            confidence_mean=0.8,
        )

    def test_latency_delta_is_computed(self):
        report = ComparisonReport(
            baseline=self._make_summary("orb", 8, 2, 10.0),
            candidate=self._make_summary("akaze", 8, 2, 25.0),
        )
        self.assertAlmostEqual(report.latency_delta_ms, 15.0)

    def test_candidate_acceptable_recommendation(self):
        report = ComparisonReport(
            baseline=self._make_summary("orb", 8, 2, 10.0),
            candidate=self._make_summary("akaze", 8, 2, 20.0),
        )
        self.assertIn("acceptable", report.recommendation())

    def test_candidate_exceeds_latency_budget(self):
        report = ComparisonReport(
            baseline=self._make_summary("orb", 8, 2, 10.0),
            candidate=self._make_summary("akaze", 8, 2, 100.0),
        )
        self.assertIn("latency budget", report.recommendation())


if __name__ == "__main__":
    unittest.main()
