import io
import os
import threading
import time

import cv2
import numpy as np

from . import strings as text
from .camera_frame_source import CameraFrameSource
from .config import STATE_BLOB_NAME, STATE_KEY_NAME, state_dir
from .local_state_crypto import LocalStateCipher
from .object_cue_matcher import ObjectCueMatcher


class AIGate:
    # Legacy internal identifiers are retained for vault compatibility only.
    # They must never be emitted to UI, API responses, overlays, CLI output,
    # default logs, documentation examples, or user-visible errors.
    MODES = ("dummy", "secret")
    AUTH_TOKENS = {
        "dummy": "reference_dummy_matched",
        "secret": "reference_secret_matched",
    }
    MATCH_NONE = "none"
    MATCH_AMBIGUOUS = "ambiguous"
    MIN_REFERENCE_KEYPOINTS = 60
    MIN_FRAME_DESCRIPTORS = 10
    MIN_GOOD_MATCHES = 50
    MIN_INLIERS = 30
    FRAME_SIZE = (640, 480)
    MATCH_HISTORY_FRAMES = 5
    MATCH_HISTORY_REQUIRED = 3
    REFERENCE_CAPTURE_SAMPLES = 3
    TARGET_FPS = 5

    def __init__(self, reference_dir=None):
        self._stop_event = threading.Event()
        self.lock = threading.Lock()
        self.latest_frame = None

        self.reference_dir = reference_dir or state_dir()
        os.makedirs(self.reference_dir, mode=0o700, exist_ok=True)
        try:
            os.chmod(self.reference_dir, 0o700)
        except OSError:
            pass
        self.state_blob_path = os.path.join(self.reference_dir, STATE_BLOB_NAME)
        self.state_key_path = os.path.join(self.reference_dir, STATE_KEY_NAME)
        self.state_cipher = LocalStateCipher(
            state_key_path=self.state_key_path,
            aad=self._template_aad(self.state_blob_path),
        )

        self.object_detected = False
        self.last_match_mode = self.MATCH_NONE
        self.match_states = {mode: False for mode in self.MODES}
        self.match_history = []

        self.matcher = ObjectCueMatcher(
            min_reference_keypoints=self.MIN_REFERENCE_KEYPOINTS,
            min_frame_descriptors=self.MIN_FRAME_DESCRIPTORS,
            min_good_matches=self.MIN_GOOD_MATCHES,
            min_inliers=self.MIN_INLIERS,
        )
        self.camera = CameraFrameSource(frame_size=self.FRAME_SIZE)

        self.reference_data = {mode: self._empty_reference() for mode in self.MODES}
        self._load_references()

        self._thread = None

    def _empty_reference(self):
        return self.matcher.empty_reference()

    def _validate_mode(self, mode):
        if mode not in self.MODES:
            raise ValueError("unsupported local entry")

    def _reference_state_from_image(self, image):
        return self.matcher.reference_state_from_image(image)

    def _to_gray(self, image):
        return self.matcher.to_gray(image)

    def _reference_state_from_arrays(self, des, kp_data, shape):
        state = self.matcher.reference_state_from_arrays(des, kp_data, shape)
        if state["des"] is not None:
            state["path"] = self.state_blob_path
        return state

    def _load_references(self):
        with self.lock:
            self.reference_data = self._read_reference_blob()

    def _match_reference_state(self, ref_state, frame_gray):
        return self.matcher.match_reference_state(ref_state, frame_gray)

    def _match_descriptors(self, ref_state, kp, des):
        return self.matcher.match_descriptors(ref_state, kp, des)

    def _references_too_similar(self, mode, candidate_state):
        other_mode = "secret" if mode == "dummy" else "dummy"
        other_state = self.reference_data[other_mode]
        if other_state["des"] is None:
            return False

        return (
            self._match_descriptors(
                candidate_state, other_state["kp"], other_state["des"]
            )
            is not None
        )

    def _state_to_arrays(self, state):
        kp_data = np.array(
            [
                [
                    point.pt[0],
                    point.pt[1],
                    point.size,
                    point.angle,
                    point.response,
                    point.octave,
                    point.class_id,
                ]
                for point in state["kp"]
            ],
            dtype=np.float32,
        )
        return {
            "des": state["des"],
            "kp": kp_data,
            "shape": np.array(state["shape"], dtype=np.int32),
        }

    def _write_reference_blob(self, references):
        template = io.BytesIO()
        payload = {}
        for mode in self.MODES:
            state = references.get(mode) or self._empty_reference()
            if state["des"] is None:
                payload[f"{mode}_present"] = np.array([0], dtype=np.uint8)
                payload[f"{mode}_des"] = np.empty((0, 32), dtype=np.uint8)
                payload[f"{mode}_kp"] = np.empty((0, 7), dtype=np.float32)
                payload[f"{mode}_shape"] = np.array([0, 0], dtype=np.int32)
                continue
            arrays = self._state_to_arrays(state)
            payload[f"{mode}_present"] = np.array([1], dtype=np.uint8)
            payload[f"{mode}_des"] = arrays["des"]
            payload[f"{mode}_kp"] = arrays["kp"]
            payload[f"{mode}_shape"] = arrays["shape"]

        np.savez_compressed(
            template,
            **payload,
        )
        encrypted = self._encrypt_template(template.getvalue(), self.state_blob_path)
        with open(self.state_blob_path, "wb") as handle:
            handle.write(encrypted)
        try:
            os.chmod(self.state_blob_path, 0o600)
        except OSError:
            pass

    def _read_reference_blob(self):
        references = {mode: self._empty_reference() for mode in self.MODES}
        if not os.path.exists(self.state_blob_path):
            return references

        try:
            with np.load(
                io.BytesIO(self._read_encrypted_template(self.state_blob_path)),
                allow_pickle=False,
            ) as template:
                for mode in self.MODES:
                    if int(template[f"{mode}_present"][0]) != 1:
                        continue
                    references[mode] = self._reference_state_from_arrays(
                        template[f"{mode}_des"],
                        template[f"{mode}_kp"],
                        template[f"{mode}_shape"],
                    )
        except Exception:
            return {mode: self._empty_reference() for mode in self.MODES}
        return references

    def _encrypt_template(self, plaintext, path):
        return self.state_cipher.encrypt(plaintext)

    def _read_encrypted_template(self, path):
        with open(path, "rb") as handle:
            data = handle.read()
        return self.state_cipher.decrypt(
            data,
            too_short_message="reference template is too short",
            auth_failed_message="reference template authentication failed",
        )

    def _state_encryption_key(self):
        return self.state_cipher.encryption_key()

    def _load_or_create_local_state_key(self):
        return self.state_cipher._load_or_create_local_state_key()

    def _template_aad(self, path):
        return f"phasmid-reference-state:{os.path.basename(path)}".encode("utf-8")

    def _update_match_result(self, matches):
        active_modes = [mode for mode, result in matches.items() if result is not None]
        self.match_history.append(tuple(active_modes))
        self.match_history = self.match_history[-self.MATCH_HISTORY_FRAMES :]

        stable_modes = []
        for mode in self.MODES:
            count = sum(1 for active in self.match_history if mode in active)
            if count >= self.MATCH_HISTORY_REQUIRED:
                stable_modes.append(mode)

        active_modes = stable_modes
        if not active_modes:
            self.last_match_mode = self.MATCH_NONE
            self.object_detected = False
            self.match_states = {mode: False for mode in self.MODES}
            return

        if len(active_modes) > 1:
            self.last_match_mode = self.MATCH_AMBIGUOUS
            self.object_detected = False
            self.match_states = {mode: True for mode in active_modes}
            for mode in self.MODES:
                if mode not in active_modes:
                    self.match_states[mode] = False
            return

        matched_mode = active_modes[0]
        self.last_match_mode = matched_mode
        self.object_detected = True
        self.match_states = {mode: mode == matched_mode for mode in self.MODES}

    def sequence_for_mode(self, mode, length=1):
        self._validate_mode(mode)
        return [self.AUTH_TOKENS[mode]] * length

    def get_auth_sequence(self, length=1):
        if self.last_match_mode in self.AUTH_TOKENS:
            return self.sequence_for_mode(self.last_match_mode, length=length)
        return [self.MATCH_NONE] * length

    def capture_reference(self, mode):
        self._validate_mode(mode)
        if self.latest_frame is None:
            return False, text.AI_GATE_NO_FRAME

        candidate_state = self._best_reference_state_from_recent_frames()
        if candidate_state is None:
            return False, text.AI_GATE_IMAGE_TOO_SIMPLE

        if self._references_too_similar(mode, candidate_state):
            return (
                False,
                text.AI_GATE_CUES_TOO_SIMILAR,
            )

        try:
            updated_references = dict(self.reference_data)
            updated_references[mode] = candidate_state
            self._write_reference_blob(updated_references)
        except OSError:
            return False, text.AI_GATE_SAVE_FAILED

        candidate_state["path"] = self.state_blob_path
        with self.lock:
            self.reference_data[mode] = candidate_state
            self.last_match_mode = self.MATCH_NONE
            self.object_detected = False
            self.match_states = {ref_mode: False for ref_mode in self.MODES}
            self.match_history = []

        return True, text.AI_GATE_OBJECT_MATCHED

    def _best_reference_state_from_recent_frames(self):
        candidates = []
        for _ in range(self.REFERENCE_CAPTURE_SAMPLES):
            with self.lock:
                frame = None if self.latest_frame is None else self.latest_frame.copy()
            state = self._reference_state_from_image(frame)
            if state is not None:
                candidates.append(state)
            time.sleep(0.12)

        if not candidates:
            return None
        return max(candidates, key=lambda state: len(state["kp"]))

    def get_status(self):
        return {
            "object_detected": self.object_detected,
            "matched_mode": self.last_match_mode,
            "match_states": dict(self.match_states),
            "registered_modes": {
                mode: self.reference_data[mode]["des"] is not None
                for mode in self.MODES
            },
        }

    def clear_references(self):
        empty = {mode: self._empty_reference() for mode in self.MODES}
        try:
            self._write_reference_blob(empty)
        except OSError:
            return False, text.AI_GATE_CLEAR_FAILED

        with self.lock:
            self.reference_data = empty
            self.last_match_mode = self.MATCH_NONE
            self.object_detected = False
            self.match_states = {mode: False for mode in self.MODES}
            self.match_history = []

        return True, text.AI_GATE_CUES_CLEARED

    def _draw_match_status(self, image):
        h, w, _ = image.shape
        cv2.rectangle(image, (0, 0), (w, 50), (0, 0, 0), -1)
        cv2.putText(
            image,
            text.AI_GATE_ACTIVE,
            (20, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 165, 255),
            2,
        )

        if self.last_match_mode in self.AUTH_TOKENS:
            cv2.circle(image, (w - 15, 15), 8, (0, 255, 0), -1)
            cv2.putText(
                image,
                text.AI_GATE_MATCH,
                (w - 80, 28),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2,
            )
            cv2.rectangle(image, (5, 55), (w - 5, h - 5), (0, 255, 0), 3)
            cv2.putText(
                image,
                text.AI_GATE_OBJECT_MATCHED,
                (15, 75),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2,
            )
            cv2.putText(
                image,
                text.AI_GATE_OBJECT_DETECTED,
                (15, 100),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                1,
            )
            return

        if self.last_match_mode == self.MATCH_AMBIGUOUS:
            cv2.circle(image, (w - 15, 15), 8, (0, 165, 255), -1)
            cv2.putText(
                image,
                text.AI_GATE_AMBIGUOUS,
                (w - 85, 28),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 165, 255),
                2,
            )
            cv2.rectangle(image, (5, 55), (w - 5, h - 5), (0, 165, 255), 3)
            cv2.putText(
                image,
                text.AI_GATE_AMBIGUOUS_CUE,
                (15, 75),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 165, 255),
                2,
            )
            cv2.putText(
                image,
                text.AI_GATE_CUES_TOO_SIMILAR,
                (15, 100),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 165, 255),
                1,
            )
            return

        cv2.putText(
            image,
            text.AI_GATE_NO_MATCH,
            (15, 75),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (100, 100, 255),
            2,
        )
        cv2.putText(
            image,
            text.AI_GATE_PRESENT_OBJECT,
            (15, 100),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (100, 100, 255),
            1,
        )

    def generate_frames(self):
        frame_delay = 1.0 / self.TARGET_FPS
        while not self._stop_event.is_set():
            loop_start = time.time()
            success, frame = self.camera.read()
            if not success:
                continue

            with self.lock:
                self.latest_frame = frame.copy()
                reference_data = {
                    mode: dict(state) for mode, state in self.reference_data.items()
                }

            image = cv2.flip(frame, 1)

            processed_gray = self._to_gray(frame)
            matches = {
                mode: self._match_reference_state(state, processed_gray)
                for mode, state in reference_data.items()
            }
            self._update_match_result(matches)
            self._draw_match_status(image)

            ok, buffer = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if not ok:
                continue

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
            )

            elapsed = time.time() - loop_start
            if elapsed < frame_delay:
                time.sleep(frame_delay - elapsed)

    def close(self):
        self._stop_event.set()
        self.camera.release()
        if self._thread:
            self._thread.join()
            self._thread = None

    def start(self):
        if self._thread is None:
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._generate_loop, daemon=True)
            self._thread.start()

    def _generate_loop(self):
        for _ in self.generate_frames():
            pass


def get_gesture_sequence(length=1):
    return gate.get_auth_sequence(length=length)


gate = AIGate()
