import os
import sys
import unittest
from unittest import mock

import numpy as np

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

from phasmid.object_gate import ObjectGate
from phasmid.object_gate_policy import ObjectGatePolicy
from phasmid.object_model_gate import ObjectModelGateResult


class ObjectGatePolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = ObjectGatePolicy(min_quality_score=0.1)

    def test_no_frame_returns_no_signal(self):
        result = self.policy.combine(
            orb_match=None,
            model_result=ObjectModelGateResult("unavailable", None, 0, "no_frame"),
            quality_score=None,
            attempted_frames=1,
            elapsed_ms=1,
        )
        self.assertEqual(result.state, "no_signal")
        self.assertEqual(result.reason_code, "no_frame")

    def test_low_quality_returns_no_signal(self):
        result = self.policy.combine(
            orb_match=None,
            model_result=ObjectModelGateResult(
                "unavailable", None, 0, "model_unavailable"
            ),
            quality_score=0.01,
            attempted_frames=1,
            elapsed_ms=1,
        )
        self.assertEqual(result.state, "no_signal")
        self.assertEqual(result.reason_code, "low_quality")

    def test_orb_accepted_model_unavailable_accepts(self):
        result = self.policy.combine(
            orb_match={"inliers": 20},
            model_result=ObjectModelGateResult(
                "unavailable", None, 0, "model_unavailable"
            ),
            quality_score=0.5,
            attempted_frames=1,
            elapsed_ms=1,
        )
        self.assertEqual(result.state, "accepted")
        self.assertEqual(result.reason_code, "orb_match")

    def test_orb_accepted_model_rejected_becomes_ambiguous(self):
        result = self.policy.combine(
            orb_match={"inliers": 20},
            model_result=ObjectModelGateResult("rejected", 0.1, 0, "model_reject"),
            quality_score=0.5,
            attempted_frames=1,
            elapsed_ms=1,
        )
        self.assertEqual(result.state, "ambiguous")
        self.assertEqual(result.reason_code, "ambiguous_match")

    def test_orb_rejected_model_accepted_becomes_ambiguous(self):
        result = self.policy.combine(
            orb_match=None,
            model_result=ObjectModelGateResult("accepted", 0.9, 0, "model_match"),
            quality_score=0.5,
            attempted_frames=1,
            elapsed_ms=1,
        )
        self.assertEqual(result.state, "ambiguous")

    def test_orb_rejected_model_unavailable_rejects(self):
        result = self.policy.combine(
            orb_match=None,
            model_result=ObjectModelGateResult(
                "unavailable", None, 0, "model_unavailable"
            ),
            quality_score=0.5,
            attempted_frames=1,
            elapsed_ms=1,
        )
        self.assertEqual(result.state, "rejected")
        self.assertEqual(result.reason_code, "unstable_match")


class ObjectGateTests(unittest.TestCase):
    def test_quality_gate_blocks_blank_frame(self):
        gate = ObjectGate()
        result = gate.evaluate_frame(
            frame=np.zeros((32, 32, 3), dtype=np.uint8),
            orb_match={"inliers": 30},
        )
        self.assertEqual(result.state, "no_signal")
        self.assertEqual(result.reason_code, "low_quality")

    def test_gate_returns_accepted_for_textured_orb_match(self):
        gate = ObjectGate()
        frame = np.zeros((64, 64, 3), dtype=np.uint8)
        frame[::4, :, :] = 255
        frame[:, ::4, :] = 255
        result = gate.evaluate_frame(frame=frame, orb_match={"inliers": 25})
        self.assertEqual(result.state, "accepted")
        self.assertEqual(result.reason_code, "orb_match")

    def test_crypto_not_called_by_object_gate(self):
        gate = ObjectGate()
        frame = np.zeros((64, 64, 3), dtype=np.uint8)
        frame[::4, :, :] = 255
        frame[:, ::4, :] = 255
        with mock.patch("phasmid.local_state_crypto.LocalStateCipher.encrypt") as enc:
            gate.evaluate_frame(frame=frame, orb_match={"inliers": 25})
        enc.assert_not_called()


if __name__ == "__main__":
    unittest.main()
