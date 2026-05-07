import os
import sys
import unittest

import numpy as np

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

from phasmid.object_model_gate import ObjectModelGate


class _AcceptedBackend:
    def score_frame(self, frame: np.ndarray) -> float | None:
        return 0.91


class _RejectedBackend:
    def score_frame(self, frame: np.ndarray) -> float | None:
        return 0.22


class _FailingBackend:
    def score_frame(self, frame: np.ndarray) -> float | None:
        raise RuntimeError("backend failed")


class ObjectModelGateTests(unittest.TestCase):
    def test_model_unavailable_without_backend(self):
        gate = ObjectModelGate()
        result = gate.evaluate_frame(np.zeros((8, 8, 3), dtype=np.uint8))
        self.assertEqual(result.state, "unavailable")
        self.assertEqual(result.reason_code, "model_unavailable")

    def test_model_accepts_when_score_exceeds_threshold(self):
        gate = ObjectModelGate(backend=_AcceptedBackend())
        result = gate.evaluate_frame(np.zeros((8, 8, 3), dtype=np.uint8))
        self.assertEqual(result.state, "accepted")
        self.assertEqual(result.reason_code, "model_match")

    def test_model_rejects_when_score_below_threshold(self):
        gate = ObjectModelGate(backend=_RejectedBackend())
        result = gate.evaluate_frame(np.zeros((8, 8, 3), dtype=np.uint8))
        self.assertEqual(result.state, "rejected")
        self.assertEqual(result.reason_code, "model_reject")

    def test_model_errors_neutrally(self):
        gate = ObjectModelGate(backend=_FailingBackend())
        result = gate.evaluate_frame(np.zeros((8, 8, 3), dtype=np.uint8))
        self.assertEqual(result.state, "error")
        self.assertEqual(result.reason_code, "model_error")


if __name__ == "__main__":
    unittest.main()
