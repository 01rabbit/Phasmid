import hashlib
import io
import os
import time

import cv2
import numpy as np
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .config import FACE_TEMPLATE_NAME, STATE_KEY_NAME, state_dir


class FaceUILock:
    FACE_SIZE = (96, 96)
    MAX_TEMPLATES = 7
    VERIFY_REQUIRED = 1
    VERIFY_MAX_FAILURES = 5
    SESSION_TTL_SECONDS = 300
    MSE_THRESHOLD = 7200.0
    CORRELATION_THRESHOLD = 0.32
    HIST_THRESHOLD = 0.62

    def __init__(self, state_path=None):
        self.state_dir = state_path or state_dir()
        os.makedirs(self.state_dir, mode=0o700, exist_ok=True)
        try:
            os.chmod(self.state_dir, 0o700)
        except OSError:
            pass
        self.template_path = os.path.join(self.state_dir, FACE_TEMPLATE_NAME)
        self.state_key_path = os.path.join(self.state_dir, STATE_KEY_NAME)
        cascade_path = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
        self.detector = cv2.CascadeClassifier(cascade_path)
        self.sessions = {}
        self.failures = {}

    def is_enrolled(self):
        return os.path.exists(self.template_path)

    def enroll_from_frame(self, frame):
        return self.enroll_from_frames([frame])

    def enroll_from_frames(self, frames):
        samples = self._collect_samples(frames)
        if not samples:
            return False, "No usable face detected."
        templates = np.array(samples[: self.MAX_TEMPLATES], dtype=np.float32)
        self._write_templates(templates)
        self.failures.clear()
        return True, "Face UI lock enrolled."

    def verify_from_frame(self, frame, client_id):
        return self.verify_from_frames([frame], client_id)

    def verify_from_frames(self, frames, client_id):
        if self.failures.get(client_id, 0) >= self.VERIFY_MAX_FAILURES:
            return False, "Face lock is temporarily unavailable."
        try:
            templates = self._read_templates()
        except (OSError, ValueError):
            return False, "Face UI lock is not enrolled."

        samples = self._collect_samples(frames)
        if not samples:
            self._record_failure(client_id)
            return False, "No usable face detected."

        good = 0
        for sample in samples:
            if self._matches_any_template(sample, templates):
                good += 1

        if good >= min(self.VERIFY_REQUIRED, len(samples)):
            self.failures.pop(client_id, None)
            return True, "Face verified."

        self._record_failure(client_id)
        return False, "Face verification failed."

    def create_session(self, client_id, token):
        self.sessions[token] = {
            "client_id": client_id,
            "expires_at": time.time() + int(os.environ.get("PHANTASM_UI_FACE_SESSION_SECONDS", self.SESSION_TTL_SECONDS)),
        }

    def session_valid(self, client_id, token):
        if not token:
            return False
        session = self.sessions.get(token)
        if not session:
            return False
        if session["client_id"] != client_id:
            return False
        if session["expires_at"] < time.time():
            self.sessions.pop(token, None)
            return False
        return True

    def clear_session(self, token):
        if token:
            self.sessions.pop(token, None)

    def status(self, client_id=None, token=None):
        return {
            "enabled": True,
            "enrolled": self.is_enrolled(),
            "unlocked": self.session_valid(client_id, token) if client_id is not None else False,
            "max_failures": self.VERIFY_MAX_FAILURES,
            "failures": self.failures.get(client_id, 0) if client_id is not None else 0,
        }

    def _record_failure(self, client_id):
        self.failures[client_id] = self.failures.get(client_id, 0) + 1

    def _collect_samples(self, frames):
        samples = []
        for frame in frames:
            if frame is None:
                continue
            sample = self._face_sample(frame)
            if sample is not None:
                samples.append(sample)
        return samples

    def _face_sample(self, frame):
        gray = cv2.equalizeHist(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
        faces = self.detector.detectMultiScale(gray, scaleFactor=1.08, minNeighbors=4, minSize=(64, 64))
        if len(faces) < 1:
            return None
        faces = sorted(faces, key=lambda item: item[2] * item[3], reverse=True)
        x, y, w, h = faces[0]
        pad_x = int(w * 0.15)
        pad_y = int(h * 0.20)
        x0 = max(0, x - pad_x)
        y0 = max(0, y - pad_y)
        x1 = min(gray.shape[1], x + w + pad_x)
        y1 = min(gray.shape[0], y + h + pad_y)
        face = gray[y0:y1, x0:x1]
        if face.size == 0:
            return None
        resized = cv2.resize(face, self.FACE_SIZE, interpolation=cv2.INTER_AREA)
        normalized = cv2.equalizeHist(resized).astype(np.float32)
        return normalized

    def _write_templates(self, templates):
        payload = io.BytesIO()
        np.savez_compressed(payload, templates=templates)
        encrypted = self._encrypt(payload.getvalue())
        with open(self.template_path, "wb") as handle:
            handle.write(encrypted)
        try:
            os.chmod(self.template_path, 0o600)
        except OSError:
            pass

    def _read_templates(self):
        with open(self.template_path, "rb") as handle:
            data = handle.read()
        if len(data) <= 12:
            raise ValueError("face template is too short")
        nonce, ciphertext = data[:12], data[12:]
        try:
            plaintext = AESGCM(self._state_encryption_key()).decrypt(nonce, ciphertext, self._aad())
        except InvalidTag as exc:
            raise ValueError("face template authentication failed") from exc
        with np.load(io.BytesIO(plaintext), allow_pickle=False) as payload:
            if "templates" in payload:
                templates = payload["templates"].astype(np.float32)
                if templates.ndim == 2:
                    return templates.reshape((1, *templates.shape))
                return templates
            return payload["template"].astype(np.float32).reshape((1, *self.FACE_SIZE))

    def _encrypt(self, plaintext):
        nonce = os.urandom(12)
        return nonce + AESGCM(self._state_encryption_key()).encrypt(nonce, plaintext, self._aad())

    def _state_encryption_key(self):
        secret = os.environ.get("PHANTASM_STATE_SECRET")
        if secret:
            return hashlib.sha256(secret.encode("utf-8")).digest()
        return hashlib.sha256(self._load_or_create_local_state_key() + b":face-ui-lock").digest()

    def _load_or_create_local_state_key(self):
        if os.path.exists(self.state_key_path):
            with open(self.state_key_path, "rb") as handle:
                key = handle.read()
            if len(key) == 32:
                return key

        key = os.urandom(32)
        with open(self.state_key_path, "wb") as handle:
            handle.write(key)
        try:
            os.chmod(self.state_key_path, 0o600)
        except OSError:
            pass
        return key

    def _aad(self):
        return b"phantasm-ui-face-lock:v1"

    def _correlation(self, left, right):
        left_flat = left.reshape(-1)
        right_flat = right.reshape(-1)
        left_norm = left_flat - np.mean(left_flat)
        right_norm = right_flat - np.mean(right_flat)
        denom = float(np.linalg.norm(left_norm) * np.linalg.norm(right_norm))
        if denom == 0.0:
            return 0.0
        return float(np.dot(left_norm, right_norm) / denom)

    def _matches_any_template(self, sample, templates):
        for template in templates:
            mse = float(np.mean((sample - template) ** 2))
            corr = self._correlation(sample, template)
            hist = self._histogram_similarity(sample, template)
            if mse <= self.MSE_THRESHOLD and (corr >= self.CORRELATION_THRESHOLD or hist >= self.HIST_THRESHOLD):
                return True
        return False

    def _histogram_similarity(self, left, right):
        left_hist = cv2.calcHist([left.astype(np.uint8)], [0], None, [32], [0, 256])
        right_hist = cv2.calcHist([right.astype(np.uint8)], [0], None, [32], [0, 256])
        cv2.normalize(left_hist, left_hist)
        cv2.normalize(right_hist, right_hist)
        return float(cv2.compareHist(left_hist, right_hist, cv2.HISTCMP_CORREL))


face_lock = FaceUILock()
