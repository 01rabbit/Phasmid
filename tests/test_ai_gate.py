import inspect
import os
import sys
import tempfile
import unittest
from unittest import mock

import numpy as np

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

from phasmid import strings as text
from phasmid.ai_gate import AIGate
from phasmid.camera_frame_source import CameraFrameSource
from phasmid.local_state_crypto import LocalStateCipher
from phasmid.object_cue_matcher import ObjectCueMatcher


class AIGateTemplateTests(unittest.TestCase):
    def test_camera_frame_source_release_is_idempotent(self):
        source = CameraFrameSource(frame_size=(640, 480))
        source.release()
        self.assertIsNone(source.cap)

    def test_object_cue_matcher_provides_empty_reference_shape(self):
        matcher = ObjectCueMatcher(
            min_reference_keypoints=60,
            min_frame_descriptors=10,
            min_good_matches=50,
            min_inliers=30,
        )
        empty = matcher.empty_reference()
        self.assertEqual(
            empty,
            {"kp": None, "des": None, "shape": None, "pts": None, "path": None},
        )

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
            with (
                mock.patch.object(
                    gate,
                    "_best_reference_state_from_recent_frames",
                    return_value=candidate,
                ),
                mock.patch.object(gate, "_references_too_similar", return_value=True),
            ):
                success, message = gate.capture_reference(gate.MODES[0])

            self.assertFalse(success)
            self.assertEqual(message, text.AI_GATE_CUES_TOO_SIMILAR)
            self.assertNotRegex(message.lower(), r"\b(key|mode|dummy|secret)\b")

    def test_camera_overlay_text_is_neutral(self):
        source = inspect.getsource(AIGate._draw_match_status)
        self.assertIn("text.AI_GATE_OBJECT_MATCHED", source)
        self.assertIn("text.AI_GATE_AMBIGUOUS_CUE", source)
        self.assertIn("text.AI_GATE_NO_MATCH", source)
        self.assertIn("text.AI_GATE_PRESENT_OBJECT", source)
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

            gate._write_reference_blob(
                {"dummy": state, "secret": gate._empty_reference()}
            )

            self.assertTrue(os.path.exists(gate.state_blob_path))
            self.assertFalse(
                os.path.exists(os.path.join(tmp, "reference_key_dummy.npz"))
            )
            self.assertFalse(
                os.path.exists(os.path.join(tmp, "reference_key_secret.npz"))
            )

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

    def test_get_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            gate = AIGate(reference_dir=tmp)
            status = gate.get_status()
            self.assertFalse(status["object_detected"])
            self.assertEqual(status["matched_mode"], "none")
            self.assertFalse(status["registered_modes"]["dummy"])
            self.assertFalse(status["registered_modes"]["secret"])

    def test_clear_references(self):
        with tempfile.TemporaryDirectory() as tmp:
            gate = AIGate(reference_dir=tmp)
            # Mock a registered state
            gate.reference_data["dummy"]["des"] = np.ones((10, 32), dtype=np.uint8)
            success, msg = gate.clear_references()
            self.assertTrue(success)
            self.assertFalse(gate.reference_data["dummy"]["des"] is not None)
            # The blob file should exist but represent an empty state
            self.assertTrue(os.path.exists(gate.state_blob_path))
            loaded = gate._read_reference_blob()
            self.assertIsNone(loaded["dummy"]["des"])

    def test_get_auth_sequence(self):
        with tempfile.TemporaryDirectory() as tmp:
            gate = AIGate(reference_dir=tmp)
            seq = gate.get_auth_sequence(length=2)
            self.assertEqual(seq, ["none", "none"])

            gate.last_match_mode = "dummy"
            seq = gate.get_auth_sequence(length=3)
            self.assertEqual(seq, ["reference_dummy_matched"] * 3)

    def test_state_encryption_key_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            gate = AIGate(reference_dir=tmp)
            secret = "my_custom_secret"
            with mock.patch.dict(os.environ, {"PHASMID_STATE_SECRET": secret}):
                key = gate._state_encryption_key()
                import hashlib

                expected = hashlib.sha256(secret.encode("utf-8")).digest()
                self.assertEqual(key, expected)

    def test_read_encrypted_template_error_handling(self):
        with tempfile.TemporaryDirectory() as tmp:
            gate = AIGate(reference_dir=tmp)
            blob_path = os.path.join(tmp, "bad_blob")
            with open(blob_path, "wb") as f:
                f.write(os.urandom(10))  # Too short

            with self.assertRaisesRegex(ValueError, "too short"):
                gate._read_encrypted_template(blob_path)

            with open(blob_path, "wb") as f:
                f.write(os.urandom(20))  # Random data, tag mismatch

            with self.assertRaisesRegex(ValueError, "authentication failed"):
                gate._read_encrypted_template(blob_path)

    def test_match_reference_state_none_cases(self):
        with tempfile.TemporaryDirectory() as tmp:
            gate = AIGate(reference_dir=tmp)
            res = gate._match_reference_state(gate._empty_reference(), None)
            self.assertIsNone(res)

            state = {
                "des": np.ones((10, 32), dtype=np.uint8),
                "kp": [object()] * 10,
                "pts": np.zeros((4, 1, 2), dtype=np.float32),
            }
            res = gate._match_reference_state(state, None)  # frame_gray is None
            self.assertIsNone(res)

    def test_sequence_for_mode_invalid(self):
        gate = AIGate()
        with self.assertRaises(ValueError):
            gate.sequence_for_mode("invalid")

    def test_ai_gate_delegates_gray_conversion_to_matcher(self):
        with tempfile.TemporaryDirectory() as tmp:
            gate = AIGate(reference_dir=tmp)
            frame = np.zeros((4, 4, 3), dtype=np.uint8)
            expected = np.zeros((4, 4), dtype=np.uint8)
            with mock.patch.object(
                gate.matcher, "to_gray", return_value=expected
            ) as to_gray:
                result = gate._to_gray(frame)
            to_gray.assert_called_once_with(frame)
            self.assertIs(result, expected)

    def test_ai_gate_close_releases_camera_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            gate = AIGate(reference_dir=tmp)
            with mock.patch.object(gate.camera, "release") as release:
                gate.close()
            release.assert_called_once_with()

    def test_local_state_cipher_domain_separates_local_key_material(self):
        with tempfile.TemporaryDirectory() as tmp:
            key_path = os.path.join(tmp, "lock.bin")
            with open(key_path, "wb") as handle:
                handle.write(b"k" * 32)

            plain = LocalStateCipher(state_key_path=key_path, aad=b"plain")
            scoped = LocalStateCipher(
                state_key_path=key_path,
                aad=b"scoped",
                local_key_suffix=b":face-ui-lock",
            )

            self.assertEqual(plain.encryption_key(), b"k" * 32)
            self.assertNotEqual(plain.encryption_key(), scoped.encryption_key())


if __name__ == "__main__":
    unittest.main()
