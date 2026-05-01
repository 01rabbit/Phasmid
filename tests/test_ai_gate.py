import os
import sys
import tempfile
import unittest

import numpy as np

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

from phantasm.ai_gate import AIGate


class AIGateTemplateTests(unittest.TestCase):
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
