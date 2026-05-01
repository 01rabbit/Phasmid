import os
import inspect
import sys
import tempfile
import unittest
from unittest import mock

import numpy as np

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

from phantasm.ai_gate import AIGate


class AIGateTemplateTests(unittest.TestCase):
    def test_capture_similarity_message_is_neutral(self):
        with tempfile.TemporaryDirectory() as tmp:
            gate = AIGate(reference_dir=tmp)
            gate.latest_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            candidate = {
                "kp": [object()] * gate.MIN_REFERENCE_KEYPOINTS,
                "des": np.ones((gate.MIN_REFERENCE_KEYPOINTS, 32), dtype=np.uint8),
                "shape": (480, 640),
                "pts": np.zeros((4, 1, 2), dtype=np.float32),
                "path": None,
            }
            with mock.patch.object(gate, "_best_reference_state_from_recent_frames", return_value=candidate), \
                 mock.patch.object(gate, "_references_too_similar", return_value=True):
                success, message = gate.capture_reference(gate.MODES[0])

            self.assertFalse(success)
            self.assertIn("existing access cue", message)
            self.assertNotRegex(message.lower(), r"\b(key|mode|dummy|secret)\b")

    def test_camera_overlay_text_is_neutral(self):
        source = inspect.getsource(AIGate._draw_match_status)
        self.assertIn("Object cue matched", source)
        self.assertIn("Ambiguous object cue", source)
        self.assertIn("No object cue match", source)
        self.assertNotIn("IMAGE KEY", source)
        self.assertNotIn("Registered keys", source)
        self.assertNotIn("No reference match", source)

    def test_reference_template_is_encrypted_at_rest(self):
        with tempfile.TemporaryDirectory() as tmp:
            gate = AIGate(reference_dir=tmp)
            rng = np.random.default_rng(123)
            image = rng.integers(0, 255, size=(480, 640, 3), dtype=np.uint8)
            state = gate._reference_state_from_image(image)
            self.assertIsNotNone(state)

            gate._write_reference_blob({"dummy": state, "secret": gate._empty_reference()})

            self.assertTrue(os.path.exists(gate.state_blob_path))
            self.assertFalse(os.path.exists(os.path.join(tmp, "reference_key_dummy.npz")))
            self.assertFalse(os.path.exists(os.path.join(tmp, "reference_key_secret.npz")))

            with open(gate.state_blob_path, "rb") as handle:
                raw = handle.read()
            self.assertNotIn(b"PK", raw[:4])
            self.assertGreater(len(raw), 12)

            loaded = gate._read_reference_blob()["dummy"]
            self.assertIsNotNone(loaded["des"])
            self.assertGreaterEqual(len(loaded["kp"]), gate.MIN_REFERENCE_KEYPOINTS)

    def test_match_history_requires_stable_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            gate = AIGate(reference_dir=tmp)
            match = {"dummy": {"inliers": 99}, "secret": None}
            miss = {"dummy": None, "secret": None}

            gate._update_match_result(match)
            self.assertEqual(gate.last_match_mode, gate.MATCH_NONE)
            gate._update_match_result(miss)
            gate._update_match_result(match)
            self.assertEqual(gate.last_match_mode, gate.MATCH_NONE)
            gate._update_match_result(match)

            self.assertEqual(gate.last_match_mode, "dummy")


if __name__ == "__main__":
    unittest.main()
