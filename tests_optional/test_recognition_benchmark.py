import os
import sys
import unittest
import unittest.mock

import numpy as np

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

from phasmid.recognition_benchmark import (
    ComparisonReport,
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
